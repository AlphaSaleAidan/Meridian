"""Watch for newly generated videos and auto-upload to Supabase."""
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
BUCKET = "training-videos"
OUTPUT_DIR = Path(__file__).parent / "output"
REF_FILE = Path(__file__).parent / "lesson_content.json"


def upload_file(filepath: Path) -> bool:
    import urllib.request
    import urllib.error
    data = filepath.read_bytes()
    headers = {"Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "video/mp4"}
    for method in ["POST", "PUT"]:
        try:
            url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{filepath.name}"
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req) as resp:
                if resp.status in (200, 201):
                    return True
        except urllib.error.HTTPError as e:
            if e.code in (409, 400) and method == "POST":
                continue
            return False
        except Exception:
            return False
    return False


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Missing credentials")
        return

    ref_time = REF_FILE.stat().st_mtime
    uploaded = set()

    print(f"Watching for new videos in {OUTPUT_DIR}")
    print(f"Uploading to {SUPABASE_URL}/storage/v1/object/public/{BUCKET}/")
    print()

    while True:
        videos = sorted(OUTPUT_DIR.glob("*/final_*.mp4"))
        new = [v for v in videos if v.stat().st_mtime > ref_time and v.name not in uploaded]

        for v in new:
            sz = v.stat().st_size / 1024 / 1024
            print(f"  {v.name} ({sz:.1f} MB)... ", end="", flush=True)
            if upload_file(v):
                print("OK")
                uploaded.add(v.name)
            else:
                print("FAILED (will retry)")

        total_expected = 38
        print(f"\r  [{len(uploaded)}/{total_expected} uploaded]", end="", flush=True)

        if len(uploaded) >= total_expected:
            print(f"\nAll {total_expected} videos uploaded!")
            break

        time.sleep(30)


if __name__ == "__main__":
    main()
