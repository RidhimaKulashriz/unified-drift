#!/usr/bin/env python3
"""DRIFT orchestrator API."""
from __future__ import annotations

import asyncio
import base64
import binascii
import json
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
import redis
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
OBJECT_STORAGE_ENDPOINT = os.environ.get("OBJECT_STORAGE_ENDPOINT")
OBJECT_STORAGE_ACCESS_KEY = os.environ.get("OBJECT_STORAGE_ACCESS_KEY")
OBJECT_STORAGE_SECRET_KEY = os.environ.get("OBJECT_STORAGE_SECRET_KEY")
OBJECT_STORAGE_BUCKET = os.environ.get("OBJECT_STORAGE_BUCKET", "drift-storage")
WORKER_QUEUE_NAME = os.environ.get("WORKER_QUEUE_NAME", "drift-inference")
MAX_INLINE_BYTES = int(os.environ.get("MAX_INLINE_BYTES", str(256 * 1024 * 1024)))

app = FastAPI(title="DRIFT Orchestrator", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://unified-drift.vercel.app", "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
s3_client = None
if OBJECT_STORAGE_ENDPOINT:
    s3_client = boto3.client(
        "s3",
        endpoint_url=OBJECT_STORAGE_ENDPOINT,
        aws_access_key_id=OBJECT_STORAGE_ACCESS_KEY,
        aws_secret_access_key=OBJECT_STORAGE_SECRET_KEY,
    )

class MissionSubmission(BaseModel):
    video_uri: str | None = None
    thermal_video_uri: str | None = None
    rgb_image_uri: str | None = None
    image_uri: str | None = None
    srt_uri: str | None = None
    telemetry_uri: str | None = None
    mavlink_uri: str | None = None
    geotiff_uri: str | None = None
    als_uri: str | None = None
    dem_uri: str | None = None
    streams_uri: str | None = None
    satellite_uri: str | None = None
    arran_data_uri: str | None = None
    foundation_input_uri: str | None = None
    robot_simulation_uri: str | None = None
    video_base64: str | None = None
    video_file_name: str | None = None
    thermal_video_base64: str | None = None
    thermal_video_file_name: str | None = None
    experiment: str | None = None
    samples: int = Field(default=3, ge=1, le=100)
    enabled_modules: list[str] = Field(default_factory=list)

class JobStatus(BaseModel):
    run_id: str
    status: str
    created_at: str
    updated_at: str
    progress: float
    current_stage: str
    results: dict[str, Any] | None = None
    error: str | None = None

@app.get("/health")
def health() -> dict[str, Any]:
    try:
        redis_ok = bool(redis_client.ping())
    except Exception:
        redis_ok = False
    storage_mode = "s3" if s3_client else "disabled"
    storage_ok = False
    if s3_client:
        try:
            s3_client.head_bucket(Bucket=OBJECT_STORAGE_BUCKET)
            storage_ok = True
        except Exception:
            storage_ok = False
    return {"status": "healthy" if redis_ok else "degraded", "redis": redis_ok, "objectStorage": storage_ok, "storageMode": storage_mode}


def _decode_inline(value: str, label: str) -> bytes:
    encoded = value.split(",", 1)[1] if value.startswith("data:") and "," in value else value
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid inline {label} payload") from exc
    if not decoded:
        raise HTTPException(status_code=400, detail=f"Inline {label} payload is empty")
    if len(decoded) > MAX_INLINE_BYTES:
        raise HTTPException(status_code=413, detail=f"Inline {label} exceeds the {MAX_INLINE_BYTES // (1024 * 1024)} MB limit")
    return decoded


def _externalize_inline(payload: dict[str, Any], run_id: str, field: str, filename_field: str, uri_field: str) -> None:
    encoded = payload.get(field)
    if not encoded:
        return
    if not s3_client:
        raise HTTPException(status_code=503, detail="Object storage is required for inline video uploads")
    raw = _decode_inline(encoded, field)
    filename = os.path.basename(str(payload.get(filename_field) or f"{field}.bin"))
    key = f"missions/{run_id}/{filename}"
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    try:
        s3_client.put_object(Bucket=OBJECT_STORAGE_BUCKET, Key=key, Body=raw, ContentType=content_type)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Object storage upload failed: {exc}") from exc
    payload[uri_field] = f"s3://{OBJECT_STORAGE_BUCKET}/{key}"
    payload.pop(field, None)


def _clear_oversized_redis_state() -> None:
    """Best-effort recovery for the free Valkey noeviction limit."""
    try:
        redis_client.delete(WORKER_QUEUE_NAME)
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor=cursor, match="job:*")
            if keys:
                redis_client.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        pass

