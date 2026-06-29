-- US lead POS connection status.
--
-- The shared /api/onboarding/connect-pos + /verify-pos endpoints persist a
-- deal's POS connection on the lead row. Canada deals (`deals` table) already
-- have pos_system/pos_status; US leads (`us_leads`) did not, so the US lead
-- detail page's "Connect POS" action silently no-op'd and verify always
-- returned false. Add the two columns so US POS status actually persists.
--
-- US-only table; Canada (`deals`) is untouched.

ALTER TABLE us_leads ADD COLUMN IF NOT EXISTS pos_system text;
ALTER TABLE us_leads ADD COLUMN IF NOT EXISTS pos_status text;
