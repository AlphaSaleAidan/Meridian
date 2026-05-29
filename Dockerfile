FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libglib2.0-0 libgl1 && \
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
COPY services/ ./services/

RUN useradd -r -s /bin/false appuser

EXPOSE 8000

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["python", "-c", "import os, uvicorn; uvicorn.run('src.api.app:app', host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))"]
