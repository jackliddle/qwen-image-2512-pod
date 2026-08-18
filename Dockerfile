FROM runpod/comfyui:cuda12.8

COPY wrapper /opt/wrapper
RUN pip install --no-cache-dir -r /opt/wrapper/requirements.txt

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8188 8000 22

ENTRYPOINT ["/entrypoint.sh"]
