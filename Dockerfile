FROM python:3.12-slim

WORKDIR /app

# Install build dependencies for ML packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ cmake gfortran \
    libopenblas-dev liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Install core dependencies first (fast, required to boot)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install ML dependencies (optional, heavy — won't block boot if they fail)
COPY requirements-ml.txt .
RUN pip install --no-cache-dir -r requirements-ml.txt || echo "WARNING: Some ML packages failed to install. App will still boot."

COPY src/ ./src/

EXPOSE 8000

ENTRYPOINT ["python", "-c", "import os, uvicorn; uvicorn.run('src.api.app:app', host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))"]
