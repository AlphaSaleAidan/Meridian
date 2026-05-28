-- Meridian Content System — AI social, SEO, and publishing engine
-- Tables: content_brands, content_calendars, content_posts, content_rankings, content_jobs

-- ── content_brands ──────────────────────────────────────────────────────────
CREATE TABLE content_brands (
  id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id                 UUID NOT NULL REFERENCES business_accounts(id) ON DELETE CASCADE,
  business_name               TEXT NOT NULL,
  business_type               TEXT NOT NULL
    CHECK (business_type IN ('restaurant','retail','auto_shop','cannabis','coffee_shop','fast_food','smoke_shop')),
  website_url                 TEXT,

  voice_profile               JSONB NOT NULL DEFAULT '{}',

  post_tone                   TEXT DEFAULT 'professional',
  auto_publish                BOOLEAN DEFAULT FALSE,
  approval_email              TEXT,

  content_tier                TEXT DEFAULT NULL
    CHECK (content_tier IN ('starter','growth','command')),
  tier_activated_at           TIMESTAMPTZ,

  google_tokens               JSONB,
  gmb_location_id             TEXT,
  gsc_site_url                TEXT,

  ayrshare_profile_key        TEXT,
  ayrshare_connected_platforms JSONB DEFAULT '[]',

  wp_site_url                 TEXT,
  wp_app_password             TEXT,
  wp_author_id                INTEGER DEFAULT 1,

  created_at                  TIMESTAMPTZ DEFAULT NOW(),
  updated_at                  TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE (merchant_id)
);

ALTER TABLE content_brands ENABLE ROW LEVEL SECURITY;
CREATE POLICY "merchant_own_brand" ON content_brands
  FOR ALL USING (merchant_id = auth.uid());
CREATE INDEX idx_content_brands_merchant ON content_brands (merchant_id);

-- ── content_calendars ───────────────────────────────────────────────────────
CREATE TABLE content_calendars (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id     UUID NOT NULL REFERENCES business_accounts(id) ON DELETE CASCADE,
  week_start      DATE NOT NULL,
  status          TEXT DEFAULT 'draft'
    CHECK (status IN ('draft','approved','active','completed')),

  plan            JSONB NOT NULL DEFAULT '[]',

  pos_snapshot    JSONB,
  foot_traffic_peak TEXT,

  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE (merchant_id, week_start)
);

ALTER TABLE content_calendars ENABLE ROW LEVEL SECURITY;
CREATE POLICY "merchant_own_calendar" ON content_calendars
  FOR ALL USING (merchant_id = auth.uid());
CREATE INDEX idx_content_calendars_merchant ON content_calendars (merchant_id);
CREATE INDEX idx_content_calendars_week ON content_calendars (merchant_id, week_start);

-- ── content_posts ───────────────────────────────────────────────────────────
CREATE TABLE content_posts (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id         UUID NOT NULL REFERENCES business_accounts(id) ON DELETE CASCADE,
  calendar_id         UUID REFERENCES content_calendars(id),

  post_type           TEXT NOT NULL
    CHECK (post_type IN ('social','article','video_brief','gmb_post','ad_creative')),
  platform            TEXT,

  title               TEXT,
  body                TEXT,
  hook                TEXT,
  hashtags            TEXT[],
  call_to_action      TEXT,

  image_url           TEXT,
  video_url           TEXT,
  image_prompt        TEXT,

  target_keyword      TEXT,
  secondary_keywords  TEXT[],
  meta_description    TEXT,
  slug                TEXT,
  word_count          INTEGER,

  status              TEXT DEFAULT 'generating'
    CHECK (status IN (
      'generating','draft','needs_review','approved',
      'scheduled','published','failed','rejected'
    )),
  scheduled_at        TIMESTAMPTZ,
  published_at        TIMESTAMPTZ,
  publish_url         TEXT,
  ayrshare_post_id    TEXT,
  wp_post_id          INTEGER,

  model_used          TEXT,
  generation_cost_cents NUMERIC(10,4),

  pos_data_reference  JSONB,

  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE content_posts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "merchant_own_posts" ON content_posts
  FOR ALL USING (merchant_id = auth.uid());
CREATE INDEX idx_content_posts_merchant_status
  ON content_posts (merchant_id, status);
CREATE INDEX idx_content_posts_merchant_scheduled
  ON content_posts (merchant_id, scheduled_at);
CREATE INDEX idx_content_posts_merchant_type
  ON content_posts (merchant_id, post_type);

-- ── content_rankings ────────────────────────────────────────────────────────
CREATE TABLE content_rankings (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id     UUID NOT NULL REFERENCES business_accounts(id) ON DELETE CASCADE,
  checked_at      TIMESTAMPTZ DEFAULT NOW(),

  keyword         TEXT NOT NULL,
  location_code   INTEGER DEFAULT 2840,
  language_code   TEXT DEFAULT 'en',

  rank_position   INTEGER,
  rank_absolute   INTEGER,
  url_ranked      TEXT,
  serp_features   TEXT[],

  ai_citation_count   INTEGER DEFAULT 0,
  ai_platforms_cited  TEXT[],

  rank_change     INTEGER DEFAULT 0,

  UNIQUE (merchant_id, keyword, (checked_at::DATE))
);

ALTER TABLE content_rankings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "merchant_own_rankings" ON content_rankings
  FOR ALL USING (merchant_id = auth.uid());
CREATE INDEX idx_content_rankings_merchant_keyword
  ON content_rankings (merchant_id, keyword);
CREATE INDEX idx_content_rankings_merchant_date
  ON content_rankings (merchant_id, checked_at DESC);

-- ── content_jobs ────────────────────────────────────────────────────────────
CREATE TABLE content_jobs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id   UUID NOT NULL REFERENCES business_accounts(id) ON DELETE CASCADE,
  job_type      TEXT NOT NULL
    CHECK (job_type IN (
      'brand_extraction','calendar_generation','content_generation',
      'image_generation','video_generation','publish_post',
      'rank_check','gmb_post','report_generation'
    )),
  status        TEXT DEFAULT 'pending'
    CHECK (status IN ('pending','running','completed','failed','retrying')),
  bullmq_job_id TEXT,

  payload       JSONB DEFAULT '{}',
  result        JSONB,
  error_message TEXT,
  retry_count   INTEGER DEFAULT 0,

  started_at    TIMESTAMPTZ,
  completed_at  TIMESTAMPTZ,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE content_jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "merchant_own_jobs" ON content_jobs
  FOR ALL USING (merchant_id = auth.uid());
CREATE INDEX idx_content_jobs_merchant_status
  ON content_jobs (merchant_id, status);
CREATE INDEX idx_content_jobs_type_status
  ON content_jobs (job_type, status);
