#!/usr/bin/env python3
"""DRIFT remote worker."""
from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import redis

from all12_executor import execute_all
from rgb12_track import execute_rgb12

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("drift-worker")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
QUEUE = os.environ.get("WORKER_QUEUE_NAME", "drift-inference")
ACTIVE_RUN_KEY = "drift:active_run"
OBJECT_STORAGE_ENDPOINT = os.environ.get("OBJECT_STORAGE_ENDPOINT")
OBJECT_STORAGE_ACCESS_KEY = os.environ.get("OBJECT_STORAGE_ACCESS_KEY")
OBJECT_STORAGE_SECRET_KEY = os.environ.get("OBJECT_STORAGE_SECRET_KEY")
OBJECT_STORAGE_BUCKET = os.environ.get("OBJECT_STORAGE_BUCKET", "drift-storage")
MODEL_CACHE_DIR = Path(os.environ.get("MODEL_CACHE_DIR", "/models"))

redis_client = redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=15,
    socket_timeout=None,
    health_check_interval=30,
    retry_on_timeout=True,
)
s3_client = None
if OBJECT_STORAGE_ENDPOINT:
    s3_client = boto3.client("s3", endpoint_url=OBJECT_STORAGE_ENDPOINT, aws_access_key_id=OBJECT_STORAGE_ACCESS_KEY, aws_secret_access_key=OBJECT_STORAGE_SECRET_KEY)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def update_job(run_id: str, status: str, progress: float, stage: str, results: dict[str, Any] | None = None, error: str | None = None) -> None:
    raw = redis_client.get(f"job:{run_id}")
    job = json.loads(raw) if raw else {"run_id": run_id}
    job.update({"status": status, "progress": progress, "current_stage": stage, "updated_at": _now()})
    if results is not None:
        job["results"] = results
    if error is not None:
        job["error"] = error
    redis_client.set(f"job:{run_id}", json.dumps(job))


def _parse_uri(uri: str) -> tuple[str, str]:
    value = uri[5:] if uri.startswith("s3://") else uri
    bucket, key = value.split("/", 1)
    return bucket, key


def download(uri: str | None, target: Path) -> Path | None:
    if not uri:
        return None
    if not s3_client:
        raise RuntimeError("OBJECT_STORAGE_ENDPOINT is not configured")
    bucket, key = _parse_uri(uri)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Backblaze credentials may allow GetObject while rejecting HeadObject;
    # boto3.download_file performs HeadObject and causes the observed 403.
    response = s3_client.get_object(Bucket=bucket, Key=key)
    with target.open("wb") as handle:
        while True:
            chunk = response["Body"].read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    if not target.exists() or target.stat().st_size == 0:
        raise RuntimeError(f"downloaded empty object: {uri}")
    return target


def write_inline(encoded: str | None, target: Path, label: str) -> Path | None:
    if not encoded:
        return None
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise RuntimeError(f"invalid inline {label} payload") from exc
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    if not target.exists() or target.stat().st_size == 0:
        raise RuntimeError(f"inline {label} payload is empty")
    return target


