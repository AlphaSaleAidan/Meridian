#!/bin/bash
# Upload training videos to Supabase Storage
# Usage: bash upload.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../../.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: .env not found at $ENV_FILE"
  echo "Create it with SUPABASE_URL and SUPABASE_SERVICE_KEY"
  exit 1
fi

source "$ENV_FILE"

if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_KEY" ]; then
  echo "ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env"
  exit 1
fi

BUCKET="training-videos"
OUTPUT_DIR="$SCRIPT_DIR/output"

echo "Creating storage bucket: $BUCKET"
curl -s -X POST "${SUPABASE_URL}/storage/v1/bucket" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"id\":\"${BUCKET}\",\"name\":\"${BUCKET}\",\"public\":true,\"file_size_limit\":10485760}" \
  && echo ""

uploaded=0
failed=0

for video in "$OUTPUT_DIR"/*/final_*.mp4; do
  [ -f "$video" ] || continue
  filename=$(basename "$video")
  size=$(du -h "$video" | cut -f1)
  echo -n "  $filename ($size)... "

  response=$(curl -s -w "\n%{http_code}" -X POST \
    "${SUPABASE_URL}/storage/v1/object/${BUCKET}/${filename}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}" \
    -H "Content-Type: video/mp4" \
    --data-binary @"$video")

  http_code=$(echo "$response" | tail -1)
  body=$(echo "$response" | head -n -1)

  if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
    echo "OK"
    uploaded=$((uploaded + 1))
  elif echo "$body" | grep -q "already exists"; then
    echo "exists (updating)"
    curl -s -X PUT \
      "${SUPABASE_URL}/storage/v1/object/${BUCKET}/${filename}" \
      -H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}" \
      -H "Content-Type: video/mp4" \
      --data-binary @"$video" > /dev/null
    uploaded=$((uploaded + 1))
  else
    echo "FAILED ($http_code)"
    failed=$((failed + 1))
  fi
done

echo ""
echo "Done: $uploaded uploaded, $failed failed"
echo "Public URL pattern: ${SUPABASE_URL}/storage/v1/object/public/${BUCKET}/final_X_Y.mp4"
