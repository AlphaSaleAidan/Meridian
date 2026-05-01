FROM python:3.11-slim

WORKDIR /app

# Install core requirements only (fast boot, Railway-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install ML requirements separately (optional heavy packages)
COPY requirements-ml.txt .
RUN pip install --no-cache-dir -r requirements-ml.txt || echo "ML packages skipped (non-critical)"

COPY src/ ./src/

EXPOSE 8000

ENTRYPOINT ["python", "-c", "import os, uvicorn; uvicorn.run('src.api.app:app', host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))"]
