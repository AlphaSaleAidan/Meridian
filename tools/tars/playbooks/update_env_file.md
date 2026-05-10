# Playbook: Update Local .env File

## Goal
Add or update environment variables in the local `/root/Meridian/.env` file.

## Steps

1. SSH into the VPS (or use terminal if already on it)
2. Open the env file:
   ```bash
   nano /root/Meridian/.env
   ```
3. Add or update the variable(s). Format: `KEY=value` (no spaces around `=`, no quotes unless value contains spaces)
4. Save and exit (Ctrl+X, Y, Enter in nano)
5. Restart affected service:
   ```bash
   # Backend API
   kill $(lsof -t -i:8000) 2>/dev/null; cd /root/Meridian && uvicorn src.api.app:app --host 0.0.0.0 --port 8000 &

   # Celery workers
   pkill -f "celery worker" 2>/dev/null
   cd /root/Meridian && celery -A src.workers.celery_app worker -Q default,sync,analysis,reports &
   ```

## Current Variable Groups

### Database
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
DATABASE_URL=postgresql://...
```

### POS Integrations
```
SQUARE_ACCESS_TOKEN=...
SQUARE_LOCATION_ID=...
SQUARE_ENVIRONMENT=sandbox|production
CLOVER_API_KEY=...
CLOVER_MERCHANT_ID=...
CLOVER_ENVIRONMENT=sandbox|production
```

### Email
```
POSTAL_HOST=https://postal.meridian.tips
POSTAL_API_KEY=...
POSTAL_FROM=Meridian <hello@meridian.tips>
```

### AI / Task Queue
```
ANTHROPIC_API_KEY=sk-ant-...
REDIS_URL=redis://localhost:6379/0
```

## Security Rules

- NEVER commit `.env` to git (it's in `.gitignore`)
- NEVER paste secrets into chat or logs
- Rotate keys immediately if exposed
- Use `.env.example` as a template (no real values)
