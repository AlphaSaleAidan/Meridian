# Multi-Location Hub — Customer Journey & Spec

Status: **Accepted (v1)** · Workstream 5 · Branch `feat/multi-location-hub` · 2026-07-19

The Multi-Location Hub lets a single business owner — one authenticated identity,
one email — own and operate **several Meridian portals (orgs/locations)** and run
them from one command surface. It is a **Command-tier** capability.

This document is the deliverable **spec**: it defines *what* the hub does end to
end, the account model, billing implications, provisioning, staff/role
separation, and the tier gate. Implementation notes (what is wired vs stubbed in
v1) are called out inline.

---

## 0. Vocabulary (read this first — the repo has two tier vocabularies)

Meridian carries **two overlapping tier vocabularies** and they are *not* the
same column:

| Axis | Values | Where |
|------|--------|-------|
| `businesses.plan_tier` (provisioned account tier) | `trial · starter · growth · enterprise` | `20260429_001_business_accounts.sql` CHECK constraint |
| Sales / billing plan id (fee schedule) | `standard · premium · command` | `src/billing/fee_terms.py`, `frontend/.../proposal-plans.ts` |

The onboarding layer maps the sales plan id onto the account tier
(`onboarding._PLAN_TIER_MAP`): `command → enterprise`. So **the "Command tier"
the hub is gated to is represented by `businesses.plan_tier = 'enterprise'`**, and
authoritatively by `merchant_billing_terms.plan_tier = 'command'` (the locked
contract) when present.

**Canonical resolver (this workstream):** `src/billing/tiers.py::is_command_tier()`
treats an org as Command tier if **either**:
- its active `merchant_billing_terms.plan_tier == 'command'` (authoritative
  locked contract), **or**
- `businesses.plan_tier == 'enterprise'` (the provisioned account tier the sales
  `command` plan maps to).

The hub gate never trusts the request body for tier — it always resolves tier
from the org record / billing contract server-side.

---

## 1. The customer journey

### 1.1 Starting point — one owner, one location

An owner signs up (or is provisioned by a rep). Today this yields exactly one
`businesses` row (the org) with `owner_user_id = auth.users.id`, and one
`business_users` row (`role = 'owner'`). Login resolves that single org.
`businesses.max_locations` defaults to `1`.

### 1.2 Adding location #2 (same email)

The owner decides to open / acquire a second location and wants it under the
**same login**. Two supported flows:

1. **Provision a new org for the same owner.** A new `businesses` row is created
   with the *same* `owner_user_id`. Because `businesses.email` is `UNIQUE`, the
   second org must use a distinct billing email OR be linked without reusing the
   email as the PK-unique field (the hub link table, below, is what ties orgs to
   the identity — not the `businesses.email` column). In v1 the owner links an
   **existing** second portal they already own/manage (see 1.3); pure self-serve
   "spin up a blank location #2" is **stubbed** (documented in §8).
