-- ============================================================
-- MERIDIAN DATABASE SCHEMA
-- AI-Powered POS Analytics for Independent Business Owners
-- ============================================================
-- Designed for: Supabase (PostgreSQL 15+) + TimescaleDB
-- Features: Row-Level Security, Time-Series Hypertables,
--           Continuous Aggregates, Full Data Isolation
-- ============================================================

-- ============================================================
-- PART 1: EXTENSIONS & ENUMS
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================
-- ENUM TYPES
-- ============================================================

CREATE TYPE subscription_tier AS ENUM ('trial', 'insights', 'optimize', 'command');
CREATE TYPE subscription_status AS ENUM ('trialing', 'active', 'past_due', 'canceled', 'paused');
CREATE TYPE pos_provider AS ENUM ('square', 'toast', 'clover', 'lightspeed', 'shopify', 'csv_import', 'other');
CREATE TYPE pos_connection_status AS ENUM ('pending', 'connected', 'syncing', 'error', 'disconnected');
CREATE TYPE user_role AS ENUM ('owner', 'manager', 'staff', 'viewer');
CREATE TYPE business_vertical AS ENUM ('restaurant', 'smoke_shop', 'clothing_boutique', 'pawn_shop', 'convenience_store', 'bar', 'cafe', 'food_truck', 'salon', 'other_retail', 'other');
CREATE TYPE transaction_type AS ENUM ('sale', 'refund', 'void', 'exchange', 'no_sale');
CREATE TYPE payment_method AS ENUM ('cash', 'credit_card', 'debit_card', 'mobile_pay', 'gift_card', 'other');
CREATE TYPE notification_channel AS ENUM ('sms', 'email', 'push', 'in_app');
CREATE TYPE notification_status AS ENUM ('pending', 'sent', 'delivered', 'failed', 'acknowledged');
CREATE TYPE notification_priority AS ENUM ('low', 'normal', 'high', 'urgent');
CREATE TYPE event_type AS ENUM ('delivery', 'inspection', 'meeting', 'promotion', 'maintenance', 'catering', 'custom');
CREATE TYPE event_recurrence AS ENUM ('none', 'daily', 'weekly', 'biweekly', 'monthly');
CREATE TYPE insight_type AS ENUM ('money_left', 'product_recommendation', 'staffing', 'pricing', 'inventory', 'anomaly', 'seasonal', 'benchmark', 'general');
CREATE TYPE insight_action_status AS ENUM ('pending', 'viewed', 'accepted', 'dismissed', 'completed');
CREATE TYPE day_of_week AS ENUM ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday');
