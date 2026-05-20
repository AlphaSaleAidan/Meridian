-- Inventory document uploads for AI processing
CREATE TABLE IF NOT EXISTS inventory_document_uploads (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  file_name text NOT NULL,
  file_path text NOT NULL,
  file_type text,
  status text NOT NULL DEFAULT 'pending_processing'
    CHECK (status IN ('pending_processing', 'processing', 'completed', 'failed')),
  extracted_data jsonb,
  error_message text,
  processed_at timestamptz,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_inv_docs_org ON inventory_document_uploads(org_id);
CREATE INDEX IF NOT EXISTS idx_inv_docs_status ON inventory_document_uploads(status);

ALTER TABLE inventory_document_uploads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own org docs" ON inventory_document_uploads
  FOR SELECT USING (
    org_id IN (SELECT id FROM organizations WHERE email = auth.jwt() ->> 'email')
  );

CREATE POLICY "Users can insert own org docs" ON inventory_document_uploads
  FOR INSERT WITH CHECK (
    org_id IN (SELECT id FROM organizations WHERE email = auth.jwt() ->> 'email')
  );

-- Storage bucket for inventory documents
INSERT INTO storage.buckets (id, name, public)
VALUES ('inventory-docs', 'inventory-docs', false)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "Org users can upload inventory docs" ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'inventory-docs'
    AND (storage.foldername(name))[1] IN (
      SELECT id::text FROM organizations WHERE email = auth.jwt() ->> 'email'
    )
  );

CREATE POLICY "Org users can view own inventory docs" ON storage.objects
  FOR SELECT USING (
    bucket_id = 'inventory-docs'
    AND (storage.foldername(name))[1] IN (
      SELECT id::text FROM organizations WHERE email = auth.jwt() ->> 'email'
    )
  );
