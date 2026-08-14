-- 078_ad_spot_orders.sql
-- 30-Second AI Advertisement (Aidan 2026-08-14) — the sold-deliverable record
-- behind the Setup Service the rep toggles in both portals.
--
-- WHY A TABLE AND NOT THE IN-MEMORY JOB DICT: the content studio's own clips
-- live in `_video_jobs`, a process-local dict, because a merchant's throwaway
-- 5-second clip can be re-rolled for pennies. This is different — the merchant
-- has PAID US$1,000 / CA$1,400 for a finished spot, the six shots take minutes
-- each, and a Railway redeploy mid-generation must not lose the order the rep
-- just closed. So the order and every shot are persisted.
--
-- The order is the unit of delivery; a shot is one generated clip. Assembly
-- (cut, voiceover, music, captions) happens on top of the completed shots and
-- is recorded back onto the order via delivered_url — the pipeline generates
-- the footage, it does not claim to have cut the final master.
--
-- ADDITIVE + idempotent: safe to run more than once. Run manually in the
-- Supabase SQL editor like every other migration here.

-- ═══════════════════════════════════════════════════════════════
-- 1. Orders — one row per sold spot
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS ad_spot_orders (
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
    contact_email     text,

    -- What was sold, in the currency it was sold in. Mirrors the setup-fee
    -- line the rep saw: US$1,000 → 100000, CA$1,400 → 140000.
    price_cents       integer NOT NULL CHECK (price_cents >= 0),
    currency          text NOT NULL CHECK (currency IN ('USD', 'CAD')),

    -- The brief the rep took on the call — this drives the storyboard.
    goal              text NOT NULL,
    highlights        text,
    brand_notes       text,
    placement         text NOT NULL,
    aspect_ratio      text,
    audio             text NOT NULL,

    -- Delivery state.
    --   boarding   → storyboard being written
    --   generating → shots submitted to the generation queue
    --   shots_ready→ every shot landed; awaiting the finishing cut
    --   assembling → the cut is running (ffmpeg: concat + VO + bed)
    --   assembled  → a master exists at master_url, awaiting human review
    --   delivered  → final master handed to the merchant
    --   failed     → boarding, generation or assembly failed; needs a human
    status            text NOT NULL DEFAULT 'boarding'
        CHECK (status IN ('boarding', 'generating', 'shots_ready', 'assembling',
                          'assembled', 'delivered', 'failed')),
    status_detail     text,
    storyboard        jsonb,

    -- The cut. master_url is what assembly produced; delivered_url is what a
    -- human signed off and handed over. They are usually the same file, and
    -- deliberately separate columns: an assembled master is NOT a delivery.
    master_url        text,
    assembled_at      timestamptz,
    assembly_notes    jsonb,
    delivered_url     text,
    delivered_at      timestamptz,

    -- Foundry Spot Sprint: every sold spot also opens a public 48-hour contest
    -- on the Foundry board, so the owner chooses between the house cut and
    -- creator entries instead of accepting whatever the queue produced.
    -- NULL job id + a detail line = the contest did not open (Foundry down,
    -- no contact email, or one already running); the spot still generates.
    foundry_job_id    text,
    foundry_detail    text
);

CREATE INDEX IF NOT EXISTS ad_spot_orders_org_idx    ON ad_spot_orders (org_id);
CREATE INDEX IF NOT EXISTS ad_spot_orders_rep_idx    ON ad_spot_orders (rep_id);
CREATE INDEX IF NOT EXISTS ad_spot_orders_status_idx ON ad_spot_orders (status);

-- ═══════════════════════════════════════════════════════════════
-- 2. Shots — one row per generated clip
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS ad_spot_shots (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id          uuid NOT NULL REFERENCES ad_spot_orders (id) ON DELETE CASCADE,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),

    shot_number       integer NOT NULL CHECK (shot_number >= 1),
    beat              text,
    prompt            text,
    model             text,
    duration_seconds  integer,

    status            text NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'generating', 'completed', 'failed')),
    video_url         text,
    error             text,

    -- Provider handles, so a stuck shot can be chased without re-billing.
    fal_request_id    text,
    fal_status_url    text,
    fal_response_url  text,

    UNIQUE (order_id, shot_number)
);

CREATE INDEX IF NOT EXISTS ad_spot_shots_order_idx ON ad_spot_shots (order_id);

-- ═══════════════════════════════════════════════════════════════
-- 3. RLS — service-role only, like every other rep-portal write path
-- ═══════════════════════════════════════════════════════════════
-- The API writes with the service-role key; no anon/authenticated policy is
-- granted, so an explicit-deny posture holds (075 doctrine). Reps read these
-- rows through the API, never through PostgREST directly.
ALTER TABLE ad_spot_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE ad_spot_shots  ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON ad_spot_orders FROM anon, authenticated;
REVOKE ALL ON ad_spot_shots  FROM anon, authenticated;

-- ═══════════════════════════════════════════════════════════════
-- 4. Storage bucket for the finished masters
-- ═══════════════════════════════════════════════════════════════
-- The assembly step uploads the cut MP4 here. PUBLIC on purpose: the merchant
-- is handed a link to a file they have paid for and will run as an ad, and
-- object names carry a random order id, so there is nothing to enumerate.
-- The API creates the bucket on first upload too — this line just makes a
-- fresh environment match a live one.
INSERT INTO storage.buckets (id, name, public)
VALUES ('ad-spots', 'ad-spots', true)
ON CONFLICT (id) DO NOTHING;
