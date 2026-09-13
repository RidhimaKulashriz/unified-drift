#!/usr/bin/env python3
"""Generate safe, synthetic DRIFT input fixtures for local acceptance testing.

These files are clearly labeled demo data. They never claim that an ML model found
something; they only make every adapter input contract testable without field data.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo-mission"


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=4", "-t", "3", str(OUT / "rgb-video.mp4")])
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=gray:size=640x360:rate=4", "-t", "3", str(OUT / "thermal-video.mp4")])
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(OUT / "rgb-video.mp4"), "-frames:v", "1", str(OUT / "rgb-frame.jpg")])
    (OUT / "thermal-video.SRT").write_text(
        "1\n00:00:00,000 --> 00:00:00,750\n"
        "[latitude: 24.7136] [longitude: 46.6753] [rel_alt: 40.0 abs_alt: 640.0] "
        "[gb_yaw: 0.0 gb_pitch: -90.0 gb_roll: 0.0]\n\n",
        encoding="utf-8",
    )
    (OUT / "streams.geojson").write_text(json.dumps({
        "type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"demo": True}, "geometry": {"type": "LineString", "coordinates": [[46.6753, 24.7136], [46.6760, 24.7140]]}}]
    }, indent=2), encoding="utf-8")
    transform = from_origin(46.6753, 24.7140, 0.00001, 0.00001)
    elevation = np.arange(256, dtype=np.float32).reshape(16, 16)
    for name in ("terrain.tif", "dem.tif"):
        with rasterio.open(OUT / name, "w", driver="GTiff", height=16, width=16, count=1, dtype="float32", crs="EPSG:4326", transform=transform) as dataset:
            dataset.write(elevation, 1)
    (OUT / "telemetry.json").write_text(json.dumps({"demo": True, "source": "synthetic", "vehicle": "DRIFT acceptance fixture", "latitude": 24.7136, "longitude": 46.6753}, indent=2), encoding="utf-8")
    (OUT / "arran-data.json").write_text(json.dumps({"demo": True, "annotations": [], "note": "Synthetic benchmark container; no real archaeological labels."}, indent=2), encoding="utf-8")
    (OUT / "foundation-input.json").write_text(json.dumps({"demo": True, "inputType": "synthetic satellite placeholder"}, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text("""# DRIFT demo mission pack

This pack contains synthetic inputs for local contract testing. It is not field data and it must not be used to claim archaeological or person-detection findings.

- `rgb-video.mp4`: synthetic RGB video
- `thermal-video.mp4`: synthetic grayscale thermal-shaped video
- `thermal-video.SRT`: synthetic DJI-style telemetry
- `streams.geojson`: synthetic stream vector
- `telemetry.json`: synthetic ground-station telemetry
- `arran-data.json`: synthetic benchmark container
- `foundation-input.json`: synthetic foundation-model input placeholder

A real GeoTIFF/ALS/LiDAR file and ROS2 runtime are still required for those adapters to execute their upstream code.
""", encoding="utf-8")
    print(f"Created demo mission pack at {OUT}")


if __name__ == "__main__":
    main()
