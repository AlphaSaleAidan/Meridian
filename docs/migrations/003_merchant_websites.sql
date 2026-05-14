-- Migration 003: Merchant Websites
-- Creates tables for the "My Website" feature.
-- Run against Supabase SQL Editor after review.

-- Merchant website configuration
create table if not exists merchant_websites (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null,
  portal_context text not null default 'us',
  slug text unique not null,
  business_name text,
  business_type text,
  tagline text,
  description text,
  template_id text not null default 'aurora',
  template_config jsonb default '{}',
  logo_url text,
  hero_headline text,
  hero_subheadline text,
  about_text text,
  services jsonb default '[]',
  hours jsonb default '{}',
  phone text,
  email text,
  address text,
  google_rating numeric(3,2),
  google_review_count integer,
  google_reviews jsonb default '[]',
  social_links jsonb default '{}',
  source_url text,
  google_place_id text,
  last_scraped_at timestamptz,
  scrape_status text default 'pending',
  published boolean default false,
  published_at timestamptz,
  subdomain_active boolean default true,
  ordering_enabled boolean default false,
  ordering_fee_pct numeric(5,4) default 0.0299,
  stripe_connect_id text,
  subscription_active boolean default true,
  subscription_checked_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_mw_merchant on merchant_websites(merchant_id);
create index if not exists idx_mw_slug on merchant_websites(slug);
create index if not exists idx_mw_portal on merchant_websites(portal_context);

-- Website analytics events
create table if not exists website_analytics (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null,
  website_id uuid references merchant_websites(id),
  event_type text not null,
  path text,
  referrer text,
  utm_source text,
  utm_medium text,
  utm_campaign text,
  device_type text,
  country text,
  city text,
  duration_seconds integer,
  recorded_at timestamptz default now()
);

create index if not exists idx_wa_merchant on website_analytics(merchant_id);
create index if not exists idx_wa_website on website_analytics(website_id);
create index if not exists idx_wa_recorded on website_analytics(recorded_at);

-- Website orders
create table if not exists website_orders (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null,
  website_id uuid references merchant_websites(id),
  customer_name text,
  customer_phone text,
  customer_email text,
  order_type text default 'pickup',
  items jsonb not null default '[]',
  subtotal numeric(10,2),
  fee_amount numeric(10,2),
  total numeric(10,2),
  currency text default 'USD',
  pos_order_id text,
  pos_system text,
  stripe_payment_intent_id text,
  status text default 'pending',
  created_at timestamptz default now()
);

create index if not exists idx_wo_merchant on website_orders(merchant_id);
create index if not exists idx_wo_website on website_orders(website_id);
create index if not exists idx_wo_status on website_orders(status);

-- RLS
alter table merchant_websites enable row level security;
alter table website_analytics enable row level security;
alter table website_orders enable row level security;

create policy "Merchant sees own website"
  on merchant_websites for all
  using (merchant_id = auth.uid());

create policy "Merchant sees own analytics"
  on website_analytics for all
  using (merchant_id = auth.uid());

create policy "Merchant sees own orders"
  on website_orders for all
  using (merchant_id = auth.uid());

-- Public read for published websites (used by /sites/:slug)
create policy "Public can read published websites"
  on merchant_websites for select
  using (published = true and subscription_active = true);

-- Public insert for analytics events
create policy "Public can insert analytics"
  on website_analytics for insert
  with check (true);

-- Public insert for orders
create policy "Public can insert orders"
  on website_orders for insert
  with check (true);