@app.post("/v1/runs")
def submit_run(mission: MissionSubmission) -> dict[str, str]:
    has_input = any(value is not None for key, value in mission.model_dump().items() if key.endswith("_uri") or key.endswith("_base64"))
    if not has_input:
        raise HTTPException(status_code=400, detail="At least one mission input is required")
    run_id = f"DRF-{datetime.now(timezone.utc).strftime('%y%m%d')}-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    payload = mission.model_dump()
    _externalize_inline(payload, run_id, "video_base64", "video_file_name", "video_uri")
    _externalize_inline(payload, run_id, "thermal_video_base64", "thermal_video_file_name", "thermal_video_uri")
    record_input = dict(payload)
    record = {"run_id": run_id, "status": "queued", "created_at": now, "updated_at": now, "progress": 0.0, "current_stage": "queued", "input": record_input, "results": None, "error": None}
    queue_payload = {"run_id": run_id, **payload}
    try:
        redis_client.set(f"job:{run_id}", json.dumps(record), ex=86400)
        redis_client.rpush(WORKER_QUEUE_NAME, json.dumps(queue_payload))
    except redis.exceptions.ResponseError as exc:
        if "maxmemory" not in str(exc).lower():
            raise
        _clear_oversized_redis_state()
        redis_client.set(f"job:{run_id}", json.dumps(record), ex=86400)
        redis_client.rpush(WORKER_QUEUE_NAME, json.dumps(queue_payload))
    return {"run_id": run_id, "status": "queued"}

@app.get("/v1/runs/{run_id}")
def get_run(run_id: str) -> JobStatus:
    raw = redis_client.get(f"job:{run_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Run not found")
    return JobStatus(**json.loads(raw))

@app.get("/v1/runs/{run_id}/events")
async def events(run_id: str):
    async def stream():
        last = None
        while True:
            raw = redis_client.get(f"job:{run_id}")
            if not raw:
                yield "event: error\ndata: run not found\n\n"
                return
            job = json.loads(raw)
            status = job.get("status")
            if status != last:
                yield f"event: status\ndata: {json.dumps(job)}\n\n"
                last = status
            if status in {"completed", "failed"}:
                return
            await asyncio.sleep(1)
    return StreamingResponse(stream(), media_type="text/event-stream")

@app.post("/v1/storage/upload")
def upload_to_storage(file_key: str, file_path: str) -> dict[str, str]:
    if not s3_client:
        raise HTTPException(status_code=503, detail="Object storage is disabled in this deployment")
    s3_client.upload_file(file_path, OBJECT_STORAGE_BUCKET, file_key)
    return {"status": "uploaded", "uri": f"s3://{OBJECT_STORAGE_BUCKET}/{file_key}"}


@app.post("/v1/storage/upload-file")
def upload_file_to_storage(file: UploadFile = File(...)) -> dict[str, str]:
    if not s3_client:
        raise HTTPException(status_code=503, detail="Object storage is disabled in this deployment")
    safe_name = os.path.basename(file.filename or "video.bin")
    key = f"uploads/{uuid.uuid4().hex}/{safe_name}"
    content_type = file.content_type or "application/octet-stream"
    try:
        s3_client.upload_fileobj(file.file, OBJECT_STORAGE_BUCKET, key, ExtraArgs={"ContentType": content_type})
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Object storage upload failed: {exc}") from exc
    return {"status": "uploaded", "uri": f"s3://{OBJECT_STORAGE_BUCKET}/{key}"}

@app.get("/v1/storage/objects/{file_key:path}")
def download_from_storage(file_key: str):
    if not s3_client:
        raise HTTPException(status_code=503, detail="Object storage is disabled in this deployment")
    try:
        obj = s3_client.get_object(Bucket=OBJECT_STORAGE_BUCKET, Key=file_key)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return StreamingResponse(obj["Body"], media_type="application/octet-stream")

from trpc_compat import register
register(app, submit_run, MissionSubmission)
