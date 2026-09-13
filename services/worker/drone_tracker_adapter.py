"""Adapter for Drone Tracker (ROS2 detection + tracking system).

This adapter executes the upstream drone detection and tracking system.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

REPO_SRC = Path(__file__).resolve().parents[2] / "vendor" / "drone-tracker"
MODEL_DEFAULT = REPO_SRC / "detection" / "models" / "trained" / "phase2_finetuned_final_best.pt"


def model_path() -> Path:
    return Path(os.environ.get("DRIFT_DRONE_TRACKER_MODEL", str(MODEL_DEFAULT)))


def run_on_video(video_path: Path, output_dir: Path) -> dict[str, Any]:
    """Execute upstream drone detection and tracking on video."""
    path = model_path()
    if not path.exists():
        raise FileNotFoundError(f"Drone tracker model missing: {path}")
    
    try:
        from ultralytics import YOLO
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("ultralytics, opencv-python, and numpy are required for the drone tracker adapter") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load model
    model = YOLO(str(path))
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Failed to open video: {video_path}")
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Setup output video
    output_video = output_dir / "tracked_output.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_video), fourcc, fps, (width, height))
    
    findings: list[dict[str, Any]] = []
    frame_count = 0
    total_detections = 0
    track_ids = set()
    
    # Process frames (sample every 30 frames for speed)
    sample_rate = 30
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        if frame_count % sample_rate != 0:
            continue
        
        # Run detection with tracking
        results = model.track(frame, conf=0.5, iou=0.45, persist=True, verbose=False)
        
        if results and results[0].boxes is not None:
            boxes = results[0].boxes
            num_detections = len(boxes)
            total_detections += num_detections
            
            # Extract track IDs
            if boxes.id is not None:
                track_ids.update(boxes.id.int().cpu().numpy().tolist())
            
            # Extract findings
            names = results[0].names if hasattr(results[0], "names") else {0: "person"}
            for box in boxes:
                xyxy = [round(float(value), 3) for value in box.xyxy[0].tolist()]
                confidence = round(float(box.conf[0]), 6)
                class_id = int(box.cls[0])
                label = names[class_id] if isinstance(names, dict) else str(class_id)
                track_id = int(box.id[0]) if box.id is not None else None
                
                findings.append({
                    "type": "detection",
                    "module": "drone-tracker",
                    "label": label,
                    "confidence": confidence,
                    "bboxPixels": xyxy,
                    "frame": frame_count,
                    "trackId": track_id,
                    "source": {
                        "repository": "github.com/Gruzver/drone-tracker",
                        "model": "YOLOv8 phase2_finetuned_final_best.pt",
                        "checkpoint": str(path),
                    },
                })
            
            # Save annotated frame
            annotated = results[0].plot()
            out.write(annotated)
    
    # Cleanup
    cap.release()
    out.release()
    
    return {
        "adapterId": "drone-tracker",
        "repository": "vendor/drone-tracker",
        "model": "YOLOv8 / phase2_finetuned_final_best.pt",
        "executionStatus": "FULLY RUNNING",
        "ran": True,
        "input": str(video_path),
        "findings": findings,
        "artifact": str(output_video),
        "statistics": {
            "totalFrames": frame_count,
            "framesProcessed": frame_count // sample_rate,
            "totalDetections": total_detections,
            "uniqueTrackIds": len(track_ids),
            "trackIds": sorted(list(track_ids)),
        },
    }