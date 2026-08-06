#!/bin/bash
set -e

# Change to the backend root directory (parent of scripts/)
cd "$(dirname "$0")/.."

echo "======================================"
echo " Initializing Local Meridian Database "
echo "======================================"

# docker ps exits 0 even with zero matches, so probe each name filter separately
# instead of chaining with || (the fallback would never fire).
CONTAINER_NAME=$(docker ps -q -f name=supabase_db_backend | head -n 1)
if [ -z "$CONTAINER_NAME" ]; then
    CONTAINER_NAME=$(docker ps -q -f name=postgres | head -n 1)
fi

if [ -z "$CONTAINER_NAME" ]; then
    echo "❌ Error: Could not find running Supabase Postgres container (supabase_db_backend)."
    echo "   Please start Supabase first using 'supabase start'."
    exit 1
fi

echo "Found Postgres container: $CONTAINER_NAME"
echo "Applying database table definitions & seed data..."

docker exec -i "$CONTAINER_NAME" psql -U postgres -d postgres -v ON_ERROR_STOP=1 < scripts/sql/init-local-db.sql

echo ""
echo "✅ Local database schema & seed data initialized successfully!"
