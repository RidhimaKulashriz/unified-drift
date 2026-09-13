#!/usr/bin/env python3
"""DRIFT remote worker.

The worker is intentionally thin: it downloads mission inputs, invokes the
single strict all12 executor, uploads artifacts, and updates Redis status.
Heavy model/runtime work stays on the remote worker.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import redis
from botocore.exceptions import ClientError

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
    s3_client = boto3.client(
        "s3",
        endpoint_url=OBJECT_STORAGE_ENDPOINT,
        aws_access_key_id=OBJECT_STORAGE_ACCESS_KEY,
        aws_secret_access_key=OBJECT_STORAGE_SECRET_KEY,
    )


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
    redis_client.set(f"job_status:{run_id}", status)


def _parse_uri(uri: str) -> tuple[str, str]:
    if uri.startswith("s3://"):
        value = uri[5:]
        bucket, key = value.split("/", 1)
        return bucket, key
    return OBJECT_STORAGE_BUCKET, uri


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


def upload(path: Path, key: str) -> str:
    if not s3_client:
        raise RuntimeError("OBJECT_STORAGE_ENDPOINT is not configured")
    s3_client.upload_file(str(path), OBJECT_STORAGE_BUCKET, key)
    return f"s3://{OBJECT_STORAGE_BUCKET}/{key}"


def _arg(ns: dict[str, Any], key: str) -> str | None:
    value = ns.get(key)
    return str(value) if value else None


def process_job(message: dict[str, Any]) -> bool:
    run_id = str(message["run_id"])
    work = Path(tempfile.mkdtemp(prefix=f"drift-{run_id}-"))
    output = work / "results"
    output.mkdir(parents=True, exist_ok=True)
    try:
        update_job(run_id, "running", 0.05, "downloading inputs")
        video = download(_arg(message, "video_uri"), work / "video.mp4")
        thermal = download(_arg(message, "thermal_video_uri"), work / "thermal.mp4")
        srt = download(_arg(message, "srt_uri"), work / "mission.srt")
        geotiff = download(_arg(message, "geotiff_uri"), work / "mission.tif")
        als = download(_arg(message, "als_uri"), work / "mission.laz")
        rgb = download(_arg(message, "rgb_image_uri"), work / "rgb.jpg")
        image = download(_arg(message, "image_uri"), work / "image.jpg")
        telemetry = download(_arg(message, "telemetry_uri"), work / "telemetry.bin")
        dem = download(_arg(message, "dem_uri"), work / "dem.tif")
        streams = download(_arg(message, "streams_uri"), work / "streams.gpkg")
        arran = download(_arg(message, "arran_data_uri"), work / "arran-data")
        foundation_input = download(_arg(message, "foundation_input_uri"), work / "foundation-input")

        update_job(run_id, "running", 0.15, "executing all applicable upstream repositories")
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

        update_job(run_id, "running", 0.85, "uploading result artifacts")
        uploaded: list[str] = []
        for artifact in output.rglob("*"):
            if artifact.is_file():
                uploaded.append(upload(artifact, f"runs/{run_id}/{artifact.relative_to(output).as_posix()}"))
        summary["uploadedArtifacts"] = uploaded
        update_job(run_id, "completed", 1.0, "completed", summary)
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
    storage = False
    if s3_client:
        try:
            s3_client.head_bucket(Bucket=OBJECT_STORAGE_BUCKET)
            storage = True
        except Exception:
            storage = False
    try:
        redis_client.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    return {"worker": "remote-worker", "gpu": gpu, "redis": redis_ok, "objectStorage": storage, "modelCache": str(MODEL_CACHE_DIR), "timestamp": _now()}


def main() -> int:
    logger.info("DRIFT worker starting: %s", health())
    while True:
        item = redis_client.blpop(QUEUE, timeout=5)
        if item is None:
            continue
        _, payload = item
        try:
            message = json.loads(payload)
            process_job(message)
        except Exception:
            logger.exception("invalid worker payload")


if __name__ == "__main__":
    raise SystemExit(main())
