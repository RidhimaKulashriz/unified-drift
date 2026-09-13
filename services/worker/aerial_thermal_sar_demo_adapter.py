"""Adapter for Aerial Thermal SAR Detection Demo (Hugging Face Space).

This adapter executes the upstream Gradio demo that compares YOLOv12 and RT-DETRv2
for thermal human detection.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from huggingface_hub import hf_hub_download
from ultralytics import YOLO, RTDETR
import cv2
import numpy as np

YOLO_MODEL_URL = "https://huggingface.co/Kiuyha/yolov12-human-detection-thermal-uav/resolve/main/best.pt"
RTDETR_MODEL_URL = "https://huggingface.co/Kiuyha/rtdetrv2-human-detection-thermal-uav/resolve/main/best.pt"


def run_on_image(image_path: Path, output_dir: Path) -> dict[str, Any]:
    """Execute upstream YOLOv12 and RT-DETRv2 inference on thermal image."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Download models from Hugging Face
        yolo_model_path = hf_hub_download(
            repo_id="Kiuyha/yolov12-human-detection-thermal-uav",
            filename="best.pt"
        )
        rtdetr_model_path = hf_hub_download(
            repo_id="Kiuyha/rtdetrv2-human-detection-thermal-uav",
            filename="best.pt"
        )
        
        # Load models
        yolo_model = YOLO(yolo_model_path)
        rtdetr_model = RTDETR(rtdetr_model_path)
        
        # Load image
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        # Run YOLOv12 inference
        yolo_results = yolo_model.predict(image, conf=0.25, verbose=False)
        yolo_image_with_boxes = yolo_results[0].plot()
        
        # Run RT-DETRv2 inference
        rtdetr_results = rtdetr_model.predict(image, conf=0.25, verbose=False)
        rtdetr_image_with_boxes = rtdetr_results[0].plot()
        
        # Extract findings from YOLOv12 results
        findings: list[dict[str, Any]] = []
        boxes = yolo_results[0].boxes
        if boxes is not None:
            names = yolo_results[0].names if hasattr(yolo_results[0], "names") else {0: "person"}
            for box in boxes:
                xyxy = [round(float(value), 3) for value in box.xyxy[0].tolist()]
                confidence = round(float(box.conf[0]), 6)
                class_id = int(box.cls[0])
                label = names[class_id] if isinstance(names, dict) else str(class_id)
                findings.append({
                    "type": "detection",
                    "module": "thermal-sar-demo",
                    "label": label,
                    "confidence": confidence,
                    "bboxPixels": xyxy,
                    "source": {
                        "repository": "huggingface.co/spaces/Kiuyha/Aerial-Thermal-SAR-Detection-Demo",
                        "model": "YOLOv12 + RT-DETRv2",
                        "checkpoint": yolo_model_path,
                    },
                })
        
        # Save annotated images
        cv2.imwrite(str(output_dir / "yolov12_detections.jpg"), yolo_image_with_boxes)
        cv2.imwrite(str(output_dir / "rtdetrv2_detections.jpg"), rtdetr_image_with_boxes)
        
        return {
            "adapterId": "aerial-thermal-sar-detection-demo",
            "repository": "vendor/aerial-thermal-sar-detection-demo",
            "model": "YOLOv12 + RT-DETRv2 / best.pt",
            "executionStatus": "FULLY RUNNING",
            "ran": True,
            "input": str(image_path),
            "findings": findings,
            "artifacts": {
                "yolov12": str(output_dir / "yolov12_detections.jpg"),
                "rtdetrv2": str(output_dir / "rtdetrv2_detections.jpg"),
            },
            "modelUrls": {
                "yolov12": YOLO_MODEL_URL,
                "rtdetrv2": RTDETR_MODEL_URL,
            },
        }
    except Exception as exc:
        raise RuntimeError(f"Aerial Thermal SAR Demo adapter failed: {exc}") from exc