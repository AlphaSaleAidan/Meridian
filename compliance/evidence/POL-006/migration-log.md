# Evidence — POL-006 — Supabase production migration log

Required by `compliance/policies/change-management.md` §4: every migration
applied to Supabase production is recorded here with the migration filename,
the date applied, who applied it, and a confirmation query showing the schema
change is live.

This log was created on 2026-08-09. Migrations applied before that date are not
recorded here — the policy prescribed this artifact but it had never been
created, which is itself a gap worth closing in the next evidence pass.

Project: `kbuzufjxwflrutowwnfl` (Meridian production).

---

## 076_phone_vocab_learning.sql

| Field | Value |
|---|---|
| Applied | 2026-08-09 |
| Applied by | Claude Code session, on Aidan Pierce's instruction |
| Method | Supabase Management API (`POST /v1/projects/{ref}/database/query`) |
| Code commit | `e4ccd4eb` — merged to `main` before apply |
| API deploy | Railway `Meridian` service `SUCCESS` before apply; health 200 throughout, zero non-200 samples |

**Change:** adds `phone_call_transcripts` and `phone_vocab_terms` for phone-agent
vocabulary learning. Additive only — two new tables, four new indexes, no
changes to existing objects. Both tables are backend-only and are explicitly
revoked from `anon` and `authenticated`; `phone_call_transcripts` holds caller
speech, so client reachability would be a privacy problem, not just a hygiene one.

**Confirmation queries (run post-apply):**

```sql
select table_name from information_schema.tables
 where table_schema='public'
   and table_name in ('phone_call_transcripts','phone_vocab_terms');
-- → phone_call_transcripts, phone_vocab_terms

select indexname from pg_indexes
 where tablename in ('phone_call_transcripts','phone_vocab_terms');
-- → idx_phone_call_transcripts_call,
--   idx_phone_call_transcripts_merchant_recent,
--   idx_phone_vocab_terms_approved,
--   idx_phone_vocab_terms_merchant_term,
--   + both pkeys

select grantee, table_name, privilege_type
  from information_schema.role_table_grants
 where table_name in ('phone_call_transcripts','phone_vocab_terms')
   and grantee in ('anon','authenticated');
-- → 0 rows (client roles hold no privileges on either table)
```

**Rollback:** `DROP TABLE phone_vocab_terms; DROP TABLE phone_call_transcripts;`
Safe at any point — no existing object depends on either table, and the code
paths that use them fail soft (transcript capture is wrapped and never affects a
call; the keyterm lookup returns `[]` on any error).
