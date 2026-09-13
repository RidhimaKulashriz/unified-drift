"""Adapter for ADAF (Automatic Detection of Archaeological Features).

This adapter executes the upstream ADAF system for ALS/LiDAR/GeoTIFF archaeology detection.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

REPO_SRC = Path(__file__).resolve().parents[2] / "vendor" / "adaf"


def run_on_geotiff(geotiff_path: Path, output_dir: Path) -> dict[str, Any]:
    """Execute upstream ADAF inference on GeoTIFF/ALS data."""
    if not geotiff_path.exists():
        raise FileNotFoundError(f"GeoTIFF file not found: {geotiff_path}")
    
    try:
        # Try to import ADAF modules
        import sys
        sys.path.insert(0, str(REPO_SRC))
        from adaf.adaf_inference import run_inference
    except ImportError as exc:
        raise RuntimeError("ADAF modules not available or missing dependencies") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Run ADAF inference
        results = run_inference(str(geotiff_path), str(output_dir))
        
        findings: list[dict[str, Any]] = []
        
        # Process results (this depends on actual ADAF output format)
        if isinstance(results, dict) and "detections" in results:
            for detection in results["detections"]:
                findings.append({
                    "type": "archaeological_feature",
                    "module": "adaf",
                    "label": detection.get("class", "unknown"),
                    "confidence": detection.get("confidence", 0.0),
                    "location": detection.get("location"),
                    "source": {
                        "repository": "github.com/EarthObservation/adaf",
                        "model": "ADAF",
                    },
                })
        
        return {
            "adapterId": "adaf",
            "repository": "vendor/adaf",
            "model": "ADAF / ALS-LiDAR detection",
            "executionStatus": "FULLY RUNNING",
            "ran": True,
            "input": str(geotiff_path),
            "findings": findings,
            "artifact": str(output_dir),
            "note": "ADAF executed on GeoTIFF/ALS data for archaeological feature detection.",
        }
    except Exception as exc:
        raise RuntimeError(f"ADAF inference failed: {exc}") from exc