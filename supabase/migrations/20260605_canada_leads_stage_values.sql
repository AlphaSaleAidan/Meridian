-- Expand canada_leads.stage CHECK constraint to the portal's full stage vocabulary.
--
-- The original constraint (20260507_canada_leads.sql) only permitted the legacy
-- seven stages:
--   prospecting, contacted, demo_scheduled, proposal_sent, negotiation,
--   closed_won, closed_lost
--
-- The refactored lead-detail pipeline writes the newer vocabulary
-- (proposal_shown, customer_checkout, customer_walkthrough, pos_connected,
-- appointment_set). Writing any of those violated the CHECK, so the
-- "Advance to Next Stage" button — and the proposal-shown auto-advance on
-- "Generate Proposal" — failed at the DB and appeared to do nothing.
--
-- Recreate the constraint as a superset covering both the legacy and current
-- stage values. The inline column constraint is auto-named canada_leads_stage_check.

alter table canada_leads drop constraint if exists canada_leads_stage_check;

alter table canada_leads add constraint canada_leads_stage_check
  check (stage in (
    -- legacy
    'prospecting', 'contacted', 'demo_scheduled', 'proposal_sent', 'negotiation',
    'closed_won', 'closed_lost',
    -- current portal pipeline
    'appointment_set', 'proposal_shown', 'customer_checkout',
    'customer_walkthrough', 'pos_connected'
  ));
