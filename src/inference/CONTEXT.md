# src/inference/ — Local LLM + Smart Routing + Vector Store

## Components
- `local_llm.py` — Llama 3.1 8B Q4_K_M via llama-cpp-python (CPU, 8 threads)
- `router.py` — Routes batch/background→local ($0), realtime→OpenAI (gpt-4o-mini)
- `embeddings.py` — sentence-transformers (all-MiniLM-L6-v2) + SQLite vector store

## API endpoints (registered in app.py)
- POST /api/inference/generate — smart-routed text generation
- POST /api/inference/search — vector similarity search
- GET /api/inference/stats — model + vector store status
- POST /api/inference/ingest — trigger scraper data ingestion

## Model location
`data/models/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` (4.58GB)
