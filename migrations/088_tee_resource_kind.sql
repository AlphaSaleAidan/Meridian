-- 088: add 'tee' to the booking resource kinds.
--
-- The golf pack books tee times: a starting tee holds one group of up to four
-- players per interval, which is exactly the exclusion guarantee the engine
-- already makes — the tee is a resource kind, not a new engine. The CHECK
-- constraints from 081 pinned the kind list, so widening the list means
-- re-stating them.

ALTER TABLE booking_resources
    DROP CONSTRAINT IF EXISTS booking_resources_kind_check;
ALTER TABLE booking_resources
    ADD CONSTRAINT booking_resources_kind_check
    CHECK (kind IN ('table', 'staff', 'chair', 'bay', 'room', 'tee'));

ALTER TABLE booking_services
    DROP CONSTRAINT IF EXISTS booking_services_resource_kind_check;
ALTER TABLE booking_services
    ADD CONSTRAINT booking_services_resource_kind_check
    CHECK (resource_kind IN ('table', 'staff', 'chair', 'bay', 'room', 'tee'));
