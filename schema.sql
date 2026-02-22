-- SourcedMD Database Schema
-- Run once to initialize the database

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users (linked to Clerk auth user_id)
CREATE TABLE IF NOT EXISTS sourced_md_users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_user_id TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    searches_today INTEGER NOT NULL DEFAULT 0,
    searches_reset_at DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Search query log
CREATE TABLE IF NOT EXISTS sourced_md_queries (
    query_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES sourced_md_users(user_id) ON DELETE SET NULL,
    query_type TEXT NOT NULL, -- research | trials | consensus | analyze
    query_text TEXT NOT NULL,
    result_count INTEGER,
    duration_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Cached results (24hr TTL)
CREATE TABLE IF NOT EXISTS sourced_md_results (
    result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cache_key TEXT UNIQUE NOT NULL,
    query_type TEXT NOT NULL,
    query_text TEXT NOT NULL,
    result_json JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '24 hours',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Subscriptions
CREATE TABLE IF NOT EXISTS sourced_md_subscriptions (
    subscription_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES sourced_md_users(user_id) ON DELETE CASCADE,
    plan TEXT NOT NULL DEFAULT 'free',
    stripe_subscription_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_smd_users_clerk ON sourced_md_users(clerk_user_id);
CREATE INDEX IF NOT EXISTS idx_smd_queries_user ON sourced_md_queries(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_smd_results_cache ON sourced_md_results(cache_key, expires_at);
CREATE INDEX IF NOT EXISTS idx_smd_results_expiry ON sourced_md_results(expires_at);

-- Plan limits view
CREATE OR REPLACE VIEW sourced_md_plan_limits AS
SELECT
    'free' as plan, 3 as daily_searches, 5 as max_specialists, FALSE as trials_access
UNION ALL
SELECT 'pro', 999999, 20, TRUE
UNION ALL
SELECT 'clinic', 999999, 62, TRUE;
