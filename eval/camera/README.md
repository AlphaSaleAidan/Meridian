# Camera detection + tracking eval harness

Rigorous, repeatable proof that the production vision pipeline
(`MeridianDetector` — YOLO + ByteTrack) actually detects and tracks people —
not a demo replay. It runs the **real** detector over labeled footage and
reports standard metrics.

## What it measures

- **Detection** (IoU 0.5): precision, recall, F1, AP@0.5.
- **Tracking**: MOTA, MOTP (as IoU), IDF1, ID-switches, FP, misses — via
  [`motmetrics`](https://github.com/cheind/py-motmetrics).

The metric math lives in `eval_metrics.py` (pure numpy + motmetrics, no
torch/cv2) and is unit-tested in `tests/test_camera_eval.py` — including a
consistency check against motmetrics' own computation on the bundled
TUD-Campus ground truth, so the numbers are trustworthy before we run on
anything.

## Run it

```bash
# 1. Pull a labeled sequence (motchallenge.net is egress-blocked on Contabo,
#    so we mirror a standard MOT17 sequence from HuggingFace).
python3 -m eval.camera.fetch_eval_clip --seq MOT17-09-FRCNN --frames 150 --out /tmp/mot17-09

# 2. Run the real detector against ground truth → accuracy report.
python3 -m eval.camera.detect_track_eval \
    --frames /tmp/mot17-09/img1 --gt /tmp/mot17-09/gt.txt --name MOT17-09 --max-frames 150

# Smoke run on any video (no ground truth → counts + throughput only):
python3 -m eval.camera.detect_track_eval --video clip.mp4 --name my-clip
```

Reports are written to `eval/camera/reports/<name>.{json,md}`.

## Baseline results (committed in `reports/`)

| Run | Frames | Detection | Tracking |
|-----|--------|-----------|----------|
| `taproom-smoke` | 193 | — (no GT) | 14 unique tracks, 10.3 det/frame |
| `MOT17-09-150f` | 150 | P 0.74 · R 0.72 · F1 0.73 · AP@0.5 0.68 | MOTA 0.46 · IDF1 0.71 · MOTP(IoU) 0.84 · 10 IDSW |

These were produced on the **CPU-only** Contabo box with the **`yolo11n` (nano)**
model — the smallest detector. They prove the pipeline + harness work end to end
and give a baseline. They are **not** the production ceiling:

- `yolo11n` is the nano baseline. The recall gap (≈0.72) is mostly the small
  model missing distant/occluded people on the crowded MOT17 scene. A larger
  detector (`yolo11m`/`yolo11x`) or the planned **RF-DETR** swap (Apache, vs
  YOLO's AGPL) should lift recall and MOTA materially — re-run this harness
  after the swap to quantify it.
- CPU throughput is 4–8 fps; the edge/GPU box will be far faster. Run full
  sequences (525+ frames) there rather than on Contabo.

## Notes

- `motmetrics 1.4.0` calls `np.asfarray` (removed in NumPy 2.0); `eval_metrics`
  installs a tiny shim at import so it runs under NumPy ≥ 2.
- Ground-truth filtering: pedestrian class (1), `conf != 0` rows only (MOT16/17
  convention).
