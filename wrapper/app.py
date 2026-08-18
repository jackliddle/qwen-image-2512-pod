import base64
import copy
import json
import os
import time
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

COMFY_URL = "http://127.0.0.1:8188"
WORKFLOW_PATH = Path(__file__).parent / "workflow_api.json"
API_TOKEN = os.environ["WRAPPER_API_TOKEN"]

PROMPT_NODE_ID = os.environ.get("WORKFLOW_PROMPT_NODE_ID", "6")
LATENT_NODE_ID = os.environ.get("WORKFLOW_LATENT_NODE_ID", "58")
SEED_NODE_ID = os.environ.get("WORKFLOW_SEED_NODE_ID", "3")

app = FastAPI()


class GenerateRequest(BaseModel):
    prompt: str
    width: int = 1328
    height: int = 1328
    seed: int | None = None


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

    workflow[PROMPT_NODE_ID]["inputs"]["text"] = req.prompt
    workflow[LATENT_NODE_ID]["inputs"]["width"] = req.width
    workflow[LATENT_NODE_ID]["inputs"]["height"] = req.height
    if req.seed is not None:
        workflow[SEED_NODE_ID]["inputs"]["seed"] = req.seed

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
