"""
Camera detection + tracking evaluation runner.

Runs the REAL production detector (``MeridianDetector`` — YOLO + ByteTrack)
over either:

  * a MOT-format sequence  (``--frames <dir> --gt <gt.txt>``)  → full accuracy
    report: precision / recall / F1 / AP@0.5 (detection) and MOTA / MOTP / IDF1
    / ID-switches (tracking), since ground truth is available; or
  * a plain video         (``--video <file.mp4>``)            → a SMOKE report:
    proves the pipeline executes on real footage and reports detection counts,
    unique tracks, and throughput (no ground truth ⇒ no accuracy).

Usage
-----
    python3 -m eval.camera.detect_track_eval --video path/clip.mp4 --name taproom
    python3 -m eval.camera.detect_track_eval --frames seq/img1 --gt seq/gt/gt.txt --name MOT-XX

Reports are written to eval/camera/reports/<name>.{json,md}. CPU-only is fine
for short clips; use a GPU box for full MOT sequences.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

# Apply the np.asfarray shim (for motmetrics) by importing the metrics module.
from eval.camera.eval_metrics import detection_pr, tracking_metrics

REPORTS_DIR = Path(__file__).resolve().parent / "reports"
_IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


def _xyxy_to_xywh(b):
    x1, y1, x2, y2 = b
    return [float(x1), float(y1), float(x2 - x1), float(y2 - y1)]


def load_mot_gt(gt_path: str) -> dict[int, dict]:
    """Parse a MOT-format gt.txt into {frame: {'ids':[], 'boxes':[xywh]}}.

    MOT line: frame,id,x,y,w,h,conf,class,visibility. We keep rows with conf!=0
    (gt active) and, when a class column is present, pedestrians (class 1).
    """
    by_frame: dict[int, dict] = {}
    with open(gt_path) as fh:
        for line in fh:
            parts = line.strip().split(",")
            if len(parts) < 6:
                continue
            f = int(float(parts[0]))
            tid = int(float(parts[1]))
            x, y, w, h = (float(parts[i]) for i in range(2, 6))
            conf = float(parts[6]) if len(parts) > 6 and parts[6] != "" else 1.0
            cls = int(float(parts[7])) if len(parts) > 7 and parts[7] != "" else 1
            if conf == 0:
                continue
            if len(parts) > 7 and cls != 1:  # 1 = pedestrian in MOT16/17
                continue
            rec = by_frame.setdefault(f, {"ids": [], "boxes": []})
            rec["ids"].append(tid)
            rec["boxes"].append([x, y, w, h])
    return by_frame


def _iter_frames(video: str | None, frames_dir: str | None):
    """Yield (frame_index_starting_at_1, bgr_ndarray)."""
    if video:
        import cv2

        cap = cv2.VideoCapture(video)
        if not cap.isOpened():
            raise SystemExit(f"could not open video: {video}")
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            idx += 1
            yield idx, frame
        cap.release()
    else:
        import cv2

        files = sorted(
            p for p in Path(frames_dir).iterdir() if p.suffix.lower() in _IMG_EXTS
        )
        for i, p in enumerate(files, start=1):
            img = cv2.imread(str(p))
            if img is not None:
                yield i, img


def run(
    name: str,
    video: str | None = None,
    frames_dir: str | None = None,
    gt_path: str | None = None,
    confidence: float = 0.35,
    iou_thresh: float = 0.5,
    max_frames: int | None = None,
) -> dict:
    from src.camera.detector import MeridianDetector

    detector = MeridianDetector(confidence=confidence)

    hyp_by_frame: dict[int, dict] = {}
    n_frames = 0
    n_dets = 0
    t0 = time.time()
    for idx, frame in _iter_frames(video, frames_dir):
        out = detector.process_frame(frame, merchant_id="eval", camera_id="eval")
        ids = [p["tracker_id"] for p in out["persons"]]
        boxes = [_xyxy_to_xywh(p["bbox"]) for p in out["persons"]]
        scores = [p["confidence"] for p in out["persons"]]
        hyp_by_frame[idx] = {"ids": ids, "boxes": boxes, "scores": scores}
        n_frames += 1
        n_dets += len(ids)
        if max_frames and n_frames >= max_frames:
            break
    elapsed = time.time() - t0

    report: dict = {
        "name": name,
        "source": video or frames_dir,
        "frames": n_frames,
        "total_detections": n_dets,
        "unique_tracks": len({i for fr in hyp_by_frame.values() for i in fr["ids"]}),
        "avg_detections_per_frame": round(n_dets / n_frames, 2) if n_frames else 0,
        "fps_cpu": round(n_frames / elapsed, 2) if elapsed else 0,
        "confidence": confidence,
        "model": "yolo11n + ByteTrack",
    }

    if gt_path:
        gt_by_frame = load_mot_gt(gt_path)
        # Evaluate only the frame range we actually processed (handles --max-frames
        # on a sequence whose gt covers more frames than we ran — otherwise the
        # un-run tail would score as all-misses and tank MOTA).
        proc = set(hyp_by_frame)
        lo, hi = (min(proc), max(proc)) if proc else (1, 0)
        frames = sorted(f for f in (set(gt_by_frame) | proc) if lo <= f <= hi)
        empty = {"ids": [], "boxes": [], "scores": []}
        gt_seq = [gt_by_frame.get(f, {"ids": [], "boxes": []}) for f in frames]
        hyp_seq = [hyp_by_frame.get(f, empty) for f in frames]
        report["detection"] = detection_pr(gt_seq, hyp_seq, iou_thresh)
        report["tracking"] = tracking_metrics(gt_seq, hyp_seq, iou_thresh)
        report["mode"] = "accuracy"
    else:
        report["mode"] = "smoke (no ground truth — counts only)"

    return report


def write_report(report: dict) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    base = REPORTS_DIR / report["name"]
    json_path = base.with_suffix(".json")
    json_path.write_text(json.dumps(report, indent=2))

    lines = [
        f"# Camera eval — {report['name']}",
        "",
        f"- **Mode:** {report['mode']}",
        f"- **Source:** `{report['source']}`",
        f"- **Frames:** {report['frames']}  ·  **CPU fps:** {report['fps_cpu']}",
        f"- **Model:** {report['model']} @ conf {report['confidence']}",
        f"- **Detections:** {report['total_detections']} "
        f"({report['avg_detections_per_frame']}/frame)  ·  "
        f"**Unique tracks:** {report['unique_tracks']}",
    ]
    if "detection" in report:
        d, t = report["detection"], report["tracking"]
        lines += [
            "",
            "## Detection (IoU 0.5)",
            f"- Precision **{d['precision']}** · Recall **{d['recall']}** · F1 **{d['f1']}**",
            f"- TP {d['tp']} · FP {d['fp']} · FN {d['fn']}",
            "",
            "## Tracking",
            f"- **MOTA {t['mota']}** · MOTP(IoU) {t['motp_iou']} · **IDF1 {t['idf1']}**",
            f"- ID switches {t['id_switches']} · FP {t['false_positives']} · misses {t['misses']} · gt {t['gt_objects']}",
        ]
    md_path = base.with_suffix(".md")
    md_path.write_text("\n".join(lines) + "\n")
    return json_path, md_path


def main():
    ap = argparse.ArgumentParser(description="Camera detection+tracking eval")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--video", help="video file (smoke run)")
    src.add_argument("--frames", help="directory of MOT image frames")
    ap.add_argument("--gt", help="MOT gt.txt (enables accuracy metrics)")
    ap.add_argument("--name", default="eval")
    ap.add_argument("--confidence", type=float, default=0.35)
    ap.add_argument("--iou", type=float, default=0.5)
    ap.add_argument("--max-frames", type=int, default=None)
    args = ap.parse_args()

    report = run(
        name=args.name,
        video=args.video,
        frames_dir=args.frames,
        gt_path=args.gt,
        confidence=args.confidence,
        iou_thresh=args.iou,
        max_frames=args.max_frames,
    )
    jp, mp = write_report(report)
    print(json.dumps(report, indent=2))
    print(f"\nwrote {jp}\n      {mp}")


if __name__ == "__main__":
    main()
