-- 085_booking_deposits.sql
-- DEPOSITS — the thing four trades ask for by name.
--
-- A tattoo shop will not hold a four-hour sitting on a promise, a med spa
-- loses a $400 room to a no-show, and a nail studio's two-hour full set is
-- the appointment most likely to evaporate. All four trades ask the same
-- question in the first meeting: can you take a deposit.
--
-- WHY THIS IS CHEAP FOR US AND EXPENSIVE FOR THEM. Stripe Connect is already
-- live, and the no-show button already records the exact moment somebody did
-- not turn up. The missing piece was never the payment — it is the link
-- between "this booking needs money up front" and "that money should now be
-- taken", and that link is what this migration stores.
--
-- THE DEPOSIT IS A PROPERTY OF THE SERVICE, NOT THE MERCHANT. A barber who
-- wants $20 on a beard transplant does not want $20 on a fifteen-minute
-- neaten-up, and a policy that cannot tell them apart gets switched off. So
-- the requirement lives on booking_services and is COPIED onto the booking at
-- the moment it is taken — a merchant raising their deposit next month must
-- not silently change what an existing customer already agreed to.
--
-- STATUS IS EXPLICIT AND NEVER INFERRED. 'none' and 'not paid yet' are
-- different facts with different consequences: one is a booking that never
-- needed a deposit, the other is one that is not confirmed. Collapsing them
-- would let an unpaid booking read as a normal one.
--
-- ADDITIVE + idempotent. Run manually in the Supabase SQL editor, after 084.

-- ═══════════════════════════════════════════════════════════════
-- What a service asks for up front.
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE booking_services
    ADD COLUMN IF NOT EXISTS deposit_cents integer
    CHECK (deposit_cents IS NULL OR (deposit_cents >= 0 AND deposit_cents <= 10000000));

-- Percentage is how most shops actually think about it ("half up front"), and
-- it survives a price change without being re-typed. When both are set the
-- FLAT amount wins, because it is the more deliberate of the two.
ALTER TABLE booking_services
    ADD COLUMN IF NOT EXISTS deposit_percent integer
    CHECK (deposit_percent IS NULL OR (deposit_percent > 0 AND deposit_percent <= 100));

-- ═══════════════════════════════════════════════════════════════
-- What THIS booking agreed to.
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS deposit_cents integer
    CHECK (deposit_cents IS NULL OR deposit_cents >= 0);

ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS deposit_status text NOT NULL DEFAULT 'none'
    CHECK (deposit_status IN (
        'none',       -- this booking never needed one
        'requested',  -- link sent, nothing paid
        'held',       -- authorised or paid, sitting against the booking
        'captured',   -- kept, because they did not turn up
        'refunded',   -- released, because they did
        'failed',     -- the payment did not go through
        'waived'      -- the merchant let this one go
    ));

-- Stripe's id for whatever we created. Nullable because a waived or
-- never-required deposit has none, and because a link can be sent before a
-- PaymentIntent exists.
ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS deposit_payment_intent text;

ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS deposit_requested_at timestamptz;
ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS deposit_paid_at timestamptz;
ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS deposit_resolved_at timestamptz;

-- Drives "who has not paid yet" without scanning: the list a shop chases.
CREATE INDEX IF NOT EXISTS bookings_deposit_pending_idx
    ON bookings (merchant_id, starts_at)
    WHERE deposit_status = 'requested';

-- ═══════════════════════════════════════════════════════════════
-- The merchant's policy.
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS deposits_enabled boolean NOT NULL DEFAULT false;

-- Spoken by the agent and printed on the payment page. Stored rather than
-- generated, because this is a commitment to a customer and the merchant has
-- to be able to read the exact words they are making.
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS deposit_policy text;

-- How long a booking may sit unpaid before the slot goes back on the floor.
-- Without this an unpaid booking holds a chair for ever, which is the failure
-- mode deposits were supposed to fix.
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS deposit_hold_minutes integer NOT NULL DEFAULT 60
    CHECK (deposit_hold_minutes BETWEEN 5 AND 10080);

COMMENT ON COLUMN bookings.deposit_cents IS
    'Copied from the service at booking time, never read live. A merchant '
    'raising their deposit must not change what an existing customer agreed to.';

COMMENT ON COLUMN bookings.deposit_status IS
    'Explicit, never inferred. "none" (never needed one) and "requested" (not '
    'paid yet) are different facts — collapsing them lets an unpaid booking '
    'read as a normal one.';
