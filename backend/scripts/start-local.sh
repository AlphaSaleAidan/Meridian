#!/bin/bash
set -e

# Change to the backend root directory (parent of scripts/)
cd "$(dirname "$0")/.."

echo "======================================"
echo " Starting Meridian Local Environment "
echo "======================================"

echo ""
echo "[1/2] Starting Supabase stack..."
supabase start

echo ""
echo "[2/4] Initializing local database tables & seed data..."
./scripts/init-local-db.sh

echo ""
echo "[3/4] Extracting Supabase secrets for Docker..."
# Extract just the publishable key and save it to the local/.env file
supabase status -o env | grep -E '^(PUBLISHABLE_KEY)=' > local/.env

echo ""
echo "[4/4] Starting Spring Boot Backend via Docker Compose..."
cd local
docker-compose --env-file .env up --build
