-- Email delivery tracking — logs every outbound email via Postal
CREATE TABLE IF NOT EXISTS email_send_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id              TEXT,
    to_address          TEXT NOT NULL,
    template            TEXT NOT NULL,
    subject             TEXT NOT NULL,
    tag                 TEXT,
    status              TEXT NOT NULL DEFAULT 'pending',
    postal_message_id   TEXT,
    postal_status       TEXT,
    error_detail        TEXT,
    opened_at           TIMESTAMPTZ,
    clicked_at          TIMESTAMPTZ,
    bounced_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_email_log_org ON email_send_log(org_id);
CREATE INDEX IF NOT EXISTS idx_email_log_template ON email_send_log(template);
CREATE INDEX IF NOT EXISTS idx_email_log_status ON email_send_log(status);
CREATE INDEX IF NOT EXISTS idx_email_log_created ON email_send_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_log_postal_id ON email_send_log(postal_message_id);

ALTER TABLE email_send_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on email_send_log"
    ON email_send_log FOR ALL USING (true) WITH CHECK (true);
