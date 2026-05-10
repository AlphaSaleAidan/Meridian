# TARS Security Rules

## Hard Rules — Never Violate

1. **Never type or paste credentials** into TARS prompts. Reference them by env var name only.
2. **Never screenshot** pages showing API keys, tokens, or database connection strings.
3. **Never automate** destructive database operations (DROP TABLE, DELETE without WHERE, TRUNCATE).
4. **Never push to production** without explicit confirmation from Aidan.
5. **Never modify** `.env` files on production services through TARS — use Railway/Vercel dashboards.
6. **Never commit** `.env`, credentials, or secret keys to git.
7. **Never expose** internal URLs (localhost:5000, Redis URLs) to external services.

## Credential Handling

- All secrets are sourced from environment variables at runtime
- Local secrets live in `/root/Meridian/.env` (git-ignored)
- Railway secrets are in the Railway Variables tab
- Vercel secrets are in Vercel Environment Variables
- Supabase keys are in the Supabase project settings
- Never hardcode secrets in playbooks or context files

## TARS Session Boundaries

- TARS sessions should be **single-purpose**: one playbook per session
- Close TARS after completing the task — don't leave it running idle
- If TARS navigates to an unexpected page, stop and verify before continuing
- Review TARS actions before confirming any write operations

## Allowed Automation Domains

TARS may only interact with these domains:
- `railway.app` — backend deployment and env vars
- `vercel.com` — frontend deployment and env vars
- `supabase.com` — database management and SQL editor
- `ap.www.namecheap.com` — DNS management
- `dashboard.stripe.com` — payment product setup
- `localhost:5000` — Postal email admin (local only)
- `github.com` — repo management (read-only preferred)

Any other domain requires explicit approval.

## Incident Response

If TARS accidentally:
- **Exposed a secret**: Rotate the key immediately, check git history
- **Modified wrong resource**: Check Railway/Vercel deployment history, rollback if needed
- **Ran wrong migration**: Write a reverse migration, apply via SQL Editor
- **Changed DNS incorrectly**: Revert in Namecheap, wait for propagation

## Audit Trail

TARS sessions are not logged automatically. For critical operations:
1. Note what you asked TARS to do
2. Verify the result in the relevant dashboard
3. If it was a migration or deploy, record it in the project's commit history