def publish_visual_artifacts(summary: dict[str, Any], run_id: str, source_frame: Path | None = None) -> None:
    """Keep visual evidence available after the temporary job directory is removed.

    Adapters that only emit JSON still receive the actual extracted input frame as
    source evidence; it is never presented as an annotated detection result.
    """
    if not s3_client:
        return
    for record in summary.get("results", []):
        artifact = record.get("artifact") or record.get("visualArtifactPath")
        if not artifact:
            continue
        root = Path(str(artifact))
        image_suffixes = {".jpg", ".jpeg", ".png"}
        video_suffixes = {".mp4", ".webm", ".mov"}
        if root.is_file() and root.suffix.lower() in image_suffixes | video_suffixes:
            candidates = [root]
        else:
            candidates = list(root.rglob("*.jpg")) + list(root.rglob("*.jpeg")) + list(root.rglob("*.png")) + list(root.rglob("*.mp4")) + list(root.rglob("*.webm")) + list(root.rglob("*.mov"))
        candidates = [path for path in candidates if path.is_file() and path.stat().st_size > 0]
        is_source_frame = not candidates
        if is_source_frame:
            if source_frame is None or not source_frame.is_file() or source_frame.stat().st_size == 0:
                continue
            image = source_frame
        else:
            image = max(candidates, key=lambda path: path.stat().st_size)
        repository = str(record.get("repository", "adapter")).replace("/", "-")
        if is_source_frame:
            # Give every repository its own honest visual artifact. For a real
            # detector, draw only the boxes returned by that adapter. For an
            # input-gated/non-video repository, label the frame instead of
            # inventing a detection.
            try:
                from PIL import Image, ImageDraw
                evidence = Image.open(image).convert("RGB")
                draw = ImageDraw.Draw(evidence)
                findings = record.get("findingRecords", []) or []
                for finding in findings:
                    box = finding.get("bboxPixels") if isinstance(finding, dict) else None
                    if not isinstance(box, (list, tuple)) or len(box) != 4:
                        continue
                    x1, y1, x2, y2 = [int(float(value)) for value in box]
                    draw.rectangle((x1, y1, x2, y2), outline=(216, 245, 156), width=4)
                    label = str(finding.get("label", "detection"))
                    confidence = finding.get("confidence")
                    if confidence is not None:
                        label += f" {float(confidence):.2f}"
                    draw.text((max(0, x1), max(0, y1 - 18)), label, fill=(216, 245, 156))
                banner = repository if findings else f"{repository} · no compatible video detection"
                draw.rectangle((0, 0, min(evidence.width, max(360, len(banner) * 8)), 28), fill=(10, 10, 10))
                draw.text((8, 7), banner, fill=(216, 245, 156))
                evidence_path = source_frame.parent / f"{repository}-evidence.jpg"
                evidence.save(evidence_path, format="JPEG", quality=90)
                image = evidence_path
            except Exception:
                # The source frame remains a valid fallback if PIL is absent.
                pass
        prefix = "source-frame" if is_source_frame else "annotated"
        key = f"results/{run_id}/{repository}/{prefix}-{image.name}"
        content_type = "image/png" if image.suffix.lower() == ".png" else ("video/mp4" if image.suffix.lower() == ".mp4" else ("video/webm" if image.suffix.lower() == ".webm" else ("video/quicktime" if image.suffix.lower() == ".mov" else "image/jpeg")))
        s3_client.upload_file(str(image), OBJECT_STORAGE_BUCKET, key, ExtraArgs={"ContentType": content_type})
        record["visualArtifactUri"] = f"s3://{OBJECT_STORAGE_BUCKET}/{key}"
        record["visualArtifactKind"] = "source-frame" if is_source_frame else ("annotated-video" if image.suffix.lower() in video_suffixes else "annotated")

def publish_normalized_artifact(normalized: dict[str, Any], output: Path, run_id: str) -> None:
    path = output / "normalized_drift.json"
    normalized["normalizedArtifactPath"] = str(path)
    path.write_text(json.dumps(normalized, indent=2, default=str), encoding="utf-8")
    if s3_client:
        key = f"results/{run_id}/normalized_drift.json"
        normalized["normalizedArtifactUri"] = f"s3://{OBJECT_STORAGE_BUCKET}/{key}"
        path.write_text(json.dumps(normalized, indent=2, default=str), encoding="utf-8")
        s3_client.upload_file(str(path), OBJECT_STORAGE_BUCKET, key, ExtraArgs={"ContentType": "application/json"})


def execution_gate(summary: dict[str, Any]) -> tuple[bool, str]:
    """Require every upstream entrypoint to execute with a real artifact."""
    records = summary.get("results", [])
    expected = 12
    if len(records) != expected:
        return False, f"expected {expected} upstream records, received {len(records)}"
    incomplete = []
    for record in records:
        if record.get("status") != "COMPLETED" or not record.get("ran") or not record.get("artifact"):
            incomplete.append(f"{record.get('repository', 'unknown')}: {record.get('status', 'UNKNOWN')} — {record.get('detail', '')}")
    if incomplete:
        return False, "; ".join(incomplete)
    return True, "all 12 upstream entrypoints produced verified artifacts"


