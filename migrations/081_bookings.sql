-- 081_bookings.sql
-- BOOKINGS — the phone agent can now take a reservation or an appointment,
-- not just an order.
--
-- Asked for by the Canada team (2026-08-14): restaurants want tables,
-- barbershops want chairs, detailers want bays. Until now "reservations" was
-- a PROMPT, not a system — src/api/routes/vapi_webhook.py:_reservation_block
-- told the agent to call submit_order with order_type='reservation' and stuff
-- the date, time and party size into a free-text notes field. Nothing checked
-- whether the restaurant was open, whether a table was free, or whether two
-- callers had just been promised the same 7pm. reservation_config on
-- phone_agent_config ({on_website, website_url}) is the only reservation data
-- that exists today, and it is NULL on every merchant in production.
--
-- THE ONE IDEA IN THIS SCHEMA: a table, a barber's chair, a detailing bay and
-- a named staff member are the same thing — a RESOURCE that holds exactly one
-- booking at a time. Model that once and every vertical works. A restaurant
-- table carries seats=4; a barber chair carries seats=1. Nothing else differs.
--
-- THE DOUBLE-BOOKING GUARANTEE IS THE DATABASE'S, NOT THE APP'S.
-- bookings_no_double_book below is a GiST exclusion constraint. Two callers on
-- two phone lines, a walk-in typed into the portal, and a synced Google
-- Calendar event cannot take the same resource at the same time no matter how
-- the race interleaves, because Postgres refuses the second write (SQLSTATE
-- 23P01) — the app layer catches that and offers the next slot instead. The
-- same construct is already proven in production in the Meridian Scheduler app.
-- An availability check in Python is a convenience for the caller experience;
-- it is NOT what makes the promise true.
--
-- Half-open ranges (tstzrange defaults to '[)') mean back-to-back bookings do
-- NOT collide: a 2:00–2:30 cut and a 2:30–3:00 cut both fit one chair. Turn
-- gaps belong in booking_services.buffer_minutes, which is baked into ends_at
-- at write time.
--
-- Verified against the live database 2026-08-14: PostgreSQL 17.6, btree_gist
-- available but NOT yet installed (this migration installs it — it is what
-- lets an exclusion constraint mix `=` on resource_id with `&&` on a range).
-- merchant_id is TEXT to match phone_agent_config.merchant_id, whose live
-- values are a mix of 'maple-tandoor-demo', 'biz_<hex>' and bare uuids. It is
-- deliberately NOT a foreign key, for the same reason 079 gave: bookings may
-- be configured against a merchant before every row exists elsewhere.
--
-- ADDITIVE + idempotent: safe to run more than once. Run manually in the
-- Supabase SQL editor like every other migration here.

CREATE EXTENSION IF NOT EXISTS btree_gist;

-- ═══════════════════════════════════════════════════════════════
-- booking_resources — the unit of capacity.
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS booking_resources (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),

    merchant_id   text NOT NULL,
    name          text NOT NULL,

    -- What the merchant calls it. Purely descriptive: the booking engine
    -- treats every kind identically. It drives the noun the phone agent
    -- speaks ("table" vs "chair" vs "bay") and the portal's labels.
    kind          text NOT NULL DEFAULT 'table'
                  CHECK (kind IN ('table', 'staff', 'chair', 'bay', 'room')),

    -- Party-size fit. 1 for a chair or a bay; 2/4/6 for a restaurant table.
    seats         integer NOT NULL DEFAULT 1 CHECK (seats BETWEEN 1 AND 100),

    -- Assignment preference: the engine picks the smallest fitting resource,
    -- breaking ties on sort_order, so merchants can keep the window table for
    -- walk-ins by sorting it last.
    sort_order    integer NOT NULL DEFAULT 0,

    active        boolean NOT NULL DEFAULT true,
    metadata      jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS booking_resources_merchant_idx
    ON booking_resources (merchant_id, active, seats);

