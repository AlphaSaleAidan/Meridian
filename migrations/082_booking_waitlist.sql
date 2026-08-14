-- 082_booking_waitlist.sql
-- CANCELLATION RECOVERY — the one thing no booking platform actually does.
--
-- Competitive research 2026-08-15 checked every incumbent's waitlist feature
-- and found the same pattern everywhere: a waitlist is A LIST A HUMAN WORKS.
-- Boulevard's "waitlist notifications" notify STAFF. Vagaro and SevenRooms
-- document waitlist management, not waitlist action. The consumer-side
-- versions are first-come "notify me" blasts. When a 7pm cancels at 4pm,
-- somebody has to notice, decide who to call, and call them — and on a busy
-- Friday nobody does, so the table goes empty.
--
-- That gap is unusually cheap for us and unusually expensive for them. We
-- already send SMS, already hold the merchant's calendar, and already see POS
-- spend. The incumbents' new AI voice agents (SevenRooms Voice AI, Fresha AI
-- Concierge, Mindbody, Slang.ai) are all INBOUND — they answer a call, they do
-- not place one.
--
-- WHY THE OFFER IS EXCLUSIVE AND EXPIRING.
-- The naive version texts everyone at once and gives the slot to whoever taps
-- first. That is a race that annoys everyone who loses it, and it teaches
-- regulars that the waitlist is a lottery. Instead an offer is made to ONE
-- guest at a time and the slot is genuinely held for them until
-- offer_expires_at. The hold is a real booking row in 'offered' status, so the
-- exclusion constraint from 081 protects it exactly like a confirmed booking
-- and nothing else can take it while they decide.
--
-- ORDER IS BY VALUE, NOT ARRIVAL — and honestly so. Ranking uses the guest's
-- own history where we have it and falls back to arrival order where we do
-- not, rather than inventing a score. booking_waitlist.rank_reason records
-- which applied, so a merchant asking "why did they get it?" gets an answer.
--
-- ADDITIVE + idempotent. Run manually in the Supabase SQL editor, after 081.

-- ═══════════════════════════════════════════════════════════════
-- booking_waitlist — who wants a slot that does not exist yet.
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS booking_waitlist (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),

    merchant_id       text NOT NULL,
    service_id        uuid REFERENCES booking_services(id) ON DELETE SET NULL,

    customer_name     text NOT NULL,
    customer_phone    text NOT NULL,
    party_size        integer NOT NULL DEFAULT 1 CHECK (party_size BETWEEN 1 AND 100),
    notes             text,

    -- The window they would accept, in real instants. A caller saying "Friday
    -- evening" becomes Friday 17:00–21:00 in the merchant's timezone at the
    -- point of capture, so matching later never has to re-guess what they meant.
    window_start      timestamptz NOT NULL,
    window_end        timestamptz NOT NULL,

    -- Their own limit. Someone who wants Friday 7pm does not want a text at
    -- 6:40pm about a table at 7pm; someone flexible does.
    min_notice_minutes integer NOT NULL DEFAULT 60
                       CHECK (min_notice_minutes BETWEEN 0 AND 10080),

    status            text NOT NULL DEFAULT 'waiting'
                      CHECK (status IN ('waiting', 'offered', 'booked',
                                        'declined', 'expired', 'cancelled')),

    source            text NOT NULL DEFAULT 'phone'
                      CHECK (source IN ('phone', 'sms', 'web', 'portal', 'walk_in')),

    -- Offer state. offer_booking_id points at the HELD booking row, so the
    -- hold and the offer can never disagree about which slot is reserved.
    offered_at        timestamptz,
    offer_expires_at  timestamptz,
    offer_booking_id  uuid REFERENCES bookings(id) ON DELETE SET NULL,
    offer_count       integer NOT NULL DEFAULT 0,
    -- Plain-English record of WHY this entry was ranked where it was, so a
    -- merchant asking "why them?" gets a real answer instead of "the algorithm".
    rank_reason       text,

    -- Short code the guest quotes or replies with to claim the slot.
    claim_code        text,

    vapi_call_id      text,

    CHECK (window_end > window_start)
);

CREATE INDEX IF NOT EXISTS booking_waitlist_match_idx
    ON booking_waitlist (merchant_id, status, window_start, window_end);
CREATE INDEX IF NOT EXISTS booking_waitlist_phone_idx
    ON booking_waitlist (merchant_id, customer_phone);
-- Drives the expiry sweep cheaply.
CREATE INDEX IF NOT EXISTS booking_waitlist_offer_expiry_idx
    ON booking_waitlist (offer_expires_at)
    WHERE status = 'offered';

CREATE UNIQUE INDEX IF NOT EXISTS booking_waitlist_claim_code_idx
    ON booking_waitlist (merchant_id, upper(claim_code))
    WHERE status = 'offered';

-- ═══════════════════════════════════════════════════════════════
-- bookings.'offered' — a real hold, not a soft reservation.
--
-- The exclusion constraint in 081 lists the statuses that occupy a resource.
-- 'offered' has to join them, or a held slot would be bookable by the phone
-- agent while the guest we just texted is still reading the message. This
-- REPLACES the constraint rather than adding a second one.
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE bookings DROP CONSTRAINT IF EXISTS bookings_no_double_book;
ALTER TABLE bookings
    DROP CONSTRAINT IF EXISTS bookings_status_check;
ALTER TABLE bookings
    ADD CONSTRAINT bookings_status_check
    CHECK (status IN ('offered', 'confirmed', 'seated', 'completed',
                      'cancelled', 'no_show'));

ALTER TABLE bookings
    ADD CONSTRAINT bookings_no_double_book
    EXCLUDE USING gist (
        merchant_id WITH =,
        resource_id WITH =,
        tstzrange(starts_at, ends_at) WITH &&
    ) WHERE (status IN ('offered', 'confirmed', 'seated'));

-- Which waitlist entry a held booking belongs to, so an expiring offer can
-- release exactly its own hold.
ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS waitlist_id uuid REFERENCES booking_waitlist(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS bookings_waitlist_idx
    ON bookings (waitlist_id) WHERE waitlist_id IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════
-- Per-merchant switch. OFF by default: texting a guest that a table opened
-- up is an outbound message sent on the merchant's behalf, and that is
-- theirs to opt into, not ours to assume.
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS waitlist_enabled boolean NOT NULL DEFAULT false;

-- How long a guest gets to claim before the offer moves on. Short enough that
-- a 4pm cancellation can still fill a 7pm table after two or three passes,
-- long enough that someone driving can pull over and reply.
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS waitlist_offer_minutes integer NOT NULL DEFAULT 15;

ALTER TABLE booking_waitlist ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON booking_waitlist FROM anon, authenticated;

COMMENT ON TABLE booking_waitlist IS
    'Guests waiting for a slot that does not exist yet. When a booking '
    'cancels, the best-matching entry is OFFERED the freed slot exclusively '
    'for a few minutes — the hold is a real bookings row in ''offered'' '
    'status, so the exclusion constraint protects it like any other booking.';
