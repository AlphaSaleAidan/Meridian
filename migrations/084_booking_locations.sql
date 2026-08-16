-- 084_booking_locations.sql
-- WHERE THE WORK HAPPENS — mobile trades.
--
-- Every trade so far books a thing at a place: a table in the dining room, a
-- chair in the shop, a bay in the unit. A mobile detailer, a mobile groomer
-- and every home-services trade book a thing at THE CUSTOMER'S place, and that
-- breaks two assumptions the booking engine currently makes.
--
-- 1. A booking has no location. It does not need one when the location is the
--    shop. It is the single most important field when it is not — a job with
--    no address is a job nobody can drive to.
--
-- 2. booking_services.buffer_minutes is a CONSTANT. For a shop that is right:
--    fifteen minutes to turn a table, five to sweep up. For a mobile trade the
--    gap after a job is not a property of the job at all — it is the drive to
--    wherever the next one is, which depends on a booking that may not exist
--    yet. Hence travel_minutes here, stored per booking rather than derived at
--    read time, so the day's plan does not silently change when a routing
--    service is slow or unavailable.
--
-- COORDINATES ARE STORED, NOT LOOKED UP REPEATEDLY. Geocoding is rate-limited
-- and costs money; a booking's address does not move. Resolve once on write,
-- keep the result, and treat a null lat/lng as "not geocoded yet" rather than
-- "no address" — the two need different handling in the UI and conflating them
-- would hide failures.
--
-- ADDITIVE + idempotent. Run manually in the Supabase SQL editor, after 083.

ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS service_address text;

-- Geocoded from service_address. NULL means not resolved yet — which is a
-- state the route view has to show honestly, because a stop it cannot place
-- is a stop the owner still has to drive to.
ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS service_lat double precision;
ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS service_lng double precision;

-- Estimated drive TO this booking from the previous one in the day. Written
-- when the day is planned, not computed on every read: a route that rearranges
-- itself because a maps API was slow is worse than one that is slightly stale.
ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS travel_minutes integer
    CHECK (travel_minutes IS NULL OR (travel_minutes >= 0 AND travel_minutes <= 600));

-- Does this merchant go to the customer? Drives whether the agent asks for an
-- address at all, and whether the day is drawn as a grid or as a route.
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS booking_travels boolean NOT NULL DEFAULT false;

-- How far the merchant is willing to drive. A mobile detailer in one suburb
-- and one covering a whole county need different answers to "can you do
-- Thursday", and without this the agent says yes to both.
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS service_radius_km integer
    CHECK (service_radius_km IS NULL OR (service_radius_km > 0 AND service_radius_km <= 500));

-- Where the day starts and ends — the shop, or the owner's driveway. Without
-- an origin the first leg of every route is unknown.
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS base_address text;
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS base_lat double precision;
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS base_lng double precision;

-- Drives the route view for one day without scanning the table.
CREATE INDEX IF NOT EXISTS bookings_travel_idx
    ON bookings (merchant_id, starts_at)
    WHERE service_address IS NOT NULL;

COMMENT ON COLUMN bookings.travel_minutes IS
    'Estimated drive to this booking from the previous stop, written when the '
    'day is planned. NOT a service buffer: buffer_minutes is a property of the '
    'work, this is a property of the gap between two jobs.';
