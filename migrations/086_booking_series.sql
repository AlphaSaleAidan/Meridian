-- 086_booking_series.sql
-- RECURRING APPOINTMENTS — "same time, every four weeks".
--
-- A nail studio's whole economics are the fill every three weeks; a barber's
-- best customers are the ones who never ring because the slot is already
-- theirs. Today they hold that in a paper book or in their head, and the
-- appointment exists only because somebody remembered.
--
-- THE SERIES IS THE INTENTION; THE BOOKINGS ARE REAL ROWS. This is the whole
-- design decision. The alternative — storing a rule and computing occurrences
-- at read time — sounds tidier and is wrong here, because our double-booking
-- guarantee is a Postgres exclusion constraint over ACTUAL ROWS. A virtual
-- occurrence occupies nothing, so the phone agent would happily sell the same
-- chair to somebody else and both parties would be told yes.
--
-- So a series MATERIALISES a limited number of bookings ahead (generate_weeks),
-- each carrying series_id. Every one is a normal booking: it blocks the
-- resource, appears in the book, can be moved or cancelled on its own.
--
-- WHAT HAPPENS WHEN AN OCCURRENCE CANNOT BE PLACED. Somebody else has the
-- 2pm in three weeks' time. The generation does NOT fail the series and does
-- NOT bump the other booking — it records the skip and moves on, because a
-- recurring customer losing one week is recoverable and a walk-in being
-- silently evicted is not. The skipped date is surfaced so a human decides.
--
-- ADDITIVE + idempotent. Run manually in the Supabase SQL editor, after 085.

CREATE TABLE IF NOT EXISTS booking_series (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),

    merchant_id     text NOT NULL,
    service_id      uuid REFERENCES booking_services(id) ON DELETE SET NULL,

    -- Preferred, not guaranteed. A regular wants Marco; if Marco is off that
    -- week the engine may seat them elsewhere rather than skip the visit.
    resource_id     uuid REFERENCES booking_resources(id) ON DELETE SET NULL,
    resource_strict boolean NOT NULL DEFAULT false,

    customer_name   text NOT NULL,
    customer_phone  text,
    customer_email  text,
    party_size      integer NOT NULL DEFAULT 1 CHECK (party_size BETWEEN 1 AND 100),
    notes           text,

    -- The rule, deliberately NOT an RFC 5545 RRULE. Everything these trades
    -- actually book is "every N weeks on this weekday at this time", and a
    -- full RRULE engine would let a merchant express recurrences the booking
    -- engine cannot honour — monthly-by-position, yearly, count-limited — and
    -- then quietly not honour them.
    interval_weeks  integer NOT NULL DEFAULT 4
                    CHECK (interval_weeks BETWEEN 1 AND 26),
    weekday         smallint NOT NULL CHECK (weekday BETWEEN 0 AND 6),  -- 0=Sunday
    -- Local wall clock in the merchant's timezone, for the same reason
    -- booking_hours stores local time: a standing 2pm must stay 2pm across DST.
    local_time      time NOT NULL,

    starts_on       date NOT NULL,
    -- NULL = runs until cancelled, which is what a standing appointment is.
    ends_on         date,

    -- How far ahead to materialise. Small on purpose: a year of rows locks a
    -- calendar nobody has planned yet, and every one of them is a row somebody
    -- may have to move.
    generate_weeks  integer NOT NULL DEFAULT 12
                    CHECK (generate_weeks BETWEEN 1 AND 52),

    status          text NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'paused', 'cancelled')),

    last_generated_at timestamptz,
    -- Dates the engine could not place, so a human can decide rather than the
    -- customer silently losing a week.
    skipped_dates   date[] NOT NULL DEFAULT '{}'::date[]
);

CREATE INDEX IF NOT EXISTS booking_series_merchant_idx
    ON booking_series (merchant_id, status);
CREATE INDEX IF NOT EXISTS booking_series_due_idx
    ON booking_series (last_generated_at)
    WHERE status = 'active';
CREATE INDEX IF NOT EXISTS booking_series_phone_idx
    ON booking_series (merchant_id, customer_phone);

-- Which series an occurrence belongs to. NULL for every ordinary booking,
-- which is almost all of them.
ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS series_id uuid REFERENCES booking_series(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS bookings_series_idx
    ON bookings (series_id, starts_at) WHERE series_id IS NOT NULL;

-- One occurrence per series per date. The exclusion constraint stops two
-- bookings sharing a resource; this stops one series producing the same
-- Tuesday twice when generation runs more than once — which it will, because
-- it is a scheduled sweep.
-- Pinned to UTC on purpose. `starts_at::date` is STABLE, not IMMUTABLE — it
-- depends on the session TimeZone — so Postgres refuses it in an index
-- (42P17). `AT TIME ZONE 'UTC'` yields a plain timestamp and is immutable.
-- The date this collapses to is therefore the UTC date, which is exactly what
-- we want here: this index exists to stop ONE generation run producing the
-- same occurrence twice, and occurrences are generated from a single UTC
-- instant per date.
CREATE UNIQUE INDEX IF NOT EXISTS bookings_series_date_idx
    ON bookings (series_id, ((starts_at AT TIME ZONE 'UTC')::date))
    WHERE series_id IS NOT NULL AND status IN ('offered', 'confirmed', 'seated', 'completed');

ALTER TABLE booking_series ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON booking_series FROM anon, authenticated;

-- Per-merchant switch, off by default like every other capability here.
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS recurring_enabled boolean NOT NULL DEFAULT false;

COMMENT ON TABLE booking_series IS
    'The INTENTION to repeat. Occurrences are materialised as real bookings '
    'rows because the double-booking guarantee is an exclusion constraint over '
    'actual rows — a virtual occurrence occupies nothing and would let the '
    'phone agent sell the same chair twice.';

COMMENT ON COLUMN booking_series.skipped_dates IS
    'Dates that could not be placed because the resource was taken. The series '
    'never evicts an existing booking: a regular losing one week is '
    'recoverable, a walk-in being silently cancelled is not.';
