#!/usr/bin/env python3
"""DRIFT remote worker."""
from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import redis

from all12_executor import execute_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("drift-worker")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
QUEUE = os.environ.get("WORKER_QUEUE_NAME", "drift-inference")
OBJECT_STORAGE_ENDPOINT = os.environ.get("OBJECT_STORAGE_ENDPOINT")
OBJECT_STORAGE_ACCESS_KEY = os.environ.get("OBJECT_STORAGE_ACCESS_KEY")
OBJECT_STORAGE_SECRET_KEY = os.environ.get("OBJECT_STORAGE_SECRET_KEY")
OBJECT_STORAGE_BUCKET = os.environ.get("OBJECT_STORAGE_BUCKET", "drift-storage")
MODEL_CACHE_DIR = Path(os.environ.get("MODEL_CACHE_DIR", "/models"))

redis_client = redis.from_url(REDIS_URL, decode_responses=True)
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
    s3_client.download_file(bucket, key, str(target))
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


def normalize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Expose the all-12 executor through the dashboard's stable mission contract."""
    records = summary.get("results", [])
    adapters = []
    findings: list[dict[str, Any]] = []
    for record in records:
        repo = record.get("repository", "unknown")
        status = record.get("status", "UNKNOWN")
        adapters.append({
            "adapterId": repo,
            "repository": repo,
            "model": record.get("mode", "upstream adapter"),
            "executionStatus": status,
            "reason": record.get("detail", ""),
            "contribution": record.get("detail", ""),
            "ran": bool(record.get("ran")),
            "artifact": record.get("artifact"),
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
        srt = download(message.get("srt_uri"), work / "mission.srt")
        geotiff = download(message.get("geotiff_uri"), work / "mission.tif")
        als = download(message.get("als_uri"), work / "mission.laz")
        rgb = download(message.get("rgb_image_uri"), work / "rgb.jpg")
        image = download(message.get("image_uri"), work / "image.jpg")
        telemetry = download(message.get("telemetry_uri"), work / "telemetry.bin")
        dem = download(message.get("dem_uri"), work / "dem.tif")
        streams = download(message.get("streams_uri"), work / "streams.gpkg")
        arran = download(message.get("arran_data_uri"), work / "arran-data")
        foundation_input = download(message.get("foundation_input_uri"), work / "foundation-input")

        if video is None:
            raise RuntimeError("no video input supplied")

        update_job(run_id, "running", 0.15, "executing upstream repository pipeline")
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
        summary = execute_all(args)
        summary["runId"] = run_id
        normalized = normalize_summary(summary)
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
        item = redis_client.blpop(QUEUE, timeout=5)
        if item is None:
            continue
        _, payload = item
        try:
            process_job(json.loads(payload))
        except Exception:
            logger.exception("invalid worker payload")


if __name__ == "__main__":
    raise SystemExit(main())
