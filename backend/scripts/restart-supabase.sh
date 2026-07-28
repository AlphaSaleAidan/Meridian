#!/bin/bash
set -e

# Change to the backend root directory (parent of scripts/)
cd "$(dirname "$0")/.."

echo "======================================"
echo " Restarting Supabase Stack "
echo "======================================"

echo ""
echo "[1/2] Stopping existing Supabase containers..."
supabase stop

echo ""
echo "[2/2] Starting Supabase..."
supabase start

echo ""
echo "✅ Supabase successfully restarted!"
