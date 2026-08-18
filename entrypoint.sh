#!/usr/bin/env bash
set -uo pipefail

# Run model provisioning + the wrapper API in the background, then hand off
# PID 1 to the base image's own /start.sh (which sets up SSH, Jupyter,
# FileBrowser, and correctly installs/starts ComfyUI at
# /workspace/runpod-slim/ComfyUI). Overriding /start.sh entirely — instead of
# chaining to it — is what broke SSH and the ComfyUI path in an earlier
# version of this image.
/opt/wrapper/provision_and_serve.sh &

exec /start.sh