-- ═══════════════════════════════════════════════════════════════
-- booking_services — what is being booked, and for how long.
--
-- A barbershop has real services ("Fade", 30 min, $35). A restaurant has one
-- pseudo-service per party band, which is how turn times get modelled without
-- a second mechanism: "Table for 1–4" 90 min, "Table for 5–8" 120 min. The
-- engine picks the service whose [min_party, max_party] contains the party.
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS booking_services (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),

    merchant_id       text NOT NULL,
    name              text NOT NULL,
    description       text,

    duration_minutes  integer NOT NULL CHECK (duration_minutes BETWEEN 5 AND 1440),

    -- Cleanup / turn time. Held against the resource (baked into ends_at) but
    -- never spoken to the caller as part of their appointment length.
    buffer_minutes    integer NOT NULL DEFAULT 0 CHECK (buffer_minutes BETWEEN 0 AND 240),

    price_cents       integer CHECK (price_cents >= 0),

    -- Which kind of resource this consumes; NULL means any active resource.
    resource_kind     text CHECK (resource_kind IN ('table', 'staff', 'chair', 'bay', 'room')),

    min_party         integer NOT NULL DEFAULT 1 CHECK (min_party >= 1),
    max_party         integer NOT NULL DEFAULT 1 CHECK (max_party >= 1),

    sort_order        integer NOT NULL DEFAULT 0,
    active            boolean NOT NULL DEFAULT true,

    CHECK (max_party >= min_party)
);

CREATE INDEX IF NOT EXISTS booking_services_merchant_idx
    ON booking_services (merchant_id, active, sort_order);

-- ═══════════════════════════════════════════════════════════════
-- booking_hours — when bookings may START, in the merchant's LOCAL time.
--
-- Authored local, stored local, evaluated against
-- phone_agent_config.business_timezone. Storing a wall-clock opening time as
-- UTC would silently shift the whole schedule twice a year at DST.
--
-- Overnight service is expressed as two rows (Fri 17:00–23:59 + Sat
-- 00:00–02:00), which is both semantically right — a 1am booking IS on
-- Saturday — and keeps slot generation trivially correct. The portal splits
-- it for the merchant; they never see the seam.
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS booking_hours (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at    timestamptz NOT NULL DEFAULT now(),

    merchant_id   text NOT NULL,
    weekday       smallint NOT NULL CHECK (weekday BETWEEN 0 AND 6),  -- 0=Sunday
    opens_at      time NOT NULL,
    closes_at     time NOT NULL,

    -- Slot granularity offered to callers ("7:00, 7:15, 7:30…").
    slot_minutes  integer NOT NULL DEFAULT 15 CHECK (slot_minutes BETWEEN 5 AND 240),

    active        boolean NOT NULL DEFAULT true,

    CHECK (closes_at > opens_at)
);

CREATE INDEX IF NOT EXISTS booking_hours_merchant_idx
    ON booking_hours (merchant_id, weekday, active);

-- ═══════════════════════════════════════════════════════════════
-- booking_closures — holidays, private events, a staff member's day off.
-- MERCHANT-AUTHORED. Externally-synced busy time lives in
-- booking_busy_blocks so a resync can never delete a merchant's own closure.
-- resource_id NULL = the whole business is closed.
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS booking_closures (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at    timestamptz NOT NULL DEFAULT now(),

    merchant_id   text NOT NULL,
    resource_id   uuid REFERENCES booking_resources(id) ON DELETE CASCADE,
    starts_at     timestamptz NOT NULL,
    ends_at       timestamptz NOT NULL,
    reason        text,

    CHECK (ends_at > starts_at)
);

CREATE INDEX IF NOT EXISTS booking_closures_range_idx
    ON booking_closures USING gist (tstzrange(starts_at, ends_at));
CREATE INDEX IF NOT EXISTS booking_closures_merchant_idx
    ON booking_closures (merchant_id, starts_at);

-- ═══════════════════════════════════════════════════════════════
-- booking_pacing_rules — restaurants only, and optional.
--
-- Table inventory alone lets all six tables book 7:00pm and drown the kitchen.
-- Real reservation systems cap COVERS per interval on top of table
-- availability. Barbershops and detailers simply have no rows here and the
-- pacing check is skipped entirely.
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS booking_pacing_rules (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at        timestamptz NOT NULL DEFAULT now(),

    merchant_id       text NOT NULL,
    weekday           smallint CHECK (weekday BETWEEN 0 AND 6),  -- NULL = every day
    starts_at         time NOT NULL,
    ends_at           time NOT NULL,
    max_covers        integer NOT NULL CHECK (max_covers > 0),
    interval_minutes  integer NOT NULL DEFAULT 15 CHECK (interval_minutes BETWEEN 5 AND 240),
    active            boolean NOT NULL DEFAULT true,

    CHECK (ends_at > starts_at)
);

CREATE INDEX IF NOT EXISTS booking_pacing_merchant_idx
    ON booking_pacing_rules (merchant_id, active);

