-- Data marketplace sales log
CREATE TABLE IF NOT EXISTS data_sales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_email TEXT NOT NULL,
    product TEXT NOT NULL,
    amount_cents INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    download_url TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_data_sales_buyer ON data_sales(buyer_email);
CREATE INDEX IF NOT EXISTS idx_data_sales_product ON data_sales(product);
CREATE INDEX IF NOT EXISTS idx_data_sales_created ON data_sales(created_at DESC);

-- RLS
ALTER TABLE data_sales ENABLE ROW LEVEL SECURITY;
CREATE POLICY data_sales_service ON data_sales
    FOR ALL USING (auth.role() = 'service_role');
