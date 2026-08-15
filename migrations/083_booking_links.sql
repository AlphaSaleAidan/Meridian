-- 083_booking_links.sql
-- THE LINK GOES BY TEXT, EVERY TIME — and we find out whether it worked.
--
-- Until now booking_mode='external_link' meant the prompt told the agent to
-- SPEAK a URL: "book online at maple-tandoor.ca/reservations". That is the
-- worst possible channel for a URL. The caller is usually driving or holding a
-- toddler, the agent has to spell out slashes and hyphens, a mis-heard
-- character sends them to a 404, and nobody can tell afterwards whether the
-- caller ever arrived. The merchant pays for a call that produced nothing they
-- can see.
--
-- Texting it fixes all four at once. The caller taps instead of transcribing,
-- the agent stops spelling, and because every text carries its own short code
-- we learn something the spoken version could never tell us: whether the link
-- was opened. That last part is why this table exists at all — a merchant on
-- external_link mode otherwise has NO evidence the phone agent did anything,
-- because the booking lands in somebody else's system.
--
-- ONE ROW PER TEXT, not one row per merchant link. Per-send codes are what
-- make click attribution exact: two callers on the same evening get different
-- codes for the same destination, so "opened" means a specific caller opened
-- it, not "somebody did". The merchant's own destination URL lives on
-- phone_agent_config, since there is exactly one of it.
--
-- The code is PUBLIC and unauthenticated by construction — it arrives in an
-- SMS and is tapped from a phone that has no session. It is therefore
-- deliberately not a secret and grants nothing: resolving one returns a 302 to
-- a URL the merchant publishes anyway. It must never become a key to anything
-- else.
--
-- ADDITIVE + idempotent. Run manually in the Supabase SQL editor, after 082.

-- ═══════════════════════════════════════════════════════════════
-- booking_link_sends — one outbound text, and what became of it.
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS booking_link_sends (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at     timestamptz NOT NULL DEFAULT now(),

    merchant_id    text NOT NULL,

    -- Short, URL-safe, case-insensitively unique. Resolved by GET /b/{code}.
    code           text NOT NULL,

    -- Snapshotted, NOT looked up at click time: a merchant changing their
    -- booking URL must not silently redirect links already sitting in
    -- someone's message history to a different destination.
    target_url     text NOT NULL,

    to_phone       text,
    vapi_call_id   text,

    -- 'sent' | 'failed' — whether the SMS provider accepted it. A landline
    -- caller lands here as failed, which is the signal the agent uses to fall
    -- back to reading the address out loud.
    delivery       text NOT NULL DEFAULT 'sent'
                   CHECK (delivery IN ('sent', 'failed')),
    error          text,

    clicked_at     timestamptz,
    click_count    integer NOT NULL DEFAULT 0 CHECK (click_count >= 0),
    last_clicked_at timestamptz
);

-- Case-insensitive: SMS clients and humans re-type codes in any case.
CREATE UNIQUE INDEX IF NOT EXISTS booking_link_sends_code_idx
    ON booking_link_sends (upper(code));

CREATE INDEX IF NOT EXISTS booking_link_sends_merchant_idx
    ON booking_link_sends (merchant_id, created_at DESC);

-- Drives the portal's "texted 31 · opened 22" counter without a scan.
CREATE INDEX IF NOT EXISTS booking_link_sends_clicked_idx
    ON booking_link_sends (merchant_id)
    WHERE clicked_at IS NOT NULL;

ALTER TABLE booking_link_sends ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON booking_link_sends FROM anon, authenticated;

-- ═══════════════════════════════════════════════════════════════
-- Where the link points.
--
-- reservation_config.website_url already holds this for merchants who
-- answered the onboarding questionnaire, and the link service falls back to
-- it. A dedicated column exists because reservation_config is questionnaire
-- output that onboarding may rewrite, and a merchant editing their booking URL
-- in the Bookings screen should not have it clobbered by an unrelated form.
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS booking_link_url text;

COMMENT ON TABLE booking_link_sends IS
    'One row per booking link texted to a caller. Per-send short codes make '
    'click attribution exact, which is the only evidence an external_link '
    'merchant ever gets that the phone agent produced a booking.';
