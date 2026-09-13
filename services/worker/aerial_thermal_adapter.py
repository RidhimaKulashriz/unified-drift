"""Adapter for Kiuyha's Aerial Thermal Detection RT-DETRv2 model.

The model and inference API are from the upstream repository. We only normalize
Ultralytics Results into DRIFT's provenance-bearing finding contract.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

MODEL_URL = "https://huggingface.co/Kiuyha/rtdetrv2-human-detection-thermal-uav/resolve/main/best.pt"
MODEL_DEFAULT = Path(__file__).resolve().parents[2] / "models" / "aerial-thermal-rtdetrv2-best.pt"


def model_path() -> Path:
    return Path(os.environ.get("DRIFT_AERIAL_THERMAL_MODEL", str(MODEL_DEFAULT)))


def run_on_image(image_path: Path, output_dir: Path) -> dict[str, Any]:
    """Execute upstream RT-DETRv2 inference on one extracted thermal frame."""
    path = model_path()
    if not path.exists():
        raise FileNotFoundError(f"RT-DETRv2 checkpoint missing: {path}; download from {MODEL_URL}")
    try:
        from ultralytics import RTDETR
    except ImportError as exc:
        raise RuntimeError("ultralytics is required for the upstream RT-DETRv2 adapter") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    model = RTDETR(str(path))
    results = model.predict(source=str(image_path), conf=0.25, verbose=False, save=True, project=str(output_dir), name="rtdetrv2")
    result = results[0]
    names = result.names if hasattr(result, "names") else {0: "person"}
    findings: list[dict[str, Any]] = []
    boxes = result.boxes
    if boxes is not None:
        for box in boxes:
            xyxy = [round(float(value), 3) for value in box.xyxy[0].tolist()]
            confidence = round(float(box.conf[0]), 6)
            class_id = int(box.cls[0])
            label = names[class_id] if isinstance(names, dict) else str(class_id)
            findings.append({
                "type": "detection",
                "module": "thermal-sar",
                "label": label,
                "confidence": confidence,
                "bboxPixels": xyxy,
                "source": {
                    "repository": "github.com/kiuyha/Aerial-Thermal-Detection-RT-DETRv2-and-YOLOv12",
                    "model": "RT-DETRv2 / best.pt",
                    "checkpoint": str(path),
                },
            })
    return {
        "adapterId": "aerial-thermal-detection",
        "repository": "vendor/aerial-thermal-detection",
        "model": "RT-DETRv2 / best.pt",
        "executionStatus": "FULLY RUNNING",
        "ran": True,
        "input": str(image_path),
        "findings": findings,
        "artifact": str(output_dir / "rtdetrv2"),
        "modelUrl": MODEL_URL,
    }


def run_on_video(video_path: Path, output_dir: Path) -> dict[str, Any]:
    """Run the upstream detector over every frame of a thermal video."""
    path = model_path()
    if not path.exists():
        raise FileNotFoundError(f"RT-DETRv2 checkpoint missing: {path}; download from {MODEL_URL}")
    try:
        from ultralytics import RTDETR
    except ImportError as exc:
        raise RuntimeError("ultralytics is required for the upstream RT-DETRv2 adapter") from exc
    output_dir.mkdir(parents=True, exist_ok=True)
    model = RTDETR(str(path))
    results = model.predict(source=str(video_path), conf=0.25, verbose=False, save=True, project=str(output_dir), name="rtdetrv2-video", exist_ok=True)
    findings: list[dict[str, Any]] = []
    for frame_index, result in enumerate(results):
        boxes = result.boxes
        names = result.names if hasattr(result, "names") else {0: "person"}
        if boxes is None:
            continue
        for box in boxes:
            xyxy = [round(float(value), 3) for value in box.xyxy[0].tolist()]
            confidence = round(float(box.conf[0]), 6)
            class_id = int(box.cls[0])
            findings.append({
                "type": "detection", "module": "thermal-sar", "label": names[class_id] if isinstance(names, dict) else str(class_id),
                "confidence": confidence, "bboxPixels": xyxy, "frame": frame_index,
                "source": {"repository": "github.com/kiuyha/Aerial-Thermal-Detection-RT-DETRv2-and-YOLOv12", "model": "RT-DETRv2 / best.pt", "checkpoint": str(path)},
            })
    videos = list((output_dir / "rtdetrv2-video").glob("*.mp4"))
    artifact = videos[0] if videos else output_dir / "rtdetrv2-video"
    return {"adapterId": "aerial-thermal-detection", "repository": "vendor/aerial-thermal-detection", "model": "RT-DETRv2 / best.pt", "executionStatus": "FULLY RUNNING", "ran": True, "input": str(video_path), "findings": findings, "artifact": str(artifact), "modelUrl": MODEL_URL}
