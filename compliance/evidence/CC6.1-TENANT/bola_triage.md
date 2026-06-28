# C1 BOLA triage — `require_service_auth` / `require_jwt` + `org_id` endpoints

> Refines the C1 finding with ground truth (route auth + frontend consumers + the rep model). v0.1 — 2026-06-28.
> **No code was changed** — the correct fix depends on a rep-authorization model decision (below). Editing these
> live endpoints with a member-check would break the rep/sales portal.

## What's already covered (no action)
Merchant-facing tenant-data routes already call `enforce_service_member`: `phone_dashboard.py` (11),
`schedule.py` (11), `website.py` (10), `intelligence.py` (4), `pos.py` (2), `stripe_connect.py` (3). These are
the routes a merchant calls for their **own** org's data — membership is the right control and it's enforced.

## The real remaining surface — rep/admin/provisioning endpoints
The `require_service_auth`/`require_jwt` endpoints **without** a member check are not a simple oversight — they
are **rep, admin, or provisioning** surfaces where a *member* check is the **wrong** control:

| Endpoint | Auth today | Consumer (frontend) | Verdict |
|---|---|---|---|
| `billing/status/{org_id}` (GET) | `require_jwt` | merchant `SettingsPage` **and** rep `*PortalLeadDetail/Accounts` | **BOLA read** — any logged-in user reads any org's subscription. Member-check breaks the rep view. |
| `billing/invoice-url/{org_id}` (GET) | `require_jwt` | `SettingsPage` | **BOLA read** (lower sensitivity). |
| `billing/create-checkout` | `require_jwt` | rep `*PortalCreateCustomer`, onboarding wizards | rep acts for a customer org → member-check wrong. |
| `billing/create-invoice` | `require_service_auth` | rep/customer onboarding wizards | "the SR sets a custom amount" — rep, not member. |
| `billing/update-payment-method` | `require_service_auth` | rep `*PortalAccounts/LeadDetail` | rep acts for customer. |
| `billing/notify-payment-failed` | `require_service_auth` | machine/cron | `enforce_service_member` is a safe no-op here, but caller is machine anyway. |
| `onboarding/provision-customer` | `require_service_auth` | rep onboarding wizards | provisioning a NEW org — no membership exists yet. Member-check impossible. |
| `onboarding/checklist?org_id` | (verify) | onboarding | provisioning context. |
| `email/log`, `email/stats` | `require_admin` | admin `EmailDashboard` | **admin-locked — fine.** |
| `billing/cancel`, `process-renewals`, `check-trials` | `require_admin_auth`/`require_admin` | admin/automation | **fine.** |
| `payouts/*` | `require_admin_auth` | admin | **fine.** |

## Why this is a DECISION, not a code edit
Reps are rows in `sales_reps` (`supabase/migrations/20260512_sales_reps_table.sql`); they are **not**
`business_users` of the customer orgs they manage. So `enforce_service_member`/`require_org_member` would deny
every rep and break the US/Canada sales portal. The genuine vulnerability is that these endpoints today
authorize **"any logged-in user"** with no org binding at all — a rep (or any user) can pass an arbitrary
`org_id`. The fix is a **rep-authorization** check, which needs the rep↔org model defined.

## DECISION — SELECTED: Option A (ownership link). 2026-06-28
Aidan deferred the choice ("I don't know what's best"); proceeding with the recommended **Option A** — authorize
a rep for an org only when an ownership/creation link exists (rep created/owns that org). Next step: confirm the
data model carries a rep→org link (e.g. `created_by_rep`/`rep_id` on `businesses` or `subscriptions`, or via the
`sales_reps` provisioning path) and, if missing, stamp it at provisioning. Then implement `require_rep_for_org`.
This is a separate PR after the data-model confirmation; it is NOT a prod change yet.

## Option menu (for the record) — what authorizes a rep to act on a customer org?
Pick the binding, then a `require_rep_for_org(principal, org_id)` helper can enforce it:
- **(A, recommended) Ownership link** — stamp `created_by_rep`/`rep_id` on the business/subscription at
  provisioning (`onboarding/provision-customer`, `us.create_customer` already track `rep_id`), and authorize a
  rep only for orgs they created. Cleanest; data largely exists.
- **(B) Rep-assignment table** — explicit `rep_assignments(rep_id, org_id)`; most flexible, most new plumbing.
- **(C) Any active rep** — accept that any approved rep may act on any customer org (today's de-facto behavior),
  and simply require the caller be an **active rep** (`sales_reps.is_active`) rather than any logged-in user.
  Closes the "any user" hole cheaply but gives every rep access to every customer.

Plus, independently: `billing/status` + `invoice-url` need "**member OR authorized-rep**" (merchants hit them
from `SettingsPage`; reps from the portal).

## Recommended remediation (after the decision)
Add `require_rep_for_org(principal, org_id)` implementing the chosen binding; apply it to the rep/billing
endpoints above (capturing the principal via `principal = Depends(require_service_auth)` instead of the
`dependencies=[...]` list form). Extend `tests/api/test_tenant_isolation_bola.py` with: (1) a rep authorized for
their org → 200, (2) a rep/user **not** authorized for the org → 403 and the side effect does not run. Then
this is a clean, reviewable PR — but it should **not** ship before the model is confirmed and the rep portal is
verified on staging.

## Status
🟡 C1 refined: merchant routes covered; rep-portal endpoints need rep-authorization (model = Aidan's call).
This is more accurate than "thread `enforce_service_member` everywhere," which would break the sales portal.
