-- Add missing subscription tier and status enum values
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New Query)

-- Tier values needed by billing_service.py
ALTER TYPE subscription_tier ADD VALUE IF NOT EXISTS 'standard';
ALTER TYPE subscription_tier ADD VALUE IF NOT EXISTS 'premium';
ALTER TYPE subscription_tier ADD VALUE IF NOT EXISTS 'weekly';
ALTER TYPE subscription_tier ADD VALUE IF NOT EXISTS 'starter';

-- Status values needed by billing_service.py
ALTER TYPE subscription_status ADD VALUE IF NOT EXISTS 'pending_payment';
