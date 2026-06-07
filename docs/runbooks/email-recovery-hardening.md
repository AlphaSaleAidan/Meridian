# Runbook — Password-recovery & verification email hardening

Status: **ready to apply — NOT yet applied to prod.** The code change in this PR
is safe to merge as-is (no behaviour change until the env var is set). The
Supabase config steps below are manual and must be done by a human with
dashboard access.

## Problem

Recovery / verification emails for the customer portal go through **Supabase
Auth's email sender**, which is a *separate* path from the backend Resend/Postal
transport used for application email. Three weaknesses:

1. **Built-in SMTP is capped at ~2 emails/hour (project-wide).** Under any real
   onboarding volume, `POST /auth/v1/recover` and `/auth/v1/resend` start
   returning `429` and the email never sends.
2. **`site_url` is stale.** It points at `https://meridian-dun-nu.vercel.app`,
   so the reset link in the email lands on the wrong host instead of
   meridian.tips — a customer who clicks it can't complete the reset.
3. **Failures were swallowed.** `forgot-password` (and `verify`) always returned
   "email sent" regardless of the Supabase response, so a fully-broken recovery
   flow was invisible to ops.

## What the code change in this PR does

- `src/auth/router.py`
  - `forgot-password` and `verify` now **log** `429` / `5xx` / transport errors
    from Supabase at `error` level, so broken email delivery is visible. The
    client-facing response is unchanged (still generic, still enumeration-safe).
  - `forgot-password` appends `redirect_to=$PASSWORD_RESET_REDIRECT_URL` to the
    recover call when that env var is set, so the reset link points at the right
    host. **Empty/unset = current behaviour** (falls back to Supabase site_url),
    so merging this changes nothing until you set the env var.

This fixes observability and the link target. It does **not** fix the 2/hr cap —
that requires the custom-SMTP config below.

## Apply steps (manual — do in this order)

### 1. Configure custom SMTP in Supabase (fixes the 2/hr cap + deliverability)
Supabase Dashboard → Authentication → Emails → SMTP Settings → Enable custom SMTP.
Reuse the existing **Resend** account already used for application email:
- Host: `smtp.resend.com`  Port: `465` (or `587`)
- Username: `resend`  Password: the Resend API key (from the env / secret store)
- Sender email: a verified domain sender, e.g. `no-reply@meridian.tips`
- Sender name: `Meridian`

(Resend domain for meridian.tips must be verified — DNS is documented in
`docs/postal-dns-setup.md` for the Postal path; the Resend sender domain needs
its own SPF/DKIM records if not already verified.)

### 2. Fix the redirect target
- Supabase Dashboard → Authentication → URL Configuration:
  - **Site URL**: `https://meridian.tips`
  - **Redirect URLs (allow-list)**: add the reset page, e.g.
    `https://meridian.tips/canada/reset-password` (and any other portal hosts).
- Railway → Meridian (API) service → Variables: set
  `PASSWORD_RESET_REDIRECT_URL=https://meridian.tips/canada/reset-password`
  (must exactly match an allow-listed redirect URL). Redeploy the API.

### 3. (Optional) raise the email rate limit
Dashboard → Authentication → Rate Limits → "Emails sent per hour": raise from the
default once custom SMTP is in place. With custom SMTP the built-in 2/hr cap no
longer applies, but the GoTrue per-hour limit still does.

## Verify

After applying:
1. From the portal, trigger "Forgot password" for a real test account.
2. Email should arrive from `no-reply@meridian.tips` (not the Supabase default
   sender), within seconds, not rate-limited.
3. The reset link host should be `meridian.tips`, and completing the reset should
   succeed end-to-end.
4. Check API logs: a healthy send logs nothing at error level; a `429`/`5xx`
   now produces an `error` log line (grep `forgot-password:` / `verify:`).

## Rollback
- Code: revert this PR (no state to undo).
- Config: unset `PASSWORD_RESET_REDIRECT_URL` (reverts link to site_url), and/or
  disable custom SMTP in the dashboard to fall back to the built-in sender.

## Related
- Backend app email (Resend/Postal) is a different transport — see
  `docs/postal-dns-setup.md`. Fixing Supabase Auth SMTP does **not** affect it,
  and vice-versa.
