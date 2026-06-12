FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libglib2.0-0 libgl1 ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY requirements-ml.txt .
RUN cat requirements-ml.txt | grep -v '^\s*#' | grep -v '^\s*$' | \
    while read pkg; do \
      pip install --no-cache-dir "$pkg" || echo "SKIP: $pkg"; \
    done

COPY src/ ./src/
# Phone-agent sidecar: caller_memory (deployed always) and the Pipecat bot
# (only activates when MEDIA_STREAMS_ENABLED=1). Heavy audio deps come from
# requirements-ml.txt and are tolerated to fail individually.
# Copying the specific subdir (not services/*) keeps the image lean and
# decouples this from the broad services/ exclusion in .dockerignore.
COPY services/phone_agent/ ./services/phone_agent/

COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

RUN useradd -r -s /bin/false appuser

EXPOSE 8000

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["/bin/sh", "/app/docker-entrypoint.sh"]
