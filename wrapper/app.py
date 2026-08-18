import base64
import copy
import json
import os
import random
import time
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

COMFY_URL = "http://127.0.0.1:8188"
WORKFLOW_PATH = Path(__file__).parent / "workflow_api.json"
API_TOKEN = os.environ["WRAPPER_API_TOKEN"]

# Node IDs from the exported Qwen-Image-2512 workflow (wrapper/workflow_api.json).
POSITIVE_PROMPT_NODE_ID = "238:227"
NEGATIVE_PROMPT_NODE_ID = "238:228"
LATENT_NODE_ID = "238:232"
SEED_NODE_ID = "238:230"
LIGHTNING_LORA_SWITCH_NODE_ID = "238:229"

DEFAULT_NEGATIVE_PROMPT = (
    "低分辨率，低画质，肢体畸形，手指畸形，画面过饱和，蜡像感，"
    "人脸无细节，过度光滑，画面具有AI感。构图混乱。文字模糊，扭曲"
)

app = FastAPI()


class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT
    width: int = 1328
    height: int = 1328
    seed: int | None = None
    fast: bool = False  # use the 4-step Lightning LoRA for speed over quality


def check_auth(authorization: str | None) -> None:
    if authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="invalid or missing bearer token")


@app.get("/health")
def health():
    try:
        r = httpx.get(f"{COMFY_URL}/system_stats", timeout=5)
        r.raise_for_status()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"comfyui not ready: {e}")


@app.post("/generate")
def generate(req: GenerateRequest, authorization: str | None = Header(default=None)):
    check_auth(authorization)

    workflow = json.loads(WORKFLOW_PATH.read_text())
    workflow = copy.deepcopy(workflow)

    workflow[POSITIVE_PROMPT_NODE_ID]["inputs"]["text"] = req.prompt
    workflow[NEGATIVE_PROMPT_NODE_ID]["inputs"]["text"] = req.negative_prompt
    workflow[LATENT_NODE_ID]["inputs"]["width"] = req.width
    workflow[LATENT_NODE_ID]["inputs"]["height"] = req.height
    workflow[SEED_NODE_ID]["inputs"]["seed"] = (
        req.seed if req.seed is not None else random.randint(0, 2**32 - 1)
    )
    workflow[LIGHTNING_LORA_SWITCH_NODE_ID]["inputs"]["value"] = req.fast

    submit = httpx.post(f"{COMFY_URL}/prompt", json={"prompt": workflow}, timeout=30)
    submit.raise_for_status()
    prompt_id = submit.json()["prompt_id"]

    deadline = time.monotonic() + 300
    history = None
    while time.monotonic() < deadline:
        r = httpx.get(f"{COMFY_URL}/history/{prompt_id}", timeout=10)
        r.raise_for_status()
        body = r.json()
        if prompt_id in body:
            history = body[prompt_id]
            break
        time.sleep(1)

    if history is None:
        raise HTTPException(status_code=504, detail="generation timed out")

    images = []
    for node_output in history["outputs"].values():
        for img in node_output.get("images", []):
            r = httpx.get(
                f"{COMFY_URL}/view",
                params={
                    "filename": img["filename"],
                    "subfolder": img["subfolder"],
                    "type": img["type"],
                },
                timeout=30,
            )
            r.raise_for_status()
            images.append(base64.b64encode(r.content).decode())

    if not images:
        raise HTTPException(status_code=500, detail="no images in comfyui output")

    return {"image_b64": images[0], "images_b64": images}
