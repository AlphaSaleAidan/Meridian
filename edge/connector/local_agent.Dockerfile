# meridian-connector (local-processing build) — ONE image the merchant runs on an
# existing on-site PC/POS. Does EVERYTHING locally, no GPU, no cloud media gateway:
#   go2rtc  -> ONVIF discovery + local frame API (camera creds stay on this box)
#   local_agent.py -> YOLO11 pipeline on CPU -> POST anonymous counts to Meridian
#
# Build from the REPO ROOT (needs src/camera):
#   docker build -f edge/connector/local_agent.Dockerfile -t ghcr.io/alphasaleaidan/meridian-connector .
#
# One-line run (shown by the "Connect cameras" wizard):
#   docker run -d --network host --restart unless-stopped \
#     -e MERIDIAN_PAIRING_CODE=XXXX -e MERIDIAN_API=https://api.meridian.tips \
#     ghcr.io/alphasaleaidan/meridian-connector
FROM alexxit/go2rtc:latest AS go2rtc

FROM python:3.12-slim
# opencv-headless needs libglib; ffmpeg helps go2rtc with odd camera codecs.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libglib2.0-0 ffmpeg ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY --from=go2rtc /usr/local/bin/go2rtc /usr/local/bin/go2rtc

WORKDIR /app
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1

COPY edge/connector/requirements.txt .
# Pin CPU-only torch wheels so we don't pull ~5GB of CUDA onto a POS box.
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

# The real pipeline (detector + people counter + zone loader) — reused verbatim.
COPY src/camera/ /app/src/camera/
# Bake the model into the image (version-matched to ultralytics) so there's no
# runtime download on the merchant's network.
RUN python3 -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"
COPY edge/connector/local_agent.py edge/connector/go2rtc.yaml edge/connector/entrypoint-local.sh ./
RUN chmod +x entrypoint-local.sh

# host networking is needed for ONVIF LAN multicast discovery.
ENTRYPOINT ["./entrypoint-local.sh"]
