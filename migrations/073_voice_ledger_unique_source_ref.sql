-- 073: make voice_ledger idempotency race-safe.
--
-- voice_ledger._post() promises "idempotent on (source, ref)" but implements it
-- as SELECT-then-INSERT. The two Clover confirmation paths (per-merchant HCO
-- webhook + /pay/clover/return) can settle the same payment concurrently: both
-- pass the existence check, both insert, and the merchant is billed the fee
-- twice. This enforces the contract at the database; the racing INSERT then
-- fails with 23505, which PostgREST surfaces as 409 and supabase_rest already
-- treats as a non-error (same swallowed-conflict pattern as the uuid5
-- commission id from PR #415).

-- 1) Remove duplicate postings that already leaked (keep the earliest of each
--    set — same (source, ref) means the same real-world payment event).
DELETE FROM voice_ledger a
USING voice_ledger b
WHERE a.ref IS NOT NULL
  AND a.source = b.source
  AND a.ref = b.ref
  AND a.id > b.id;

-- 2) Enforce what the code assumed. Partial: ref-less postings (manual
--    adjustments) carry no idempotency key and stay unconstrained.
CREATE UNIQUE INDEX IF NOT EXISTS uq_voice_ledger_source_ref
    ON voice_ledger (source, ref)
    WHERE ref IS NOT NULL;
