-- ============================================================
-- 049: SUBSCRIPTION CANCELLATION RECORD (owner self-serve cancel)
-- ============================================================
-- Workstream 4 — Cancel Subscription / Cancel Account.
--
-- Migration 023 only ADDs the 'cancel_pending' enum value used by the
-- OPERATOR-driven billing_service.cancel_subscription() when the Square
-- cancel fails. It does NOT record WHO cancelled, WHEN, or WHY, and it has
-- no notion of the "talk to us first" retention step or an access-wind-down
-- lifecycle. This migration is ADDITIVE and does not alter 023's semantics:
-- it adds an append-only audit table for merchant-owner-initiated
-- cancellation, plus the status-transition columns the wind-down policy needs.
--
-- Nothing here cuts a live merchant off. The access-wind-down transitions
-- are RECORDED only; the API gates the actual access change behind
-- SUBSCRIPTION_WINDDOWN_ENFORCED (default off — "record only") so Aidan
-- signs off before any deactivation touches a live account.
--
-- COMMISSION HALT: on cancel we emit a row here; wiring to
-- commission_engine.cancel_account() (feat/canada-commission-engine,
-- migration 046, commission_milestones) happens when both branches land.
-- We deliberately do NOT import or touch commission_milestones from here.
-- ============================================================

-- Append-only cancellation audit log. One row per cancellation REQUEST.
-- "talk to us first" is a distinct outcome that records NO cancellation —
-- so the only rows in this table are genuine cancellations.
CREATE TABLE IF NOT EXISTS public.subscription_cancellations (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id              text NOT NULL,

    -- who pressed the button (owner of the org, from session — never body)
    canceled_by_user_id text NOT NULL DEFAULT '',
    canceled_by_email   text NOT NULL DEFAULT '',

    -- optional free-text reason captured in the flow (may be empty)
    reason              text NOT NULL DEFAULT '',

    -- when the cancel was recorded (authoritative timestamp)
    canceled_at         timestamptz NOT NULL DEFAULT now(),

    -- ── access wind-down lifecycle (RECORDED here; enforcement gated) ──
    -- Proposed policy (flagged for Aidan in the PR):
    --   full access to end of paid period
    --   -> 30-day read-only export window
    --   -> deactivation.
    -- 'recorded'  = cancel captured, no access change yet (conservative default)
    -- 'active_until_period_end' = still full access, will not renew
    -- 'read_only' = paid period ended, 30-day export window open
    -- 'deactivated' = wind-down complete, access removed
    winddown_status     text NOT NULL DEFAULT 'recorded'
                        CHECK (winddown_status IN (
                            'recorded',
                            'active_until_period_end',
                            'read_only',
                            'deactivated'
                        )),
    access_until        timestamptz,   -- end of paid period (full access through)
    read_only_until     timestamptz,   -- end of the 30-day export window

    -- commission-halt hook bookkeeping: set true once the cancel event has
    -- been (or will be) handed to the commission engine. Until the engines
    -- land together it stays false and the PR documents the wiring point.
    commission_halt_requested boolean NOT NULL DEFAULT false,

    metadata            jsonb NOT NULL DEFAULT '{}',
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sub_cancel_org
    ON public.subscription_cancellations(org_id);
CREATE INDEX IF NOT EXISTS idx_sub_cancel_winddown
    ON public.subscription_cancellations(winddown_status);

-- ============================================================
-- RLS — service role writes ONLY (the cancel endpoint uses the service
-- key after verifying the caller is the OWNER of the org). Members may
-- READ their own org's cancellation record so the UI can reflect state.
-- ============================================================
ALTER TABLE public.subscription_cancellations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Members read own org cancellations"
    ON public.subscription_cancellations;
CREATE POLICY "Members read own org cancellations"
  ON public.subscription_cancellations FOR SELECT
  TO authenticated
  USING (
    org_id IN (
      SELECT id::text FROM public.businesses WHERE owner_user_id = auth.uid()
      UNION
      SELECT business_id::text FROM public.business_users
        WHERE user_id = auth.uid() AND is_active
    )
  );
