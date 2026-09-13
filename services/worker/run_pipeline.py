#!/usr/bin/env python3
"""Execution-first DRIFT worker.

This worker deliberately does not fabricate detections. It always performs real
ffprobe metadata inspection and ffmpeg frame extraction, then evaluates each
upstream adapter against the uploaded inputs and records why it can or cannot
run. Model adapters are only marked FULLY RUNNING when their required runtime
and checkpoint are present.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "services" / "worker" / "adapter-manifest.json"

STATUS = {
    "FULLY RUNNING",
    "PARTIALLY INTEGRATED",
    "INPUT NOT COMPATIBLE",
    "DEPENDENCY BLOCKED",
    "DATASET/TOOL ONLY",
}


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def command_output(command: list[str]) -> str:
    completed = subprocess.run(command, capture_output=True, text=True, check=True)
    return completed.stdout


def probe_media(path: Path) -> dict[str, Any]:
    raw = command_output([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ])
    parsed = json.loads(raw)
    streams = parsed.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise ValueError("uploaded input has no video stream")
    return {
        "filename": path.name,
        "bytes": path.stat().st_size,
        "durationSeconds": float(parsed.get("format", {}).get("duration", 0) or 0),
        "width": video.get("width"),
        "height": video.get("height"),
        "fps": video.get("r_frame_rate"),
        "codec": video.get("codec_name"),
        "streams": len(streams),
    }


def probe_image_dimensions(path: Path) -> tuple[int, int]:
    parsed = json.loads(command_output(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", str(path)]))
    stream = next(item for item in parsed.get("streams", []) if item.get("codec_type") == "video")
    return int(stream["width"]), int(stream["height"])


def extract_frame(path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "frame-000001.jpg"
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-vf", "thumbnail,scale=1280:-2", "-frames:v", "1", str(output),
    ], check=True)
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("ffmpeg did not produce an evidence frame")
    return output


def run_real_thermal_adapter(thermal_video: Path, output_dir: Path) -> dict[str, Any]:
    """Run the upstream thermal detector when its published checkpoint exists."""
    thermal_dir = output_dir / "thermal"
    thermal_frame = extract_frame(thermal_video, thermal_dir)
    from aerial_thermal_adapter import run_on_image
    return run_on_image(thermal_frame, output_dir / "adapters")


def run_real_geolocation_adapter(srt: Path, findings: list[dict[str, Any]], image_width: int, image_height: int) -> dict[str, Any]:
    """Execute the upstream Gruzver SRT parser and pixel-to-GPS utility."""
    repo_src = ROOT / "vendor" / "uav-thermal-person-geolocation" / "src" / "drone_tracker_utils"
    if not repo_src.exists():
        raise FileNotFoundError(f"upstream geolocation source missing: {repo_src}")
    sys.path.insert(0, str(repo_src))
    from drone_tracker_utils.geo_calculator import GeoCalculator
    from drone_tracker_utils.srt_parser import SRTParser
    telemetry = SRTParser(str(srt)).parse()
    if not telemetry:
        raise ValueError("SRT contained no parseable DJI telemetry frames")
    frame = telemetry[0]
    calculator = GeoCalculator()
    projected = 0
    for finding in findings:
        box = finding.get("bboxPixels")
        if not box:
            continue
        x1, y1, x2, y2 = box
        x = ((x1 + x2) / 2.0) * 640.0 / image_width
        y = ((y1 + y2) / 2.0) * 512.0 / image_height
        location = calculator.pixel_to_gps(x, y, frame.latitude, frame.longitude, frame.altitude_rel, frame.yaw, frame.pitch, frame.roll)
        if location is not None:
            finding["location"] = {"lat": location.latitude, "lon": location.longitude, "accuracyM": location.distance_m}
            projected += 1
    return {
        "adapterId": "uav-thermal-person-geolocation",
        "repository": "vendor/uav-thermal-person-geolocation",
        "model": "GeoCalculator + SRTParser (upstream source)",
        "executionStatus": "PARTIALLY INTEGRATED",
        "ran": True,
        "findingsProjected": projected,
        "source": "github.com/Gruzver/uav-thermal-person-geolocation",
        "reason": "upstream telemetry parser and pixel-to-GPS stage executed; ROS2 detector node/checkpoint remains unavailable",
    }


def adapter_decision(adapter: dict[str, Any], inputs: dict[str, Path | None]) -> dict[str, Any]:
    aid = adapter["id"]
    repo = ROOT / adapter["repo"]
    required = adapter.get("requiredRuntime", [])
    missing_runtime = [binary for binary in required if shutil.which(binary) is None]
    has_video = inputs.get("video") is not None
    has_thermal = inputs.get("thermalVideo") is not None
    has_srt = inputs.get("srt") is not None
    has_geo = inputs.get("geotiff") is not None or inputs.get("als") is not None

    if adapter.get("kind") in {"benchmark", "training", "simulator", "ground-station", "review-training", "notebooks"}:
        status = "DATASET/TOOL ONLY"
        reason = "upstream repository is not a video inference runtime"
    elif aid == "rgbt-fusion-drone-sar" and not (has_video and has_thermal):
        status = "INPUT NOT COMPATIBLE"
        reason = "requires both RGB video and a thermal video pair"
    elif aid in {"uav-thermal-person-geolocation", "aerial-thermal-detection", "aerial-thermal-sar-detection-demo"} and not has_thermal:
        status = "INPUT NOT COMPATIBLE"
        reason = "requires a thermal video or thermal frames"
    elif aid == "uav-thermal-person-geolocation" and not has_srt:
        status = "DEPENDENCY BLOCKED"
        reason = "thermal input exists, but SRT telemetry is required"
    elif aid in {"adaf", "simulated-training-data", "foundation-models-archaeology"} and not has_geo:
        status = "INPUT NOT COMPATIBLE"
        reason = "requires ALS, GeoTIFF, LiDAR, or satellite input"
    elif not repo.exists():
        status = "DEPENDENCY BLOCKED"
        reason = "vendored upstream source is absent from this deployment"
    elif missing_runtime:
        status = "DEPENDENCY BLOCKED"
        reason = "required runtime binaries are missing: " + ", ".join(missing_runtime)
    elif not adapter.get("checkpointPresent", False):
        status = "DEPENDENCY BLOCKED"
        reason = "upstream source is present, but no model checkpoint is configured"
    else:
        status = "PARTIALLY INTEGRATED"
        reason = "input and runtime are available; adapter execution hook is next"

    return {
        "repository": adapter["repo"],
        "adapterId": aid,
        "model": adapter.get("model", adapter.get("label")),
        "executionStatus": status,
        "reason": reason,
        "ran": status in {"FULLY RUNNING", "PARTIALLY INTEGRATED"},
        "contribution": "media inspection and capability evaluation" if status != "FULLY RUNNING" else "upstream inference output",
    }


def run(video: Path, output_dir: Path, **input_paths: Path | None) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = probe_media(video)
    frame = extract_frame(video, output_dir)
    inputs = {"video": video, **input_paths}
    decisions = [adapter_decision(item, inputs) for item in load_manifest()["adapters"]]
    findings: list[dict[str, Any]] = []
    execution_log: list[dict[str, Any]] = []
    thermal = inputs.get("thermalVideo")
    if thermal is not None:
        thermal_decision = next(item for item in decisions if item["adapterId"] == "aerial-thermal-detection")
        try:
            actual = run_real_thermal_adapter(thermal, output_dir)
            thermal_decision.update({
                "executionStatus": actual["executionStatus"],
                "ran": True,
                "reason": "upstream RT-DETRv2 checkpoint executed successfully",
                "model": actual["model"],
                "contribution": f"{len(actual['findings'])} thermal person detections",
            })
            findings.extend(actual["findings"])
            execution_log.append(actual)
            if inputs.get("srt") is not None and findings:
                geo_decision = next(item for item in decisions if item["adapterId"] == "uav-thermal-person-geolocation")
                try:
                    thermal_width, thermal_height = probe_image_dimensions(output_dir / "thermal" / "frame-000001.jpg")
                    geo = run_real_geolocation_adapter(inputs["srt"], findings, thermal_width, thermal_height)
                    geo_decision.update({"executionStatus": geo["executionStatus"], "ran": True, "reason": geo["reason"], "model": geo["model"], "contribution": f"{geo['findingsProjected']} detections projected to GPS"})
                    execution_log.append(geo)
                except Exception as exc:
                    geo_decision.update({"executionStatus": "DEPENDENCY BLOCKED", "ran": False, "reason": f"upstream geolocation stage failed: {exc}"})
        except Exception as exc:
            thermal_decision.update({
                "executionStatus": "DEPENDENCY BLOCKED",
                "ran": False,
                "reason": f"upstream adapter failed before producing output: {exc}",
            })
    result = {
        "runId": uuid.uuid4().hex,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "source": {"repository": "DRIFT orchestrator", "model": "ffprobe + ffmpeg media evidence path"},
        "input": metadata,
        "artifacts": [{"type": "keyframe", "path": str(frame.relative_to(output_dir))}],
        "adapters": decisions,
        "findings": findings,
        "executions": execution_log,
        "fusion": {
            "method": "provenance-preserving concatenation with repository/model attribution",
            "inputFindingCount": len(findings),
            "outputFindingCount": len(findings),
        },
        "note": "No detector finding is emitted without a compatible upstream checkpoint and runnable adapter.",
    }
    (output_dir / "run.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: run_pipeline.py VIDEO OUTPUT_DIR [--thermal-video PATH] [--srt PATH] [--geotiff PATH] [--als PATH]", file=sys.stderr)
        return 2
    video = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    values: dict[str, Path | None] = {"thermalVideo": None, "srt": None, "geotiff": None, "als": None}
    args = iter(sys.argv[3:])
    for arg in args:
        if not arg.startswith("--"):
            raise SystemExit(f"unexpected argument: {arg}")
        key = arg[2:].replace("-", "")
        mapping = {"thermalvideo": "thermalVideo", "srt": "srt", "geotiff": "geotiff", "als": "als"}
        if key not in mapping:
            raise SystemExit(f"unknown input flag: {arg}")
        values[mapping[key]] = Path(next(args)).resolve()
    print(json.dumps(run(video, output, **values), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
