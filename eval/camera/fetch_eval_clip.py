"""
Fetch a labeled MOT sequence for the camera eval harness.

motchallenge.net is not reachable from the Contabo box (egress blocked), so we
pull a standard MOT17 sequence from a HuggingFace mirror instead. Frames + the
MOT-format ground truth are downloaded into a local dir ready for
``detect_track_eval``.

    python3 -m eval.camera.fetch_eval_clip --seq MOT17-09-FRCNN --frames 150 --out /tmp/mot17-09
    python3 -m eval.camera.detect_track_eval \
        --frames /tmp/mot17-09/img1 --gt /tmp/mot17-09/gt.txt --name MOT17-09 --max-frames 150

Full sequences are large (1080p) and slow on CPU — run those on the edge/GPU box.
"""
from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

HF_BASE = "https://huggingface.co/datasets/Lekim89/MOT17/resolve/main/train"


def _get(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "meridian-eval"})
        with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - trusted host
            dest.write_bytes(r.read())
        return dest.stat().st_size > 0
    except Exception as e:  # noqa: BLE001
        print(f"  ! {url} -> {e}")
        return False


def fetch(seq: str, frames: int, out: str) -> None:
    out_dir = Path(out)
    (out_dir / "img1").mkdir(parents=True, exist_ok=True)
    base = f"{HF_BASE}/{seq}"

    print(f"seqinfo + gt for {seq} …")
    _get(f"{base}/seqinfo.ini", out_dir / "seqinfo.ini")
    if not _get(f"{base}/gt/gt.txt", out_dir / "gt.txt"):
        raise SystemExit("could not fetch gt.txt — check the sequence name / mirror")

    print(f"downloading {frames} frames …")
    ok = 0
    for i in range(1, frames + 1):
        name = f"{i:06d}.jpg"
        if _get(f"{base}/img1/{name}", out_dir / "img1" / name):
            ok += 1
    print(f"done: {ok}/{frames} frames in {out_dir}/img1  (gt: {out_dir}/gt.txt)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq", default="MOT17-09-FRCNN")
    ap.add_argument("--frames", type=int, default=150)
    ap.add_argument("--out", default="/tmp/mot17-09")
    args = ap.parse_args()
    fetch(args.seq, args.frames, args.out)


if __name__ == "__main__":
    main()
