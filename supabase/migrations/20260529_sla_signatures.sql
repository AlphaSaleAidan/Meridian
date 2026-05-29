-- Customer SLA signatures — records that a Canadian customer agreed to the
-- service agreement (PIPEDA + Quebec Law 25 compliance language) during the
-- onboarding wizard. Required for legal contract execution.
--
-- Additive migration: safe to apply, reversible with DROP TABLE.

CREATE TABLE IF NOT EXISTS sla_signatures (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id text REFERENCES businesses(id) ON DELETE SET NULL,
  customer_email text NOT NULL,
  business_name text,
  signature_name text NOT NULL,
  province text,
  signed_at timestamptz NOT NULL DEFAULT now(),
  ip_address text,
  user_agent text,
  sla_version text DEFAULT 'v1',
  monthly_price_cad_cents integer,
  setup_fee_cad_cents integer DEFAULT 0,
  pos_system text,
  rep_id uuid REFERENCES sales_reps(id) ON DELETE SET NULL,
  rep_name text
);

CREATE INDEX IF NOT EXISTS sla_signatures_org_id_idx ON sla_signatures(org_id);
CREATE INDEX IF NOT EXISTS sla_signatures_email_idx ON sla_signatures(customer_email);
CREATE INDEX IF NOT EXISTS sla_signatures_signed_at_idx ON sla_signatures(signed_at DESC);

ALTER TABLE sla_signatures ENABLE ROW LEVEL SECURITY;

CREATE POLICY sla_signatures_owner_read ON sla_signatures FOR SELECT
  USING (
    auth.uid() IS NOT NULL AND (
      org_id IN (SELECT id FROM businesses WHERE owner_user_id = auth.uid())
      OR org_id IN (SELECT business_id FROM business_users WHERE user_id = auth.uid() AND is_active = true)
    )
  );

CREATE POLICY sla_signatures_authenticated_insert ON sla_signatures FOR INSERT
  WITH CHECK (auth.uid() IS NOT NULL);