-- ═══════════════════════════════════════════════════════════════
-- bookings — the reservation / appointment itself.
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS bookings (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now(),

    merchant_id        text NOT NULL,

    -- NOT NULL on purpose: an unassigned booking would slip past the
    -- exclusion constraint (NULL never conflicts) and silently reintroduce
    -- double-booking. ON DELETE RESTRICT so deleting a table cannot orphan a
    -- guest who is still expected tonight — the portal reassigns first.
    resource_id        uuid NOT NULL REFERENCES booking_resources(id) ON DELETE RESTRICT,
    service_id         uuid REFERENCES booking_services(id) ON DELETE SET NULL,

    -- ends_at INCLUDES the service buffer; duration_minutes is what the
    -- customer was told. Keeping both means a confirmation SMS can quote the
    -- honest appointment length while the resource stays blocked for cleanup.
    starts_at          timestamptz NOT NULL,
    ends_at            timestamptz NOT NULL,
    duration_minutes   integer CHECK (duration_minutes > 0),

    party_size         integer NOT NULL DEFAULT 1 CHECK (party_size BETWEEN 1 AND 100),

    customer_name      text NOT NULL,
    customer_phone     text,
    customer_email     text,
    notes              text,

    status             text NOT NULL DEFAULT 'confirmed'
                       CHECK (status IN ('confirmed', 'seated', 'completed',
                                         'cancelled', 'no_show')),

    source             text NOT NULL DEFAULT 'phone'
                       CHECK (source IN ('phone', 'sms', 'web', 'portal',
                                         'walk_in', 'provider', 'import')),

    -- Short, human-speakable, quoted back over the phone to cancel or move a
    -- booking. Deliberately not the uuid: nobody reads a uuid aloud.
    confirmation_code  text NOT NULL,

    -- Set when this booking is mirrored to/from an external tool.
    provider           text,
    provider_booking_id text,

    vapi_call_id       text,

    reminder_24h_sent_at timestamptz,
    reminder_2h_sent_at  timestamptz,
    cancelled_at       timestamptz,
    cancel_reason      text,

    CHECK (ends_at > starts_at)
);

-- ─── THE GUARANTEE ────────────────────────────────────────────
-- One resource cannot hold two live bookings that overlap in time. Cancelled
-- and no-show rows are excluded, so a cancellation immediately frees the slot
-- without deleting the history.
ALTER TABLE bookings DROP CONSTRAINT IF EXISTS bookings_no_double_book;
ALTER TABLE bookings
    ADD CONSTRAINT bookings_no_double_book
    EXCLUDE USING gist (
        merchant_id WITH =,
        resource_id WITH =,
        tstzrange(starts_at, ends_at) WITH &&
    ) WHERE (status IN ('confirmed', 'seated'));

-- One live confirmation code per merchant. Partial so that a cancelled
-- booking's code can be reissued years later without a collision.
CREATE UNIQUE INDEX IF NOT EXISTS bookings_confirmation_code_idx
    ON bookings (merchant_id, upper(confirmation_code))
    WHERE status IN ('confirmed', 'seated');

CREATE INDEX IF NOT EXISTS bookings_merchant_start_idx
    ON bookings (merchant_id, starts_at);
CREATE INDEX IF NOT EXISTS bookings_phone_idx
    ON bookings (merchant_id, customer_phone);
-- Drives the reminder sweep: only future, live bookings, cheaply.
CREATE INDEX IF NOT EXISTS bookings_reminder_idx
    ON bookings (starts_at)
    WHERE status = 'confirmed';

-- ═══════════════════════════════════════════════════════════════
-- booking_provider_connections — the merchant's EXISTING booking tool.
--
-- Most merchants already run something (Square Appointments, a Google
-- Calendar, an OpenTable page). Two-way where the vendor's API allows it,
-- read-only busy-import where it does not. A read-only connection is still
-- worth having: it stops the phone agent booking over a haircut that was
-- taken in the merchant's other system.
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS booking_provider_connections (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),

    merchant_id         text NOT NULL,
    provider            text NOT NULL,

    status              text NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'connected', 'error', 'disabled')),

    -- What this connection is actually allowed to do, which is a property of
    -- the VENDOR's API, not of our intent: 'read' = we import their busy time,
    -- 'write' = we push ours to them, 'both' = true two-way.
    direction           text NOT NULL DEFAULT 'read'
                        CHECK (direction IN ('read', 'write', 'both')),

    external_account_id text,

    -- AES-GCM via src/security/encryption.py. NEVER a plaintext token.
    credentials_encrypted text,

    config              jsonb NOT NULL DEFAULT '{}'::jsonb,
    last_sync_at        timestamptz,
    last_error          text
);

CREATE UNIQUE INDEX IF NOT EXISTS booking_provider_connections_unique_idx
    ON booking_provider_connections (merchant_id, provider);

