FROM ultralytics/ultralytics:latest-jetson-jetpack5

WORKDIR /app

# Static ffmpeg >= 7.x (arm64) for the WHIP muxer — the live-view publisher
# (live_publisher.py) needs it; JetPack's bundled ffmpeg is too old.
RUN apt-get update && apt-get install -y --no-install-recommends curl xz-utils ca-certificates \
 && curl -fsSL "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linuxarm64-gpl.tar.xz" -o /tmp/ff.tar.xz \
 && tar -xf /tmp/ff.tar.xz -C /tmp \
 && cp /tmp/ffmpeg-*/bin/ffmpeg /usr/local/bin/ffmpeg && chmod +x /usr/local/bin/ffmpeg \
 && rm -rf /tmp/ff* && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY edge_agent.py live_publisher.py .
COPY config/ config/

CMD ["python", "edge_agent.py"]
