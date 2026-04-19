# Meridian

**AI-Powered POS Analytics for Independent Business Owners**

Meridian connects to your Square POS and transforms raw transaction data into actionable business intelligence — revenue insights, product performance scoring, demand forecasting, and "money left on the table" analysis.

## Architecture

- **Backend:** FastAPI (Python)
- **Database:** Supabase (PostgreSQL + TimescaleDB)
- **POS Integration:** Square (OAuth + Webhooks)
- **AI Engine:** Revenue analysis, pattern detection, product scoring, demand forecasting

## Quick Start

```bash
cp .env.example .env
# Fill in your Square and Supabase credentials
pip install -r requirements.txt
uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

## Deploy

```bash
docker build -t meridian .
docker run -p 8000:8000 --env-file .env meridian
```
