#!/usr/bin/env bash
set -euo pipefail

COMFY_DIR="/workspace/ComfyUI"
MODELS_DIR="$COMFY_DIR/models"

mkdir -p "$MODELS_DIR/diffusion_models" "$MODELS_DIR/text_encoders" "$MODELS_DIR/vae"

download_if_missing() {
  local repo="$1" file="$2" dest="$3"
  if [ ! -f "$dest" ]; then
    echo "Downloading $repo/$file -> $dest"
    curl -fL "https://huggingface.co/$repo/resolve/main/$file" -o "$dest.part"
    mv "$dest.part" "$dest"
  else
    echo "Already present: $dest"
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

echo "Starting ComfyUI on :8188"
cd "$COMFY_DIR"
python3 main.py --listen 0.0.0.0 --port 8188 &
COMFY_PID=$!

echo "Waiting for ComfyUI to become ready..."
until curl -sf http://127.0.0.1:8188/system_stats > /dev/null 2>&1; do
  sleep 2
done
echo "ComfyUI is ready."

echo "Starting wrapper API on :8000"
cd /opt/wrapper
uvicorn app:app --host 0.0.0.0 --port 8000 &
WRAPPER_PID=$!

wait -n "$COMFY_PID" "$WRAPPER_PID"
