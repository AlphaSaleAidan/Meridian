#!/bin/bash
# Watch for newly regenerated videos (>5MB) and upload them
cd /root/Meridian/services/training_video_pipeline

SUPABASE_URL=$(python3 -c "from dotenv import load_dotenv; from pathlib import Path; import os; load_dotenv(Path('/root/Meridian/.env')); print(os.getenv('SUPABASE_URL',''))")
SUPABASE_KEY=$(python3 -c "from dotenv import load_dotenv; from pathlib import Path; import os; load_dotenv(Path('/root/Meridian/.env')); print(os.getenv('SUPABASE_SERVICE_KEY',''))")
BUCKET="training-videos"
UPLOADED_LOG="/tmp/uploaded_videos.log"
touch "$UPLOADED_LOG"

echo "=== Video upload watcher started $(date) ==="
echo "Checking every 120s for new ready videos (>5MB)..."

while true; do
    for dir in output/*/; do
        name=$(basename "$dir")
        f="$dir/final_${name}.mp4"
        [ -f "$f" ] || continue
        
        size=$(stat -c%s "$f" 2>/dev/null)
        [ "$size" -gt 5000000 ] || continue
        
        # Skip if already uploaded this size
        key="${name}_${size}"
        grep -q "^$key$" "$UPLOADED_LOG" && continue
        
        # Check file isn't still being written (size stable for 10s)
        sleep 10
        size2=$(stat -c%s "$f" 2>/dev/null)
        [ "$size" = "$size2" ] || continue
        
        mb=$(echo "scale=1; $size/1048576" | bc)
        echo -n "  $(date +%H:%M) final_${name}.mp4 (${mb}MB)... "
        
        # Upload via PUT (overwrite)
        status=$(curl -s -o /dev/null -w "%{http_code}" \
            -X PUT \
            -H "Authorization: Bearer $SUPABASE_KEY" \
            -H "Content-Type: video/mp4" \
            --data-binary "@$f" \
            "${SUPABASE_URL}/storage/v1/object/${BUCKET}/final_${name}.mp4")
        
        if [ "$status" = "200" ] || [ "$status" = "201" ]; then
            echo "OK"
            echo "$key" >> "$UPLOADED_LOG"
        else
            echo "HTTP $status — will retry"
        fi
    done
    
    # Count remaining
    total=38
    done_count=$(wc -l < "$UPLOADED_LOG")
    remaining=$((total - done_count))
    
    if [ "$remaining" -le 0 ]; then
        echo "=== All videos uploaded! $(date) ==="
        break
    fi
    
    sleep 120
done
