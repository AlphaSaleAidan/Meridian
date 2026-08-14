-- 079_setup_service_work_orders.sql
-- ONE mechanism for every adder product (Aidan 2026-08-14):
--
--   the merchant PAYS  →  a work order is created  →  it is posted to the
--   Foundry dev marketplace  →  devs bid with actual work  →  the OWNER picks.
--
-- Before this, each adder invented its own path: Website Buildout fired a
-- Foundry contest from the browser at close, the 30-second spot fired one from
-- the API at close, and Custom CRM build fired nothing at all — it was a line
-- on an invoice and a promise. Any future adder would have invented a fourth
-- path. This table is the single record every adder shares.
--
-- TWO THINGS THIS DELIBERATELY CHANGES:
--
--   1. PAYMENT IS THE TRIGGER, NOT THE CLOSE. A work order is recorded when
--      the rep closes, but it is not posted to the marketplace until the money
--      arrives (checkout.session.completed). Devs should never do spec work
--      against a deal that never paid. Set SETUP_SERVICE_POST_ON_CLOSE=1 to
--      keep the old close-time behavior while the switch is being watched.
--   2. EVERY adder is postable, including ones with no automation behind them.
--      Custom CRM build has no generator; it does not need one — it needs a
--      brief, a price, and developers who want the work.
--
-- ADDITIVE + idempotent: safe to run more than once. Run manually in the
-- Supabase SQL editor like every other migration here.

CREATE TABLE IF NOT EXISTS setup_service_orders (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),

    -- org_id is the APP's org id, which is businesses.id — TEXT, not a uuid
    -- (verified against the live schema 2026-08-14; the CPA migration once
    -- declared uuid→organizations and died on `text = uuid`). Nullable and
    -- deliberately NOT a foreign key: a service can be sold against a lead
    -- before the org is ever provisioned.
    org_id            text,
    market            text NOT NULL CHECK (market IN ('us', 'ca')),
    lead_id           uuid,
    rep_id            text,
    rep_name          text,
    business_name     text NOT NULL,
    business_type     text,
    contact_name      text,
    contact_email     text,

    -- Which adder. Kinds live in src/services/setup_services.py — adding one
    -- there is the whole job of adding a new sellable service.
    service_kind      text NOT NULL,
    service_label     text NOT NULL,

    -- What was sold, in the currency it was sold in.
    price_cents       integer NOT NULL CHECK (price_cents >= 0),
    currency          text NOT NULL CHECK (currency IN ('USD', 'CAD')),

    -- The rep's intake, verbatim. Shape varies by kind — this IS the brief the
    -- developers bid against, so it is stored whole rather than flattened.
    brief             jsonb NOT NULL DEFAULT '{}'::jsonb,

    -- Money. 'waived' covers comped work and internal builds — it posts like a
    -- paid order because the developer is doing real work either way.
    payment_status    text NOT NULL DEFAULT 'awaiting_payment'
        CHECK (payment_status IN ('awaiting_payment', 'paid', 'waived')),
    paid_at           timestamptz,
    stripe_session_id text,

    -- Marketplace state.
    --   awaiting_payment → recorded at close, not yet posted
    --   posting          → being posted to the Foundry board
    --   posted           → live on the board, devs can submit
    --   awarded          → the owner picked; work is being bought
    --   delivered        → handed over
    --   failed           → posting failed; needs a human (never silent)
    status            text NOT NULL DEFAULT 'awaiting_payment'
        CHECK (status IN ('awaiting_payment', 'posting', 'posted',
                          'awarded', 'delivered', 'failed')),
    status_detail     text,
    foundry_job_id    text,
    posted_at         timestamptz
);

CREATE INDEX IF NOT EXISTS setup_service_orders_org_idx     ON setup_service_orders (org_id);
CREATE INDEX IF NOT EXISTS setup_service_orders_rep_idx     ON setup_service_orders (rep_id);
CREATE INDEX IF NOT EXISTS setup_service_orders_status_idx  ON setup_service_orders (status);
CREATE INDEX IF NOT EXISTS setup_service_orders_kind_idx    ON setup_service_orders (service_kind);
CREATE INDEX IF NOT EXISTS setup_service_orders_session_idx ON setup_service_orders (stripe_session_id);

-- An org cannot have two live orders of the same service — a second one is a
-- double-submit from the portal, not a second purchase.
CREATE UNIQUE INDEX IF NOT EXISTS setup_service_orders_live_uniq
    ON setup_service_orders (org_id, service_kind)
    WHERE org_id IS NOT NULL AND status IN ('awaiting_payment', 'posting', 'posted');

-- Service-role only, like every other rep-portal write path (075 doctrine).
ALTER TABLE setup_service_orders ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON setup_service_orders FROM anon, authenticated;
