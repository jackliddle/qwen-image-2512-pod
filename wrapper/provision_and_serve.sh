#!/usr/bin/env bash
set -uo pipefail

COMFY_DIR="/workspace/runpod-slim/ComfyUI"
MODELS_DIR="$COMFY_DIR/models"

echo "[qwen] Waiting for /start.sh to create the ComfyUI workspace..."
until [ -d "$MODELS_DIR" ]; do
  sleep 2
done

mkdir -p "$MODELS_DIR/diffusion_models" "$MODELS_DIR/text_encoders" "$MODELS_DIR/vae" "$MODELS_DIR/loras"

download_if_missing() {
  local repo="$1" file="$2" dest="$3"
  if [ ! -f "$dest" ]; then
    echo "[qwen] Downloading $repo/$file -> $dest"
    if curl -fL "https://huggingface.co/$repo/resolve/main/$file" -o "$dest.part"; then
      mv "$dest.part" "$dest"
    else
      echo "[qwen] ERROR: failed to download $repo/$file" >&2
      rm -f "$dest.part"
    fi
  else
    echo "[qwen] Already present: $dest"
  fi
}

download_if_missing "Comfy-Org/Qwen-Image_ComfyUI" \
  "split_files/diffusion_models/qwen_image_2512_fp8_e4m3fn.safetensors" \
  "$MODELS_DIR/diffusion_models/qwen_image_2512_fp8_e4m3fn.safetensors"

download_if_missing "Comfy-Org/Qwen-Image_ComfyUI" \
  "split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors" \
  "$MODELS_DIR/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors"

download_if_missing "Comfy-Org/Qwen-Image_ComfyUI" \
  "split_files/vae/qwen_image_vae.safetensors" \
  "$MODELS_DIR/vae/qwen_image_vae.safetensors"

download_if_missing "lightx2v/Qwen-Image-2512-Lightning" \
  "Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors" \
  "$MODELS_DIR/loras/Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors"

echo "[qwen] Models provisioned. Waiting for ComfyUI (started by /start.sh) to become ready..."
until curl -sf http://127.0.0.1:8188/system_stats > /dev/null 2>&1; do
  sleep 5
done
echo "[qwen] ComfyUI is ready. Starting wrapper API on :8000"

cd /opt/wrapper
exec uvicorn app:app --host 0.0.0.0 --port 8000
