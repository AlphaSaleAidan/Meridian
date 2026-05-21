-- US Leads table — mirrors canada_leads structure for US sales portal
CREATE TABLE IF NOT EXISTS public.us_leads (
  id                  uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  business_name       text NOT NULL DEFAULT '',
  contact_name        text NOT NULL DEFAULT '',
  contact_email       text NOT NULL DEFAULT '',
  contact_phone       text DEFAULT '',
  vertical            text DEFAULT '',
  stage               text NOT NULL DEFAULT 'lead',
  monthly_value       numeric DEFAULT 0,
  commission_rate     numeric DEFAULT 0.70,
  expected_close_date text DEFAULT '',
  notes               text DEFAULT '',
  source              text DEFAULT '',
  city                text DEFAULT '',
  province            text DEFAULT '',
  rep_id              uuid REFERENCES public.sales_reps(id) ON DELETE SET NULL,
  created_at          timestamptz DEFAULT now(),
  updated_at          timestamptz DEFAULT now()
);

ALTER TABLE public.us_leads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on us_leads"
  ON public.us_leads FOR ALL
  USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_us_leads_rep_id   ON public.us_leads(rep_id);
CREATE INDEX IF NOT EXISTS idx_us_leads_stage    ON public.us_leads(stage);
CREATE INDEX IF NOT EXISTS idx_us_leads_created  ON public.us_leads(created_at DESC);

-- Enable realtime for the frontend subscription
ALTER PUBLICATION supabase_realtime ADD TABLE public.us_leads;