def normalize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Expose the all-12 executor through the dashboard's stable mission contract."""
    records = summary.get("results", [])
    adapters = []
    findings: list[dict[str, Any]] = []
    for record in records:
        repo = record.get("repository", "unknown")
        status = record.get("status") or record.get("executionStatus", "UNKNOWN")
        adapters.append({
            "adapterId": repo,
            "repository": repo,
            "model": record.get("model") or record.get("mode", "upstream adapter"),
            "executionStatus": status,
            "reason": record.get("reason") or record.get("detail", ""),
            "contribution": record.get("contribution") or record.get("reason") or record.get("detail", ""),
            "ran": bool(record.get("ran")),
            "artifact": record.get("artifact"),
            "visualArtifactUri": record.get("visualArtifactUri"),
            "visualArtifactKind": record.get("visualArtifactKind"),
            "findingRecords": record.get("findingRecords", []),
        })
        for finding in record.get("findingRecords", []) or []:
            findings.append(finding)
    return {
        "runId": summary.get("runId"),
        "createdAt": summary.get("createdAt"),
        "adapters": adapters,
        "findings": findings,
        "executions": records,
        "fusion": {
            "method": "provenance-preserving all-12 execution ledger",
            "inputFindingCount": len(findings),
            "outputFindingCount": len(findings),
        },
        "summary": summary,
    }


