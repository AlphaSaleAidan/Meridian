# Proposal: `user_profiles` consolidation (future slice — needs Nathan + migration/backfill)

Status: PROPOSED 2026-08-11 · Not in scope for `personal/nwong/user_port`
Related: [KOTLIN_USER_PORT_PLAN.md](../KOTLIN_USER_PORT_PLAN.md)

## Problem

Person-level data is scattered across four homes, one of which is untrustworthy:

- `auth.users.user_metadata` — display name, role. **User-writable**
  (`auth.updateUser({data})`), so nothing privileged can trust it. Can't add
  columns to `auth.users` (Supabase-managed).
- `business_users` — tenant memberships (person × business × role).
- `businesses.owner_user_id` — owner linkage lives on the business row.
- `admin_users` — platform-admin grant table.
- `sales_reps` — keyed by **email only, no `user_id`**: email changes break rep
  identity; SPA does string-matching lookups.

Audit metadata is near-absent: everything has `created_at` only; **no table has
`updated_at`/`updated_by`/`created_by`**. The Kotlin AuthController TODO already
anticipates a `user_profiles` table.

## Schema drift found while researching (flag regardless of this proposal)

`src/api/routes/team_admin.py` writes `business_users.invited_by / invited_at /
invite_status / permissions` and inserts into `business_user_audit` — **none of
these exist in `supabase/migrations/`**. They were evidently applied directly to
prod. The migrations dir does not reproduce the live schema.

## Proposed shape — profile + extensions (link, don't merge)

```
user_profiles                      -- ONE row per human; PK = auth.users id
  id uuid PK references auth.users(id)
  email text, display_name text, phone text
  created_at, created_by, updated_at (trigger), updated_by   -- the audit template
business_users.user_id  → FK user_profiles(id)   -- membership table, stays separate
sales_reps.user_id      → NEW FK user_profiles(id) (replaces email keying)
admin_users.user_id     → FK user_profiles(id)   -- stays a pure grant table
```

- `business_users` cannot merge in — one person, many businesses.
- `sales_reps` links, not merges — commission economics are sales-domain data.
- `admin_users` stays separate — tamper-proof allowlist (`user_metadata` roles are
  self-grantable; a service-role-only grant table is not).
- `user_profiles` becomes the standard-bearer for generic audit columns
  (`created_at/created_by/updated_at/updated_by`) going forward.

## Migration/backfill sketch (why this is its own slice)

1. Create `user_profiles` + trigger; backfill from `auth.users`
   (id/email/metadata display_name).
2. Add `sales_reps.user_id`, backfill by email join, keep email during transition.
3. Reconcile the drifted `business_users` columns + `business_user_audit` into
   real migration files first (prereq — otherwise local/staging diverge from prod).
4. Kotlin repos swap SQL inside the Impls only (`SalesRepRepository.existsActiveByEmail`
   → `existsActiveByUserId`); interfaces/services/controllers untouched — this is
   why user_port builds against current tables now.

## Decision needed from Nathan

Whether he wants this before or after the FastAPI decommission, and whether the
drifted prod schema gets reconciled into migrations as its own PR first
(recommended).
