"""
Camera eval-harness metric correctness.

Proves the metric math is right BEFORE we trust any number it prints on real
footage:

  1. Perfect hyp == gt  → MOTA 1.0, IDF1 1.0, 0 switches; detection P=R=F1=1.
  2. A hand-built sequence with exactly 1 FP, 1 miss, 1 ID-switch over 4 gt
     objects → MOTA = 1 - 3/4 = 0.25, and each error count matches.
  3. detection_pr greedy matching gives the expected TP/FP/FN.
  4. Consistency: our tracking_metrics MOTA on the py-motmetrics bundled
     TUD-Campus sequence equals motmetrics computed directly (skipped if the
     bundled data isn't present).
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.camera.eval_metrics import (  # noqa: E402
    detection_pr,
    iou_xywh,
    tracking_metrics,
)

A = [0, 0, 10, 10]
B = [100, 100, 10, 10]
Z = [500, 500, 10, 10]


def test_iou_basic():
    assert iou_xywh(A, A) == 1.0
    assert iou_xywh(A, Z) == 0.0
    assert iou_xywh([0, 0, 10, 10], [5, 0, 10, 10]) == pytest.approx(5 / 15)


def test_perfect_tracking_and_detection():
    gt = [{"ids": [1, 2], "boxes": [A, B]}, {"ids": [1, 2], "boxes": [A, B]}]
    hyp = [{"ids": [1, 2], "boxes": [A, B]}, {"ids": [1, 2], "boxes": [A, B]}]
    t = tracking_metrics(gt, hyp)
    assert t["mota"] == 1.0
    assert t["idf1"] == 1.0
    assert t["id_switches"] == 0
    assert t["false_positives"] == 0 and t["misses"] == 0
    d = detection_pr(gt, hyp)
    assert d == {"precision": 1.0, "recall": 1.0, "f1": 1.0, "tp": 4, "fp": 0, "fn": 0}


def test_known_errors_mota():
    # F1: gt{1:A}, hyp{10:A, 99:Z}  -> 1 match (1<->10), 1 FP (99)
    # F2: gt{1:A}, hyp{11:A}        -> match but id 10->11 = 1 ID switch
    # F3: gt{1:A, 2:B}, hyp{11:A}   -> gt2 unmatched = 1 miss
    gt = [
        {"ids": [1], "boxes": [A]},
        {"ids": [1], "boxes": [A]},
        {"ids": [1, 2], "boxes": [A, B]},
    ]
    hyp = [
        {"ids": [10, 99], "boxes": [A, Z]},
        {"ids": [11], "boxes": [A]},
        {"ids": [11], "boxes": [A]},
    ]
    t = tracking_metrics(gt, hyp)
    assert t["gt_objects"] == 4
    assert t["false_positives"] == 1
    assert t["misses"] == 1
    assert t["id_switches"] == 1
    assert t["mota"] == pytest.approx(0.25)  # 1 - (1+1+1)/4


def test_detection_pr_counts():
    gt = [{"ids": [1, 2], "boxes": [A, B]}]
    hyp = [{"ids": [1, 2], "boxes": [A, Z]}]  # A matches, B missed, Z is FP
    d = detection_pr(gt, hyp)
    assert (d["tp"], d["fp"], d["fn"]) == (1, 1, 1)
    assert d["precision"] == 0.5 and d["recall"] == 0.5 and d["f1"] == 0.5


def test_consistency_with_motmetrics_on_bundled_tud():
    mm = pytest.importorskip("motmetrics")
    data_dir = os.path.join(os.path.dirname(mm.__file__), "data", "TUD-Campus")
    gt_path = os.path.join(data_dir, "gt.txt")
    hyp_path = os.path.join(data_dir, "test.txt")
    if not (os.path.exists(gt_path) and os.path.exists(hyp_path)):
        pytest.skip("bundled TUD-Campus data not present")

    gt_df = mm.io.loadtxt(gt_path, fmt="mot15-2D")
    hyp_df = mm.io.loadtxt(hyp_path, fmt="mot15-2D")

    # Reference: motmetrics' own end-to-end path.
    acc = mm.utils.compare_to_groundtruth(gt_df, hyp_df, "iou", distth=0.5)
    ref = mm.metrics.create().compute(acc, metrics=["mota", "idf1"], name="ref")
    ref_mota = round(float(ref.loc["ref"]["mota"]), 4)

    # Ours: reshape the same data into frame records and run our wrapper.
    frames = sorted(set(gt_df.index.get_level_values(0)) | set(hyp_df.index.get_level_values(0)))

    def rows(df, f):
        if f not in df.index.get_level_values(0):
            return {"ids": [], "boxes": []}
        sub = df.loc[f]
        return {
            "ids": list(sub.index),
            "boxes": sub[["X", "Y", "Width", "Height"]].values.tolist(),
        }

    gt_seq = [rows(gt_df, f) for f in frames]
    hyp_seq = [rows(hyp_df, f) for f in frames]
    ours = tracking_metrics(gt_seq, hyp_seq, iou_thresh=0.5)
    assert ours["mota"] == pytest.approx(ref_mota, abs=0.02)
