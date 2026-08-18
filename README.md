# qwen-image-2512-pod

Self-built Runpod Pod image for Qwen-Image-2512 (ComfyUI-native, fp8) bulk
image generation, with a thin wrapper API on top of ComfyUI's own HTTP API.

- Base: `runpod/comfyui:cuda12.8`
- Models (Comfy-Org's ComfyUI-native repackaging, downloaded once at first
  boot onto the pod's persistent volume): `qwen_image_2512_fp8_e4m3fn`,
  `qwen_2.5_vl_7b_fp8_scaled`, `qwen_image_vae`
- Wrapper API: `POST /generate {prompt, width, height, seed} -> {image_b64}`,
  bearer-token protected via `WRAPPER_API_TOKEN` env var
- Built and pushed to `ghcr.io/jackliddle/qwen-image-2512-pod` by
  `.github/workflows/build.yml` on every push to `main`

See the parent `runpod-endpoints` repo's `ENDPOINTS.md` for the deployed pod
ID, ports, and proxy URLs once live.
