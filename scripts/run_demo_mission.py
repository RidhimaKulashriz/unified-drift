#!/usr/bin/env python3
"""Run the all-12 executor against the generated demo mission pack."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "services" / "worker"))
from all12_executor import execute_all


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, default=ROOT / "demo-mission")
    parser.add_argument("--output", type=Path, default=ROOT / "demo-mission" / "run-output")
    args = parser.parse_args()
    pack = args.pack.resolve()
    run_args = SimpleNamespace(
        output=args.output.resolve(),
        video=pack / "rgb-video.mp4",
        thermal_video=pack / "thermal-video.mp4",
        rgb_image=pack / "rgb-frame.jpg",
        image=None,
        srt=pack / "thermal-video.SRT",
        telemetry=pack / "telemetry.json",
        geotiff=None,
        als=None,
        dem=None,
        streams=pack / "streams.geojson",
        arran_data=pack / "arran-data.json",
        foundation_input=pack / "foundation-input.json",
        experiment=None,
        samples=3,
    )
    summary = execute_all(run_args)
    print(json.dumps({
        "runId": summary.get("runId"),
        "totalRepositories": summary["totalRepositories"],
        "completed": summary["completed"],
        "failed": summary["failed"],
        "inputRequired": summary["inputRequired"],
        "runtimeRequired": summary["runtimeRequired"],
        "dependencyRequired": summary["dependencyRequired"],
        "modules": [{"topic": item["repository"], "status": item["status"], "ran": item["ran"], "detail": item["detail"]} for item in summary["results"]],
    }, indent=2))
    return 0 if len(summary["results"]) == 12 else 1


if __name__ == "__main__":
    raise SystemExit(main())