2. **Accept a membership** into an existing org (e.g. a franchisee joining a
   franchisor's hub) via a `business_users` row. This already works: one
   `auth.users` identity can hold many `business_users` rows.

Either way, the identity → org relationship is **many**. The
`identity_org_memberships` table (migration 060) records every org an identity
belongs to for the hub, with the role and how the membership was established
(owner vs invited staff), so the hub has one authoritative list to aggregate and
switch across without re-deriving it from two sources every request.

### 1.3 Connect & jump (linking portals under one identity)

From the hub the owner **connects** another Meridian portal they legitimately
control. "Legitimately control" means the server can independently verify the
identity is the org's `owner_user_id` **or** already has an active
`business_users` row for it. The connect endpoint:

- takes the target `org_id` from the **request body** but derives the acting
  identity from the **session JWT** (never the body — this repo has
  org_id-body-bypass history, PR #354);
- verifies membership server-side (owner or active business_user);
- upserts an `identity_org_memberships` row linking `user_id → org_id`.

**Jump** = switching active org context. The hub exposes a
`POST /api/hub/switch` that validates the target org is one the identity is a
member of, then returns the selected `org_id` as the new active context. The
frontend stores it as the active org (same mechanism the merchant portal already
uses — `useOrgId()` / `localStorage meridian_org`) and re-scopes every
subsequent API call to that org. **No re-login.** Because every data endpoint is
already tenant-scoped by `org_id` + `require_org_access` membership check,
switching to org B cannot expose org A's data and vice-versa — the switch only
changes which org_id is sent, and the server re-verifies membership for that
org_id on every call.

### 1.4 Unified Overview (hub dashboard)

A hub-only dashboard aggregating stats **across all connected locations the owner
belongs to**: revenue, orders, phone-agent performance, and scheduling/labor
where each portal surfaces them. It **reuses the existing per-org stat queries**
(`db.get_daily_revenue`, `db.get_phone_orders`, `db.get_phone_call_logs`) and
sums/compares across the owner's orgs **only** — the org list comes from the
session identity's memberships, never a caller-supplied list.

### 1.5 Franchise-level insights push-down

The owner deploys a config change from the hub down to **selected** locations,
with **per-branch confirm**. v1 wires two config types end to end:

- **`phone_fee_override`** — set the per-order Meridian fee override
  (`businesses.order_fee_override_cents`) across selected branches (respects the
  tier floor).
- **`chatbot_config`** — set the phone/website agent greeting/config blob
  (`businesses.phone_wizard_config` style field) across selected branches.

Each push:
- targets an explicit list of `org_id`s chosen by the owner;
- **filters that list to only orgs the identity actually owns/administers**
  (a branch the owner doesn't administer is dropped, not applied) — this is
  tested;
- returns a per-branch result (`applied` / `skipped_not_owned` / `error`) so the
  UI can show a per-branch confirmation.

Additional config types (pricing tables, schedule templates, phone-agent voice)
follow the same `PushDownConfig` extensible pattern and are **stubbed** with a
clear registration point (§8).

### 1.6 Command-tier activation

The entire hub — every `/api/hub/*` endpoint — is gated **server-side** to the
Command tier. A non-Command org receives **403** even if it forges the request or
hits the endpoint directly (UI hiding is not the control). The gate resolves tier
from the org record / locked billing contract, never the request body.

---

## 2. Billing implications per location

- **Each org bills independently.** `merchant_billing_terms` already keys the
  billing contract by `merchant_id` (= `businesses.id`), one active row per
  merchant. Adding a location = a new org = its own billing contract. The hub
  does **not** merge billing; it aggregates *reporting* only.
- The hub is a **Command-tier** entitlement. Only orgs on Command tier see it.
  A multi-location owner is expected to have the hub org (the one they operate
  from) on Command; individual branches may be on any tier but only Command orgs
  the identity belongs to can *open* the hub.
- Fee push-down respects each branch's tier floor (Command floor is lower than
  Premium — `fee_terms.py`), so a push that would set a fee below a branch's
  floor is clamped/rejected per branch.

---

## 3. Portal provisioning

- Location #2 is a standard org provision (`onboarding.provision_customer` /
  `canada.create_customer` / `us.create_customer`) with the same
  `owner_user_id`. No new provisioning path is introduced by the hub; the hub
  **links** already-provisioned orgs.
- After provisioning, the owner **connects** the new portal from the hub
  (§1.3), which records the `identity_org_memberships` row.

## 4. Staff / role separation per location

- Staff remain **per-org** via `business_users` (`role in owner|manager|staff`,
  optional `location_id`). The hub does **not** flatten staff across orgs — a
  manager at branch A is not automatically a manager at branch B.
- Only the **owner** identity (or an identity with an explicit membership in a
  branch) can push config to that branch. The push-down explicitly filters to
  owned/administered branches (§1.5).
- `identity_org_memberships.role` records the identity's role in each org for the
  hub's own authorization (who may push down, who may only view).

---

## 5. Data model (migration 060)

`identity_org_memberships`:

| column | type | notes |
|--------|------|-------|
| `id` | uuid PK | |
| `user_id` | uuid → auth.users | the identity |
| `org_id` | text → businesses.id | the org/location |
| `role` | text `owner\|admin\|manager\|viewer` | identity's hub role in this org |
| `is_owner` | boolean | true if `businesses.owner_user_id == user_id` |
| `connected_at` | timestamptz | when linked into the hub |
| `is_active` | boolean | soft-unlink |

- **Unique** `(user_id, org_id)` — one membership per identity per org.
- **RLS from day one:** an identity may `select` only its own membership rows
  (`user_id = auth.uid()`); the backend service role writes them after
  server-side verification. No policy lets an identity see another identity's
  memberships or insert a membership for an org it can't prove it belongs to.

## 6. Endpoints (all under `/api/hub`, all Command-tier gated, all
membership-from-session)

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/hub/orgs` | List orgs the session identity belongs to (the switcher) |
| POST | `/api/hub/connect` | Link an org (body `org_id`) the identity provably controls |
| POST | `/api/hub/switch` | Validate + return the selected active org (jump) |
| GET  | `/api/hub/overview` | Aggregated stats across the identity's orgs |
| POST | `/api/hub/push-down` | Deploy a config change to selected owned branches |

## 7. Isolation & security invariants (tested)

1. **Membership isolation** — an identity sees only orgs it is a member of;
   never another identity's orgs. (`/api/hub/orgs`, RLS + session resolution.)
2. **Org-switch re-scoping** — switching to org B never returns org A's data;
   the switch validates membership in B and the server re-checks membership per
   call. No A↔B leakage.
3. **Command-tier server-side gate** — a non-Command org hitting any `/api/hub/*`
   endpoint gets **403**, regardless of UI state or request body.
4. **Push-down ownership filter** — a push targeting branches the identity does
   not own/administer applies **only** to owned branches; unowned targets are
   dropped (`skipped_not_owned`).

## 8. Wired vs stubbed (v1)

| Capability | Status |
|------------|--------|
| Same-email multi-org model (migration 060 + RLS) | **wired** |
| `/api/hub/orgs` (switcher list from session) | **wired** |
| `/api/hub/connect` (link, membership-verified) | **wired** |
| `/api/hub/switch` (jump, re-scope) | **wired** |
| `/api/hub/overview` (revenue + orders + phone agg) | **wired** |
| `/api/hub/push-down` — `phone_fee_override` | **wired** |
| `/api/hub/push-down` — `chatbot_config` | **wired** |
| Command-tier server-side gate on all hub endpoints | **wired** |
| Self-serve "spin up blank location #2" | **stubbed** — owner provisions via existing flows then connects |
| Push-down — `pricing_table`, `schedule_template`, `phone_agent_voice` | **stubbed** — registered in `PUSH_DOWN_HANDLERS` with a `NotImplemented` marker; extensible pattern documented |
| Scheduling/labor + reviews in overview | **partial** — included when the portal surfaces them; revenue/orders/phone are the guaranteed columns |

## 9. Extensibility — adding a push-down config type

`src/api/routes/hub.py` defines a `PUSH_DOWN_HANDLERS` registry:
`{config_type: async handler(db, org_id, payload) -> "applied" | raises}`. To add
a new type, register a handler and add its id to the frontend push-down form. The
ownership filter, per-branch confirm, and tier gate are handled by the shared
`push_down` endpoint, so a new handler only implements the per-org write.
