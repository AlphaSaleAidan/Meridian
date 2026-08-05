#!/bin/bash
set -e

# Change to the backend root directory (parent of scripts/)
cd "$(dirname "$0")/.."

echo "======================================"
echo " Initializing Local Meridian Database "
echo "======================================"

CONTAINER_NAME=$(docker ps -q -f name=supabase_db_backend || docker ps -q -f name=postgres | head -n 1)

if [ -z "$CONTAINER_NAME" ]; then
    echo "❌ Error: Could not find running Supabase Postgres container (supabase_db_backend)."
    echo "   Please start Supabase first using 'supabase start'."
    exit 1
fi

echo "Found Postgres container: $CONTAINER_NAME"
echo "Applying database table definitions & seed data..."

docker exec -i "$CONTAINER_NAME" psql -U postgres -d postgres << 'EOF'
-- Create businesses table
CREATE TABLE IF NOT EXISTS public.businesses (
    id TEXT PRIMARY KEY,
    name TEXT,
    plan_tier TEXT,
    access_token TEXT,
    token_status TEXT,
    status TEXT,
    pos_provider TEXT,
    onboarded BOOLEAN DEFAULT FALSE
);

-- Seed default local test record
INSERT INTO public.businesses (id, name, plan_tier, access_token, token_status, status, pos_provider, onboarded)
VALUES ('demo-org-123', 'Maple Bakery', 'starter', 'demo-portal-token-999', 'active', 'active', 'square', true)
ON CONFLICT (id) DO NOTHING;
EOF

echo ""
echo "✅ Local database schema & seed data initialized successfully!"
