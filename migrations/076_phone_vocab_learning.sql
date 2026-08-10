-- 076: Phone agent vocabulary learning — hear the words this store's callers
--      actually use.
--
-- Every Vapi end-of-call-report already carries the full conversation in
-- `artifact.messages`; today it is scanned once for a submit_order tool call
-- and then discarded. These two tables keep it and distil it, so the
-- transcriber can be primed with the proper nouns a given store and its
-- neighbourhood actually say — menu items pronounced unlike their menu
-- spelling, street and area names, regulars' phrasings.
--
-- Nothing here touches the call prompt. Recognition is improved by feeding
-- learned terms to Deepgram as keyterms; the agent's script is untouched,
-- which matters because prompt rewrites have regressed this agent before.

-- 1) Raw caller turns, per call. Only what the CALLER said is retained: the
--    assistant's own lines teach us nothing about local vocabulary and would
--    just bias the miner toward the script's own wording.
CREATE TABLE IF NOT EXISTS phone_call_transcripts (
    id            UUID PRIMARY KEY,
    merchant_id   TEXT NOT NULL,
    vapi_call_id  TEXT,
    caller_text   TEXT NOT NULL,
    turn_count    INTEGER NOT NULL DEFAULT 0,
    had_order     BOOLEAN,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One row per call. Vapi retries the end-of-call report, and a retry must not
-- double-count a term's frequency in the miner.
CREATE UNIQUE INDEX IF NOT EXISTS idx_phone_call_transcripts_call
    ON phone_call_transcripts (vapi_call_id)
    WHERE vapi_call_id IS NOT NULL;

-- The miner's query shape: one merchant's recent calls.
CREATE INDEX IF NOT EXISTS idx_phone_call_transcripts_merchant_recent
    ON phone_call_transcripts (merchant_id, created_at DESC);

-- 2) The distilled vocabulary. `status` is the human gate: a term is mined as
--    'candidate' and only reaches the transcriber once someone approves it, so
--    a bad mining run can never reach a live call on its own.
CREATE TABLE IF NOT EXISTS phone_vocab_terms (
    id            UUID PRIMARY KEY,
    merchant_id   TEXT NOT NULL,
    term          TEXT NOT NULL,
    occurrences   INTEGER NOT NULL DEFAULT 1,
    source        TEXT NOT NULL DEFAULT 'transcript',
    status        TEXT NOT NULL DEFAULT 'candidate',
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Case-insensitive uniqueness per merchant: "Bayview" and "bayview" are the
-- same term and must accumulate onto one row, not compete as two.
CREATE UNIQUE INDEX IF NOT EXISTS idx_phone_vocab_terms_merchant_term
    ON phone_vocab_terms (merchant_id, lower(term));

-- Hot path: the approved list for one merchant, strongest first.
CREATE INDEX IF NOT EXISTS idx_phone_vocab_terms_approved
    ON phone_vocab_terms (merchant_id, status, occurrences DESC);

-- Backend-only tables: no client ever reads these directly, and transcripts in
-- particular are caller speech. Explicit deny at the grant layer, matching the
-- defence-in-depth pattern established in 075.
REVOKE ALL ON public.phone_call_transcripts FROM anon, authenticated;
REVOKE ALL ON public.phone_vocab_terms FROM anon, authenticated;
