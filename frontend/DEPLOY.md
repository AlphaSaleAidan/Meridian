# Meridian Frontend — Manual Production Deploy (Contabo)

The Canada dashboard frontend is served as a **static build on a Contabo nginx
box**. It is **not** built by Railway and **not** auto-deployed from `main` — a
human runs a build locally/on the box and copies `dist/` into place.

## The footgun this guards against

Vite inlines `import.meta.env.VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` as
string literals **at build time**, reading them from `frontend/.env.local`
(git-ignored). If that file is missing or has empty/placeholder values, the
build silently ships **demo mode**:

- `src/lib/supabase.ts` sees empty creds → exports `supabase = null`
- every `if (!supabase)` path degrades to demo/no-auth behavior
- **customers can't log in**, and nobody notices until they complain

## The guard (software only — does not change build output)

Two scripts + a wrapper npm script make the safe path the default:

| Script | When | What it asserts |
|--------|------|-----------------|
| `scripts/preflight-build.mjs` | **before** `vite build` | `.env.local` exists; `VITE_SUPABASE_URL` is a real `https` URL (not empty/placeholder/localhost); `VITE_SUPABASE_ANON_KEY` is present and JWT-length. Loud, specific, exits non-zero on any failure. |
| `scripts/verify-dist.mjs` | **after** `vite build` | greps the built `dist/` — **fails** if the demo-mode marker string `running without Supabase (demo mode)` is present, and **fails** if the real Supabase host from `.env.local` is not inlined anywhere in the JS. |

Both are wired into `package.json`:

```jsonc
"preflight:build": "node scripts/preflight-build.mjs",
"verify:dist":     "node scripts/verify-dist.mjs",
"build:prod":      "npm run preflight:build && npm run build && npm run verify:dist",
```

## How to deploy

```bash
cd frontend

# 1. Ensure the real prod env file exists (git-ignored — never committed).
#    Copy from the template and fill in the REAL Supabase values.
cp .env.example .env.local     # first time only
$EDITOR .env.local             # set VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY (and VITE_API_URL etc.)

# 2. Build the SAFE way. This refuses to proceed on a bad env and refuses to
#    leave a demo-mode dist/ behind.
npm run build:prod

# 3. Ship dist/ to the nginx docroot (adjust path to the box).
#    e.g. rsync -av --delete dist/ /var/www/meridian/
```

- `npm run build:prod` is the **only** command an operator should use for a
  production/Contabo build.
- Plain `npm run build` still exists unchanged for CI/dev (no guard) — do not
  use it to cut a production bundle.

## If a guard fails

- **preflight fails** → your `.env.local` is missing or has bad values. The
  error names the exact variable and problem. Fix it, re-run.
- **verify-dist fails** → the bundle you just built is demo mode. Do **not**
  copy `dist/` to the server. Fix `.env.local`, run `npm run build:prod` again.

## Demo-mode detection reference

Demo mode is defined entirely by `src/lib/supabase.ts`:

```ts
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || ''
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''
if (!supabaseUrl || !supabaseAnonKey) {
  console.error('[Meridian] Missing ... running without Supabase (demo mode)')
}
export const supabase = supabaseUrl && supabaseAnonKey ? createClient(...) : null
```

`verify-dist.mjs` keys off that exact `(demo mode)` marker string (which
survives Vite minification) plus the presence of the real inlined host. If you
change that message in `supabase.ts`, update `DEMO_MARKER` in
`scripts/verify-dist.mjs` to match.
