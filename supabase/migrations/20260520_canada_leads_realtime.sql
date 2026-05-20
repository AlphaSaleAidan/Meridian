-- Enable Supabase Realtime on canada_leads for instant sync to support dashboards
ALTER TABLE canada_leads REPLICA IDENTITY FULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime' AND tablename = 'canada_leads'
  ) THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE canada_leads;
  END IF;
END $$;
