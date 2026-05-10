# Playbook: Add Railway Environment Variables

## Goal
Add or update environment variables on the Railway Meridian backend service.

## Steps

1. Open browser to https://railway.app/dashboard
2. Log in if prompted (aidanpierce72@gmail.com)
3. Click the **Meridian** project
4. Click the **backend** service (the one running `uvicorn`)
5. Click the **Variables** tab
6. For each variable to add:
   - Click **+ New Variable**
   - Enter the variable name in the **Key** field
   - Enter the value in the **Value** field
   - Click **Add**
7. After all variables are added, click **Deploy** (Railway auto-redeploys on variable changes, but verify)
8. Verify the deploy succeeded by checking the **Deployments** tab — latest deploy should show green

## Common Variables

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anonymous/public key |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `REDIS_URL` | Redis connection string for Celery |
| `SQUARE_ACCESS_TOKEN` | Square POS API token |
| `CLOVER_API_KEY` | Clover POS API key |
| `POSTAL_API_KEY` | Postal mail server API key |
| `ANTHROPIC_API_KEY` | Claude API key for AI agents |

## Verification

After deploy completes, hit the health endpoint:
```
curl https://api.meridian.tips/health
```
Expected: `{"status": "ok", ...}`
