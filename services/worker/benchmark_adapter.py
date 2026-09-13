"""Adapter for the Arran archaeological benchmark.

Arran is a benchmark dataset, not a detector. DRIFT integrates its real
annotation/evaluation workflow: given a predictions JSON/CSV and the benchmark
annotations, execute an IoU-based evaluation and write metrics.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

REPO_SRC = Path(__file__).resolve().parents[2] / "vendor" / "arran"


def _read_annotations(data_path: Path) -> list[dict[str, Any]]:
    files = sorted(data_path.rglob("*.csv")) if data_path.is_dir() else [data_path]
    rows: list[dict[str, Any]] = []
    for file in files:
        with file.open(newline="", encoding="utf-8") as handle:
            for row in csv.reader(handle):
                if len(row) < 6:
                    continue
                rows.append({"image": row[0], "box": [float(row[1]), float(row[2]), float(row[3]), float(row[4])], "label": row[5]})
    return rows


def _iou(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union else 0.0


def execute_benchmarkevaluation(data_path: Path, output_dir: Path, predictions_path: Path | None = None) -> dict[str, Any]:
    if not REPO_SRC.exists():
        raise FileNotFoundError(f"Arran repository not found: {REPO_SRC}")
    if not data_path.exists():
        raise FileNotFoundError(f"Benchmark annotations not found: {data_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    annotations = _read_annotations(data_path)
    if not annotations:
        raise RuntimeError("No Arran CSV annotations could be parsed")
    result: dict[str, Any] = {
        "adapterId": "arran",
        "repository": "vendor/arran",
        "model": "Arran Archaeological Benchmark",
        "input": str(data_path),
        "annotationCount": len(annotations),
        "classes": sorted({row["label"] for row in annotations}),
        "ran": True,
        "executionStatus": "PARTIALLY INTEGRATED",
        "contribution": "real Arran annotation parsing and evaluation mode",
    }
    if predictions_path is None:
        result["reason"] = "benchmark dataset parsed; supply predictions_path to execute IoU evaluation"
        result["artifact"] = str(output_dir / "arran_annotations.json")
        (output_dir / "arran_annotations.json").write_text(json.dumps(annotations, indent=2), encoding="utf-8")
    else:
        if not predictions_path.exists():
            raise FileNotFoundError(f"Predictions file not found: {predictions_path}")
        predictions = json.loads(predictions_path.read_text(encoding="utf-8"))
        tp = 0
        used: set[int] = set()
        for pred in predictions:
            pbox = pred.get("box") or pred.get("bbox")
            plabel = pred.get("label") or pred.get("class")
            if not pbox:
                continue
            best = (-1.0, None)
            for i, ann in enumerate(annotations):
                if i in used or ann["label"] != plabel:
                    continue
                score = _iou([float(v) for v in pbox], ann["box"])
                if score > best[0]:
                    best = (score, i)
            if best[0] >= 0.5 and best[1] is not None:
                used.add(best[1])
                tp += 1
        fp = max(0, len(predictions) - tp)
        fn = max(0, len(annotations) - tp)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        result.update({"executionStatus": "FULLY RUNNING", "truePositives": tp, "falsePositives": fp, "falseNegatives": fn, "precisionIoU50": precision, "recallIoU50": recall, "predictions": str(predictions_path)})
        result["artifact"] = str(output_dir / "arran_benchmark_report.json")
        (output_dir / "arran_benchmark_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
