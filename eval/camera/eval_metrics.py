"""
Camera detection + tracking evaluation metrics (pure, dependency-light).

This module holds the *metric math* only — no torch, no cv2 — so it is unit
testable in isolation (and validated against py-motmetrics' bundled TUD ground
truth, whose MOTA/IDF1 are published).

Conventions
-----------
- A "frame record" is a dict: ``{"ids": [int], "boxes": [[x, y, w, h], ...]}``
  where boxes are MOT-format top-left x, y, width, height in pixels.
- Detection records may additionally carry ``"scores": [float]`` for AP.
- Sequences are ordered lists of frame records, gt and hyp aligned by index.

Detection metrics: precision / recall / F1 at a fixed IoU (greedy match), plus
a confidence-ranked AP@IoU when scores are present.
Tracking metrics: MOTA, MOTP, IDF1, ID switches, FP, misses — via motmetrics.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

# motmetrics 1.4.0 still calls np.asfarray, removed in NumPy 2.0. Restore the
# trivial helper (asarray with a float dtype) so the library runs under np>=2.
if not hasattr(np, "asfarray"):  # pragma: no cover - environment shim
    np.asfarray = lambda a, dtype=np.float64: np.asarray(a, dtype=dtype)


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
def iou_xywh(a: Sequence[float], b: Sequence[float]) -> float:
    """IoU of two [x, y, w, h] boxes (top-left origin)."""
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def _greedy_match(gt_boxes, hyp_boxes, hyp_order, iou_thresh):
    """Greedily match hyp boxes (in priority order) to gt boxes by IoU.

    Returns (num_tp, matched_gt_set). Each gt matched at most once.
    """
    matched_gt: set[int] = set()
    tp = 0
    for h in hyp_order:
        best_iou, best_g = iou_thresh, -1
        for g in range(len(gt_boxes)):
            if g in matched_gt:
                continue
            v = iou_xywh(gt_boxes[g], hyp_boxes[h])
            if v >= best_iou:
                best_iou, best_g = v, g
        if best_g >= 0:
            matched_gt.add(best_g)
            tp += 1
    return tp, matched_gt


# ---------------------------------------------------------------------------
# Detection metrics
# ---------------------------------------------------------------------------
def detection_pr(gt_seq, hyp_seq, iou_thresh: float = 0.5) -> dict:
    """Precision / recall / F1 at a fixed IoU over a sequence (greedy match)."""
    tp = fp = fn = 0
    for gt, hyp in zip(gt_seq, hyp_seq):
        gt_boxes = gt["boxes"]
        hyp_boxes = hyp["boxes"]
        # higher score first if available, else input order
        scores = hyp.get("scores")
        order = sorted(range(len(hyp_boxes)), key=lambda i: -scores[i]) if scores else list(range(len(hyp_boxes)))
        f_tp, _ = _greedy_match(gt_boxes, hyp_boxes, order, iou_thresh)
        tp += f_tp
        fp += len(hyp_boxes) - f_tp
        fn += len(gt_boxes) - f_tp
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp, "fp": fp, "fn": fn,
    }


def average_precision(gt_seq, hyp_seq, iou_thresh: float = 0.5) -> float:
    """Confidence-ranked AP@IoU (single class, 11-point-free, all-points interp).

    Requires ``scores`` on the hyp frames; returns -1.0 if absent.
    """
    dets: list[tuple[float, int]] = []  # (score, is_tp)
    total_gt = 0
    for gt, hyp in zip(gt_seq, hyp_seq):
        scores = hyp.get("scores")
        if scores is None:
            return -1.0
        gt_boxes = gt["boxes"]
        total_gt += len(gt_boxes)
        order = sorted(range(len(hyp["boxes"])), key=lambda i: -scores[i])
        matched: set[int] = set()
        for h in order:
            best_iou, best_g = iou_thresh, -1
            for g in range(len(gt_boxes)):
                if g in matched:
                    continue
                v = iou_xywh(gt_boxes[g], hyp["boxes"][h])
                if v >= best_iou:
                    best_iou, best_g = v, g
            is_tp = 1 if best_g >= 0 else 0
            if is_tp:
                matched.add(best_g)
            dets.append((scores[h], is_tp))
    if total_gt == 0 or not dets:
        return 0.0
    dets.sort(key=lambda d: -d[0])
    tp = np.cumsum([d[1] for d in dets])
    fp = np.cumsum([1 - d[1] for d in dets])
    recalls = tp / total_gt
    precisions = tp / np.maximum(tp + fp, 1e-9)
    # all-points interpolation (area under monotonic-max precision curve)
    mrec = np.concatenate(([0.0], recalls, [1.0]))
    mpre = np.concatenate(([0.0], precisions, [0.0]))
    for i in range(len(mpre) - 1, 0, -1):
        mpre[i - 1] = max(mpre[i - 1], mpre[i])
    idx = np.where(mrec[1:] != mrec[:-1])[0]
    ap = float(np.sum((mrec[idx + 1] - mrec[idx]) * mpre[idx + 1]))
    return round(ap, 4)


# ---------------------------------------------------------------------------
# Tracking metrics (motmetrics)
# ---------------------------------------------------------------------------
def tracking_metrics(gt_seq, hyp_seq, iou_thresh: float = 0.5) -> dict:
    """MOTA / MOTP / IDF1 / ID-switches via motmetrics over an aligned sequence.

    Distance = 1 - IoU; pairs below ``iou_thresh`` are not matchable.
    """
    import motmetrics as mm

    acc = mm.MOTAccumulator(auto_id=True)
    for gt, hyp in zip(gt_seq, hyp_seq):
        gt_ids = gt["ids"]
        hyp_ids = hyp["ids"]
        gt_boxes = np.array(gt["boxes"], dtype=float).reshape(-1, 4)
        hyp_boxes = np.array(hyp["boxes"], dtype=float).reshape(-1, 4)
        # mm.distances.iou_matrix: max_iou is the max *distance* (1-IoU) kept.
        dists = mm.distances.iou_matrix(gt_boxes, hyp_boxes, max_iou=1.0 - iou_thresh)
        acc.update(gt_ids, hyp_ids, dists)

    mh = mm.metrics.create()
    names = [
        "mota", "motp", "idf1", "num_switches",
        "num_false_positives", "num_misses", "num_objects",
        "precision", "recall",
    ]
    summary = mh.compute(acc, metrics=names, name="seq")
    row = summary.loc["seq"]
    # motmetrics' motp is a distance (1-IoU); report it and a friendlier IoU form.
    motp_dist = float(row["motp"]) if not np.isnan(row["motp"]) else float("nan")
    return {
        "mota": round(float(row["mota"]), 4),
        "motp_iou": round(1.0 - motp_dist, 4) if motp_dist == motp_dist else None,
        "idf1": round(float(row["idf1"]), 4),
        "id_switches": int(row["num_switches"]),
        "false_positives": int(row["num_false_positives"]),
        "misses": int(row["num_misses"]),
        "gt_objects": int(row["num_objects"]),
        "precision": round(float(row["precision"]), 4),
        "recall": round(float(row["recall"]), 4),
    }
