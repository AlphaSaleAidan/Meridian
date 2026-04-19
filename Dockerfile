FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY app/ ./app/
COPY scripts/ ./scripts/

EXPOSE 8000

# Railway sets PORT env var automatically
CMD uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000}