def process_job(message: dict[str, Any]) -> bool:
    run_id = str(message["run_id"])
    active_run = redis_client.get(ACTIVE_RUN_KEY)
    if active_run and active_run != run_id:
        logger.info("Skipping stale run %s; active run is %s", run_id, active_run)
        return True
    work = Path(tempfile.mkdtemp(prefix=f"drift-{run_id}-"))
    output = work / "results"
    output.mkdir(parents=True, exist_ok=True)
    try:
        update_job(run_id, "running", 0.05, "materializing inputs")
        video = write_inline(message.get("video_base64"), work / (message.get("video_file_name") or "video.mp4"), "video")
        thermal = write_inline(message.get("thermal_video_base64"), work / (message.get("thermal_video_file_name") or "thermal.mp4"), "thermal video")
        if video is None:
            video = download(message.get("video_uri"), work / "video.mp4")
        if thermal is None:
            thermal = download(message.get("thermal_video_uri"), work / "thermal.mp4")
        source_frame = work / "source-frame.jpg"
        frame_input = video or thermal
        if frame_input is not None:
            frame_result = subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(frame_input), "-frames:v", "1", str(source_frame)],
                capture_output=True, text=True, timeout=120,
            )
            if frame_result.returncode != 0 or not source_frame.is_file():
                source_frame = None
        srt = download(message.get("srt_uri"), work / "mission.srt")
        geotiff = download(message.get("geotiff_uri"), work / "mission.tif")
        als = download(message.get("als_uri"), work / "mission.laz")
        rgb = download(message.get("rgb_image_uri"), work / "rgb.jpg")
        image = download(message.get("image_uri"), work / "image.jpg")
        # Keep the source formats expected by upstream code; do not rename JSON
        # or GeoJSON fixtures to opaque .bin/.gpkg paths.
        telemetry = download(message.get("telemetry_uri"), work / "telemetry.json")
        dem = download(message.get("dem_uri"), work / "dem.tif")
        streams = download(message.get("streams_uri"), work / "streams.geojson")
        arran = download(message.get("arran_data_uri"), work / "arran-data.json")
        foundation_input = download(message.get("foundation_input_uri"), work / "foundation-input.json")

        # A TDM mission may contain only geospatial, telemetry, benchmark, or
        # simulator inputs. Do not force a video onto those upstream systems.
        if all(value is None for value in (video, thermal, rgb, image, srt, telemetry, geotiff, als, dem, streams, arran, foundation_input)):
            raise RuntimeError("no mission input supplied")

        update_job(run_id, "running", 0.15, "executing selected repository pipeline")
        active_run = redis_client.get(ACTIVE_RUN_KEY)
        if active_run and active_run != run_id:
            update_job(run_id, "failed", 1.0, "cancelled", error="Superseded by a newer user submission")
            return True
        execution_mode = message.get("execution_mode", "real-upstream")
        if execution_mode in {"rgb12", "synthetic-demo"}:
            track = execute_rgb12(video, output / execution_mode, synthetic=execution_mode == "synthetic-demo")
            summary = {"runId": run_id, "createdAt": _now(), "totalRepositories": len(track["results"]), "results": track["results"], "mode": execution_mode}
            publish_visual_artifacts(summary, run_id, source_frame)
            normalized = normalize_summary(summary)
            publish_normalized_artifact(normalized, output, run_id)
            update_job(run_id, "completed", 1.0, "completed", normalized)
            return True
        class Args:
            pass
        args = Args()
        args.output = output
        args.video = video
        args.thermal_video = thermal
        args.rgb_image = rgb
        args.image = image
        args.srt = srt
        args.telemetry = telemetry
        args.geotiff = geotiff
        args.als = als
        args.dem = dem
        args.streams = streams
        args.arran_data = arran
        args.foundation_input = foundation_input
        args.experiment = message.get("experiment")
        args.samples = int(message.get("samples", 3))
        def pipeline_progress(completed: int, entrypoint: str, record: dict[str, Any]) -> None:
            if redis_client.get(ACTIVE_RUN_KEY) not in (None, run_id):
                raise RuntimeError("Superseded by a newer user submission")
            progress = min(0.95, 0.15 + (completed / 12.0) * 0.80)
            stage = f"running {entrypoint} ({completed}/12 complete)" if record.get("status") == "RUNNING" else f"completed {completed}/12: {entrypoint}"
            update_job(run_id, "running", progress, stage)

        summary = execute_all(args, progress_callback=pipeline_progress)
        summary["runId"] = run_id
        publish_visual_artifacts(summary, run_id, source_frame)
        normalized = normalize_summary(summary)
        publish_normalized_artifact(normalized, output, run_id)
        passed, gate_message = execution_gate(summary)
        if not passed:
            update_job(run_id, "failed", 1.0, "execution incomplete", normalized, error=gate_message)
            return False
        update_job(run_id, "completed", 1.0, "completed", normalized)
        return True
    except Exception as exc:
        logger.exception("job %s failed", run_id)
        update_job(run_id, "failed", 1.0, "failed", error=str(exc))
        return False
    finally:
        shutil.rmtree(work, ignore_errors=True)


def health() -> dict[str, Any]:
    gpu: dict[str, Any] = {"available": False, "name": None, "vramMb": None}
    try:
        import torch
        gpu["available"] = bool(torch.cuda.is_available())
        if gpu["available"]:
            gpu["name"] = torch.cuda.get_device_name(0)
            gpu["vramMb"] = round(torch.cuda.get_device_properties(0).total_memory / 1024 / 1024)
    except Exception as exc:
        gpu["error"] = str(exc)
    try:
        redis_client.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    return {"worker": "remote-worker", "gpu": gpu, "redis": redis_ok, "objectStorage": bool(s3_client), "modelCache": str(MODEL_CACHE_DIR), "timestamp": _now()}


def main() -> int:
    logger.info("DRIFT worker starting: %s", health())
    while True:
        try:
            item = redis_client.blpop(QUEUE, timeout=5)
        except redis.exceptions.TimeoutError:
            logger.warning("Redis BLPOP timed out; reconnecting without dropping the worker")
            try:
                redis_client.connection_pool.disconnect()
            except Exception:
                pass
            continue
        except redis.exceptions.ConnectionError:
            logger.exception("Redis connection lost; retrying worker loop")
            continue
        if item is None:
            continue
        _, payload = item
        try:
            process_job(json.loads(payload))
        except Exception:
            logger.exception("invalid worker payload")


if __name__ == "__main__":
    raise SystemExit(main())
