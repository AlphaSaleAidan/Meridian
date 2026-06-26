#!/usr/bin/env python3
"""
Live-camera verifier — prove the WHIP→Cloudflare→browser path from a laptop.

This is the same publish the edge agent does in production (RTSP → Cloudflare
Stream via WHIP), but standalone so you can confirm it end-to-end without a
Jetson or the portal. It:
  1. creates a Cloudflare Stream Live Input (using your Stream token),
  2. WHIP-publishes a source to it (a test pattern by default, or a real camera
     with --rtsp rtsp://...),
  3. prints a browser URL to watch it live,
  4. deletes the Live Input on exit.

If the browser shows the video, the streaming chain works — the portal "Go live"
button drives the exact same publish via the backend.

Requires ffmpeg >= 7.1 (the `whip` muxer) — the verify Docker image bundles it.

Env:
  CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_STREAM_TOKEN   (Account · Stream:Edit)
Usage:
  python3 verify_live.py                      # test pattern
  python3 verify_live.py --rtsp rtsp://CAM    # a real camera
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import urllib.request

API = os.environ.get("CLOUDFLARE_API_BASE", "https://api.cloudflare.com/client/v4")
FFMPEG = os.environ.get("FFMPEG_BIN", "ffmpeg")


def _cf(method, path, body=None):
    acct = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    token = os.environ["CLOUDFLARE_STREAM_TOKEN"]
    url = f"{API}/accounts/{acct}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if body:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtsp", help="RTSP URL of a real camera (default: a test pattern)")
    args = ap.parse_args()

    if not (os.environ.get("CLOUDFLARE_ACCOUNT_ID") and os.environ.get("CLOUDFLARE_STREAM_TOKEN")):
        print("ERROR: set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_STREAM_TOKEN", file=sys.stderr)
        sys.exit(2)

    print("Creating Cloudflare Live Input…")
    res = _cf("POST", "/stream/live_inputs",
              {"meta": {"name": "meridian-verify"}, "recording": {"mode": "off"}})
    if not res.get("success"):
        print("Create failed:", res.get("errors"), file=sys.stderr)
        sys.exit(1)
    r = res["result"]
    uid = r["uid"]
    whip = r["webRTC"]["url"]
    whep = r["webRTCPlayback"]["url"]
    # iframe player URL lives on the same customer-* subdomain as WHEP
    sub = whep.split("/")[2]
    iframe = f"https://{sub}/{uid}/iframe?autoplay=true&muted=true"

    print("\n  WATCH IT HERE (open in a browser):")
    print(f"    {iframe}")
    print(f"\n  (WHEP url for the app player: {whep})")
    print(f"  (live input uid: {uid})\n")

    if args.rtsp:
        src = ["-rtsp_transport", "tcp", "-i", args.rtsp, "-c:v", "copy"]
        print(f"Publishing camera {args.rtsp} → Cloudflare (Ctrl+C to stop)…")
    else:
        src = ["-f", "lavfi", "-i", "testsrc=size=1280x720:rate=25",
               "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
               "-profile:v", "baseline", "-pix_fmt", "yuv420p", "-g", "50"]
        print("Publishing a TEST PATTERN → Cloudflare (Ctrl+C to stop)…")

    # Video-only WHIP publish (passthrough for real cameras, libx264 for the test
    # pattern). Audio omitted — live monitoring is video; keeps it simple/robust.
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "warning", "-re", *src, "-an", "-f", "whip", whip]

    proc = None
    def cleanup(*_):
        if proc and proc.poll() is None:
            proc.terminate()
        try:
            _cf("DELETE", f"/stream/live_inputs/{uid}")
            print("\nCleaned up Live Input.")
        except Exception:
            pass
        sys.exit(0)
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    try:
        proc = subprocess.Popen(cmd)
        proc.wait()
    finally:
        cleanup()


if __name__ == "__main__":
    main()
