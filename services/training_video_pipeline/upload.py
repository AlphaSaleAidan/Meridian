"""Upload training videos to Supabase Storage."""
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
BUCKET = "training-videos"
OUTPUT_DIR = Path(__file__).parent / "output"


def upload_file(filepath: Path) -> bool:
    filename = filepath.name
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{filename}"
    data = filepath.read_bytes()
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "video/mp4",
    }

    for method in ["POST", "PUT"]:
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req) as resp:
                if resp.status in (200, 201):
                    return True
        except urllib.error.HTTPError as e:
            if e.code == 409 and method == "POST":
                continue
            if e.code == 400 and method == "POST":
                continue
            print(f"    HTTP {e.code}: {e.read().decode()[:100]}")
            return False
        except Exception as e:
            print(f"    Error: {e}")
            return False
    return False


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        sys.exit(1)

    print(f"Supabase: {SUPABASE_URL}")
    print(f"Bucket: {BUCKET}")
    print()

    videos = sorted(OUTPUT_DIR.glob("*/final_*.mp4"))
    print(f"Found {len(videos)} videos to upload")
    print()

    uploaded = 0
    failed = 0

    for video in videos:
        size_mb = video.stat().st_size / 1024 / 1024
        print(f"  {video.name} ({size_mb:.1f} MB)... ", end="", flush=True)

        if upload_file(video):
            print("OK")
            uploaded += 1
        else:
            print("FAILED")
            failed += 1

    print()
    print(f"Done: {uploaded} uploaded, {failed} failed")
    print(f"Public URL: {SUPABASE_URL}/storage/v1/object/public/{BUCKET}/final_X_Y.mp4")


if __name__ == "__main__":
    main()
