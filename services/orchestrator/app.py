#!/usr/bin/env python3
"""DRIFT orchestrator API.

Lightweight API only: accepts a mission manifest, queues it in Redis, and lets
the remote worker perform all heavy repository execution.
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
import redis
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
OBJECT_STORAGE_ENDPOINT = os.environ.get("OBJECT_STORAGE_ENDPOINT")
OBJECT_STORAGE_ACCESS_KEY = os.environ.get("OBJECT_STORAGE_ACCESS_KEY")
OBJECT_STORAGE_SECRET_KEY = os.environ.get("OBJECT_STORAGE_SECRET_KEY")
OBJECT_STORAGE_BUCKET = os.environ.get("OBJECT_STORAGE_BUCKET", "drift-storage")
WORKER_QUEUE_NAME = os.environ.get("WORKER_QUEUE_NAME", "drift-inference")

app = FastAPI(title="DRIFT Orchestrator", version="1.0")
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
    storage_ok = False
    if s3_client:
        try:
            s3_client.head_bucket(Bucket=OBJECT_STORAGE_BUCKET)
            storage_ok = True
        except Exception:
            storage_ok = False
    return {"status": "healthy" if redis_ok else "degraded", "redis": redis_ok, "objectStorage": storage_ok}


@app.post("/v1/runs")
def submit_run(mission: MissionSubmission) -> dict[str, str]:
    if not any(value is not None for value in mission.model_dump(exclude={"enabled_modules", "samples", "experiment"}).values()):
        raise HTTPException(status_code=400, detail="At least one mission input is required")
    run_id = f"DRF-{datetime.now(timezone.utc).strftime('%y%m%d')}-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    record = {"run_id": run_id, "status": "queued", "created_at": now, "updated_at": now, "progress": 0.0, "current_stage": "queued", "input": mission.model_dump(), "results": None, "error": None}
    redis_client.set(f"job:{run_id}", json.dumps(record))
    message = {"run_id": run_id, **mission.model_dump()}
    redis_client.rpush(WORKER_QUEUE_NAME, json.dumps(message))
    return {"run_id": run_id, "status": "queued"}


@app.get("/v1/runs/{run_id}")
def get_run(run_id: str) -> JobStatus:
    raw = redis_client.get(f"job:{run_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Run not found")
    job = json.loads(raw)
    return JobStatus(**job)


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
        raise HTTPException(status_code=503, detail="Object storage is not configured")
    s3_client.upload_file(file_path, OBJECT_STORAGE_BUCKET, file_key)
    return {"status": "uploaded", "uri": f"s3://{OBJECT_STORAGE_BUCKET}/{file_key}"}


@app.get("/v1/storage/objects/{file_key:path}")
def download_from_storage(file_key: str):
    if not s3_client:
        raise HTTPException(status_code=503, detail="Object storage is not configured")
    try:
        obj = s3_client.get_object(Bucket=OBJECT_STORAGE_BUCKET, Key=file_key)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return StreamingResponse(obj["Body"], media_type="application/octet-stream")


@app.options("/{path:path}")
def cors_preflight(path: str):
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
