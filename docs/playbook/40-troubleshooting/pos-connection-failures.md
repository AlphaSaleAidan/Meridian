# POS Connection Failures

Symptom dictionary. Find the merchant's exact complaint, follow the fix.

## "I clicked Connect and nothing happened"

| Cause | Diagnosis | Fix |
|-------|-----------|-----|
| Popup blocked | Browser blocked the OAuth popup window | Allow popups for meridian.tips, retry |
| Logged into wrong POS account | Their browser is signed into a different merchant | Log out of POS, retry |
| Stale session | Old portal session, redirect URL expired | Log out of Meridian, log back in, retry |
| Sandbox vs production | Using sandbox connect URL on prod account (rare, internal bug) | Confirm they're on `meridian.tips` not a dev URL |

## "OAuth screen says 'App not found' or 'Invalid client'"

| POS | Likely cause | Fix |
|-----|--------------|-----|
| Square | Production app not configured for their region | Check `src/square/oauth.py`; usually a region mismatch (US/CA/AU) |
| Clover | Wrong environment (sandbox vs production) | Use production connect URL only |
| Toast | Restaurant external ID wrong | Toast Web → Settings → confirm GUID |

## "It worked, now it says 401 / unauthorized after months"

This is the **classic token-refresh bug**.

| POS | Token behavior | Fix |
|-----|---------------|-----|
| **Clover** | **Tokens DO expire** despite the old code comment claiming otherwise. **Known production bug** — fix pending. | **Workaround: one-click reconnect from portal.** No data loss. |
| Square | Refresh token rotates after 30 days of inactivity | Re-OAuth from portal |
| Toast | Bearer expires hourly (auto-refreshes); breaks if Toast credentials revoked | Confirm Toast credential still active in Toast Web; regenerate if needed |

**Clover-specific:** track this as a known issue. The fix is in flight (see Phase 2 decisions, production issue #1). Until then, advise affected merchants to reconnect — full history preserved, no data loss.

## "Connection succeeded but no data is appearing"

| Cause | Fix |
|-------|-----|
| Backfill hasn't started yet | Wait 5–10 minutes; backfill kicks off after handshake completes |
| Backfill stuck | See [backfill-stuck.md](./backfill-stuck.md) |
| Webhooks not configured (Toast) | Webhooks shipping this wave; meanwhile hourly poll covers it |
| Merchant has no recent transactions | Confirm they're actually transacting; check their POS dashboard for today |

## POS-specific error reference

### Square (`OAuthError`, `SquareAPIError`)

| Error | Meaning | Fix |
|-------|---------|-----|
| `OAuthError: invalid_grant` | Refresh token expired | Reconnect from portal |
| `SquareAPIError: PERMISSION_DENIED` | Scope rejected (merchant didn't approve all scopes) | Reconnect, approve all requested scopes |
| `SquareAPIError: RATE_LIMITED` | Square throttling our backfill | Auto-handled; backfill slows but continues |

### Clover (`CloverOAuthError`, `CloverAPIError`)

| Error | Meaning | Fix |
|-------|---------|-----|
| `CloverOAuthError: token expired` | The token-refresh bug | Reconnect (workaround until fix ships) |
| `CloverAPIError: 401 Unauthorized` | Auth header rejected | Reconnect |
| `CloverAPIError: 429` | Rate limited | Auto-throttle; expected at high volumes |

### Toast (`ToastAuthError`)

| Error | Meaning | Fix |
|-------|---------|-----|
| `ToastAuthError: invalid client credentials` | Client ID/secret revoked or wrong | Regenerate in Toast Web → API Access |
| `ToastAuthError: restaurant ID not found` | Wrong restaurant external ID | Toast Web → Settings → use the GUID, not the display name |

### Other POSes

For Lightspeed, Korona, Shopify POS, CAKE, Lavu, talech, SkyTab, Cova, cannabis POSes, Wave 2 systems: the error patterns above generalize. If you see a 401, the first move is **reconnect from portal**. If you see a 4xx other than 401, check the POS-specific doc in `10-pos-integrations/` for the "common failure modes" section.

## "I get a Meridian-side error: `IntegrationError` / `AuthError`"

These are our internal exception types from `src/errors.py`:

- `IntegrationError(provider="...")` — the POS interaction failed; check the provider-specific error above
- `AuthError(org_id=...)` — OAuth/token/RLS issue; usually means reconnect
- `DataError(...)` — not a connection problem; see [data-mismatch.md](./data-mismatch.md) or [insights-not-appearing.md](./insights-not-appearing.md)
- `ConfigError(...)` — internal config bug; **escalate to engineering**, do not try to fix client-side

## When to escalate

| Time spent | Next step |
|-----------|-----------|
| 15 min, no progress | Open Medium ticket |
| 30 min, customer is in active conversation | Open High ticket + Slack ping |
| Customer says "I'm cancelling" | Open Critical ticket + tag CS Manager |

---

_Last updated: 2026-05-31_
_Sourced from: src/errors.py + src/square/oauth.py + src/clover/oauth.py + src/toast/client.py + docs/playbook/_status/phase-2-decisions.md (production issue #1 — Clover token refresh)_
