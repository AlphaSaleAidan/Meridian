-- Seed data for Canada leads portal
-- Safe to re-run: uses ON CONFLICT DO NOTHING
-- Tagged with is_demo = true for clean filtering

-- Create canada_leads table if it doesn't exist
CREATE TABLE IF NOT EXISTS canada_leads (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  business_name TEXT NOT NULL,
  contact_name TEXT NOT NULL,
  contact_email TEXT NOT NULL DEFAULT '',
  contact_phone TEXT NOT NULL DEFAULT '',
  vertical TEXT NOT NULL DEFAULT '',
  stage TEXT NOT NULL DEFAULT 'prospecting',
  monthly_value INTEGER NOT NULL DEFAULT 0,
  commission_rate INTEGER NOT NULL DEFAULT 70,
  expected_close_date TEXT,
  notes TEXT DEFAULT '',
  source TEXT DEFAULT '',
  city TEXT DEFAULT '',
  province TEXT DEFAULT '',
  is_demo BOOLEAN DEFAULT false,
  created_at TEXT DEFAULT now()::text,
  updated_at TEXT DEFAULT now()::text
);

-- Enable RLS
ALTER TABLE canada_leads ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read/write canada_leads
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'canada_leads' AND policyname = 'canada_leads_read'
  ) THEN
    CREATE POLICY "canada_leads_read" ON canada_leads FOR SELECT USING (auth.role() = 'authenticated');
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'canada_leads' AND policyname = 'canada_leads_write'
  ) THEN
    CREATE POLICY "canada_leads_write" ON canada_leads FOR ALL USING (auth.role() = 'authenticated');
  END IF;
END $$;

-- Seed 10 demo leads
INSERT INTO canada_leads (id, business_name, contact_name, contact_email, contact_phone, vertical, stage, monthly_value, commission_rate, expected_close_date, notes, source, city, province, is_demo)
VALUES
  ('seed-golden-dragon', 'Golden Dragon Dim Sum', 'Kevin Lau', 'kevin@goldendragon.ca', '(604) 555-2345', 'Restaurant', 'prospecting', 685, 70, (CURRENT_DATE + INTERVAL '21 days')::text, 'High-volume dim sum spot in Richmond. 4 POS terminals, wants inventory tracking.', 'Referral', 'Richmond', 'BC', true),
  ('seed-cloud-nine-vape', 'Cloud Nine Vape YVR', 'Marcus Gill', 'marcus@cloudninevape.ca', '(604) 555-3456', 'Smoke Shop', 'contacted', 500, 70, (CURRENT_DATE + INTERVAL '14 days')::text, 'Currently on Clover. Wants anomaly detection for theft. 2 Vancouver locations.', 'Cold Call', 'Vancouver', 'BC', true),
  ('seed-kensington-coffee', 'Kensington Coffee House', 'Sarah Olsen', 'sarah@kensingtoncoffee.ca', '(403) 555-4567', 'Café', 'demo_scheduled', 343, 70, (CURRENT_DATE + INTERVAL '7 days')::text, 'Demo set for Thursday 2pm MST. Interested in predictive ordering for pastry inventory.', 'Website', 'Calgary', 'AB', true),
  ('seed-queen-west-threads', 'Queen West Threads', 'Priya Patel', 'priya@queenwestthreads.ca', '(416) 555-5678', 'Boutique', 'proposal_sent', 500, 70, (CURRENT_DATE + INTERVAL '5 days')::text, 'Sent Premium tier proposal. Owner reviewing with business partner.', 'Referral', 'Toronto', 'ON', true),
  ('seed-pilot-taphouse', 'The Pilot Taphouse', 'David Fong', 'david@pilottaphouse.ca', '(416) 555-6789', 'Bar', 'negotiation', 1000, 70, (CURRENT_DATE + INTERVAL '3 days')::text, 'Wants camera intelligence. 3 patios. Very close to signing.', 'Event', 'Toronto', 'ON', true),
  ('seed-chez-benny', 'Chez Benny Poutine', 'Benoît Tremblay', 'benoit@chezbenny.ca', '(514) 555-7890', 'Restaurant', 'closed_won', 343, 70, (CURRENT_DATE - INTERVAL '2 days')::text, 'Signed! Onboarding started. Moneris integration in progress.', 'Referral', 'Montreal', 'QC', true),
  ('seed-lux-hair', 'Lux Hair Studio', 'Tanya Chen', 'tanya@luxhair.ca', '(604) 555-8901', 'Salon', 'closed_won', 500, 70, (CURRENT_DATE - INTERVAL '10 days')::text, 'Active client. POS connected via Square Canada. First commission earned.', 'Website', 'Vancouver', 'BC', true),
  ('seed-maple-quick-mart', 'Maple Quick Mart', 'Ali Farah', 'ali@maplequickmart.ca', '(905) 555-9012', 'Convenience Store', 'closed_lost', 685, 70, (CURRENT_DATE - INTERVAL '5 days')::text, 'Went with competitor. Price was the deciding factor — revisit in 6 months.', 'Cold Call', 'Mississauga', 'ON', true),
  ('seed-taco-madre', 'Taco Madre', 'Maria Santos', 'maria@tacomadre.ca', '(403) 555-0123', 'Restaurant', 'prospecting', 500, 70, (CURRENT_DATE + INTERVAL '28 days')::text, 'Referral from Chez Benny. First call scheduled for next week.', 'Referral', 'Calgary', 'AB', true),
  ('seed-byward-smoke', 'Byward Smoke Co.', 'Kyle Bennett', 'kyle@bywardsmoke.ca', '(613) 555-1122', 'Smoke Shop', 'demo_scheduled', 343, 70, (CURRENT_DATE + INTERVAL '10 days')::text, 'Demo next Tuesday. Interested in anomaly detection for high-value inventory.', 'Website', 'Ottawa', 'ON', true)
ON CONFLICT (id) DO NOTHING;