-- ═══════════════════════════════════════════════════════════════
-- booking_busy_blocks — time imported FROM an external tool.
--
-- Separate from booking_closures so a resync can safely delete-and-replace
-- everything it owns without touching a closure the merchant typed in.
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS booking_busy_blocks (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    synced_at     timestamptz NOT NULL DEFAULT now(),

    merchant_id   text NOT NULL,
    connection_id uuid NOT NULL REFERENCES booking_provider_connections(id) ON DELETE CASCADE,
    resource_id   uuid REFERENCES booking_resources(id) ON DELETE CASCADE,

    starts_at     timestamptz NOT NULL,
    ends_at       timestamptz NOT NULL,
    external_id   text NOT NULL,
    summary       text,

    CHECK (ends_at > starts_at)
);

CREATE UNIQUE INDEX IF NOT EXISTS booking_busy_blocks_external_idx
    ON booking_busy_blocks (connection_id, external_id);
CREATE INDEX IF NOT EXISTS booking_busy_blocks_merchant_idx
    ON booking_busy_blocks (merchant_id, starts_at);

-- ═══════════════════════════════════════════════════════════════
-- Explicit-deny posture (075/080 doctrine): RLS ON with NO policy. The service
-- role bypasses RLS and is the only writer; anon and authenticated get
-- nothing. Adding a policy here would loosen it, not tighten it — so there
-- deliberately isn't one. Booking rows carry customer names and phone
-- numbers, which is exactly the data the 20260628 anon-exposure incident was
-- about.
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE booking_resources ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON booking_resources FROM anon, authenticated;

ALTER TABLE booking_services ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON booking_services FROM anon, authenticated;

ALTER TABLE booking_hours ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON booking_hours FROM anon, authenticated;

ALTER TABLE booking_closures ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON booking_closures FROM anon, authenticated;

ALTER TABLE booking_pacing_rules ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON booking_pacing_rules FROM anon, authenticated;

ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON bookings FROM anon, authenticated;

ALTER TABLE booking_provider_connections ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON booking_provider_connections FROM anon, authenticated;

ALTER TABLE booking_busy_blocks ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON booking_busy_blocks FROM anon, authenticated;

-- ═══════════════════════════════════════════════════════════════
-- phone_agent_config — turn the capability on per merchant.
--
-- reservations_enabled and reservation_platform already exist (added by
-- supabase/migrations/20260706_reservation_config.sql) and are NULL/false on
-- every live merchant, so they are free to take on their intended meaning
-- here rather than inventing parallel columns. What was missing is the choice
-- between "we book it for you" and "we read them the link".
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS booking_mode text NOT NULL DEFAULT 'off'
    CHECK (booking_mode IN ('off', 'native', 'external_link', 'provider'));

-- The noun the agent says out loud: "table", "chair", "bay", "appointment".
-- Set per merchant because a barbershop caller should never hear "table".
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS booking_noun text NOT NULL DEFAULT 'reservation';

-- Secret for the outbound .ics feed the merchant subscribes to in whatever
-- calendar they already use. This is the universal fallback for every tool we
-- cannot integrate with (Resy, Tock, Booksy, Vagaro, Fresha and the whole
-- detailing category publish no API at all), so it has to work without an
-- account, a login or a vendor agreement — which means the URL itself is the
-- credential. Calendar clients cannot send an Authorization header.
--
-- NULL until the merchant asks for the feed: no token, no public surface.
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS booking_feed_token text;

CREATE UNIQUE INDEX IF NOT EXISTS phone_agent_config_feed_token_idx
    ON phone_agent_config (booking_feed_token)
    WHERE booking_feed_token IS NOT NULL;

-- Booking is a distinct outcome from ordering: a barbershop's calls succeed by
-- filling a chair, not by selling food. Counting them in had_order would make
-- both numbers meaningless.
-- Guarded because voice_call_endings is one of the tables that was created
-- directly in Supabase rather than by a migration (it is in this repo's
-- KNOWN_RLS_MIGRATION_DRIFT set), so a from-scratch replay of migrations/
-- would not have it and a bare ALTER would abort the whole file.
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'voice_call_endings') THEN
        ALTER TABLE voice_call_endings ADD COLUMN IF NOT EXISTS had_booking boolean;
    END IF;
END $$;

COMMENT ON CONSTRAINT bookings_no_double_book ON bookings IS
    'The double-booking guarantee. Enforced by Postgres, not by application '
    'code: concurrent phone, portal and synced-calendar writes all fail here '
    'with SQLSTATE 23P01 rather than overbooking a resource.';
