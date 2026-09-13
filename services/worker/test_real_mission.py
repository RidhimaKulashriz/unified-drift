#!/usr/bin/env python3
"""Acceptance test for one uploaded RGB + thermal mission.

The test uses valid generated MP4 inputs, executes the published upstream
RT-DETRv2 checkpoint, and asserts that DRIFT returns real provenance-bearing
outputs rather than only adapter status records.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from run_pipeline import run

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "models" / "aerial-thermal-rtdetrv2-best.pt"


def main() -> int:
    if not MODEL.exists():
        raise SystemExit(f"missing checkpoint: {MODEL}; run scripts/download_models.sh")
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is required")
    with tempfile.TemporaryDirectory(prefix="drift-acceptance-") as tmp:
        root = Path(tmp)
        rgb = root / "rgb.mp4"
        thermal = root / "thermal.mp4"
        srt = root / "thermal.SRT"
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=2", "-t", "1", str(rgb)], check=True)
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=gray:size=640x360:rate=2", "-t", "1", str(thermal)], check=True)
        srt.write_text("1\n00:00:00,000 --> 00:00:00,500\n[latitude: 24.7136] [longitude: 46.6753] [rel_alt: 40.0 abs_alt: 640.0] [gb_yaw: 0.0 gb_pitch: -90.0 gb_roll: 0.0]\n")
        result = run(rgb, root / "run", thermalVideo=thermal, srt=srt, geotiff=None, als=None)
        thermal_adapter = next(item for item in result["adapters"] if item["adapterId"] == "aerial-thermal-detection")
        assert thermal_adapter["executionStatus"] == "FULLY RUNNING", thermal_adapter
        assert thermal_adapter["ran"] is True
        geo_adapter = next(item for item in result["adapters"] if item["adapterId"] == "uav-thermal-person-geolocation")
        assert geo_adapter["executionStatus"] == "PARTIALLY INTEGRATED", geo_adapter
        assert geo_adapter["ran"] is True
        assert len(result["executions"]) == 2, "expected detector and geolocation executions"
        assert result["findings"], "expected real model outputs"
        assert result["findings"][0]["source"]["repository"].startswith("github.com/kiuyha/")
        assert any("location" in finding for finding in result["findings"]), "expected upstream GPS projection"
        assert result["fusion"]["outputFindingCount"] == len(result["findings"])
        print(json.dumps({"runId": result["runId"], "executedRepositories": [item["repository"] for item in result["executions"]], "models": [item["model"] for item in result["executions"]], "findingCount": len(result["findings"]), "accepted": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
