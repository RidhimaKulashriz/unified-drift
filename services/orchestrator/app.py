#!/usr/bin/env python3
"""DRIFT Orchestrator - API service for job submission and progress tracking.

This service runs locally or on Render and handles:
- Job submission to remote GPU workers
- Progress tracking and result retrieval
- Object storage integration for large files
- Queue management via Redis
"""
from __future__ import annotations

import os
import json
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Any
from pathlib import Path

import redis
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import boto3

# Configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
OBJECT_STORAGE_ENDPOINT = os.environ.get("OBJECT_STORAGE_ENDPOINT")
OBJECT_STORAGE_ACCESS_KEY = os.environ.get("OBJECT_STORAGE_ACCESS_KEY")
OBJECT_STORAGE_SECRET_KEY = os.environ.get("OBJECT_STORAGE_SECRET_KEY")
OBJECT_STORAGE_BUCKET = os.environ.get("OBJECT_STORAGE_BUCKET", "drift-storage")
WORKER_QUEUE_NAME = os.environ.get("WORKER_QUEUE_NAME", "drift-inference")

app = FastAPI(title="DRIFT Orchestrator")

# Redis client for job queue
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# S3 client for object storage
s3_client = None
if OBJECT_STORAGE_ENDPOINT:
    s3_client = boto3.client(
        's3',
        endpoint_url=OBJECT_STORAGE_ENDPOINT,
        aws_access_key_id=OBJECT_STORAGE_ACCESS_KEY,
        aws_secret_access_key=OBJECT_STORAGE_SECRET_KEY
    )


class JobSubmission(BaseModel):
    """Job submission model."""
    video_uri: str
    thermal_video_uri: str | None = None
    srt_uri: str | None = None
    geotiff_uri: str | None = None
    als_uri: str | None = None
    enabled_modules: list[str] = []


class JobStatus(BaseModel):
    """Job status model."""
    run_id: str
    status: str  # queued, running, completed, failed
    created_at: str
    updated_at: str
    progress: float
    current_stage: str
    results: dict[str, Any] | None = None
    error: str | None = None


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/v1/runs")
def submit_job(job: JobSubmission, background_tasks: BackgroundTasks) -> dict[str, str]:
    """Submit a new inference job to the GPU worker queue."""
    run_id = f"DRF-{datetime.now(timezone.utc).strftime('%y%m%d')}-{uuid.uuid4().hex[:8]}"
    
    # Create job record
    job_record = {
        "run_id": run_id,
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "progress": 0.0,
        "current_stage": "queued",
        "input": job.dict(),
        "results": None,
        "error": None
    }
    
    # Store job in Redis
    redis_client.set(f"job:{run_id}", json.dumps(job_record))
    redis_client.set(f"job_status:{run_id}", "queued")
    
    # Queue job for worker
    queue_message = {
        "run_id": run_id,
        "video_uri": job.video_uri,
        "thermal_video_uri": job.thermal_video_uri,
        "srt_uri": job.srt_uri,
        "geotiff_uri": job.geotiff_uri,
        "als_uri": job.als_uri,
        "enabled_modules": job.enabled_modules
    }
    redis_client.rpush(WORKER_QUEUE_NAME, json.dumps(queue_message))
    
    return {"run_id": run_id, "status": "queued"}


@app.get("/v1/runs/{run_id}")
def get_job_status(run_id: str) -> JobStatus:
    """Get job status and results."""
    job_data = redis_client.get(f"job:{run_id}")
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = json.loads(job_data)
    return JobStatus(
        run_id=job["run_id"],
        status=job["status"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        progress=job["progress"],
        current_stage=job["current_stage"],
        results=job.get("results"),
        error=job.get("error")
    )


@app.get("/v1/runs/{run_id}/events")
async def stream_job_events(run_id: str):
    """Stream job events as Server-Sent Events."""
    async def event_stream():
        last_status = None
        while True:
            job_data = redis_client.get(f"job:{run_id}")
            if not job_data:
                yield f"event: error\ndata: Job not found\n\n"
                break
            
            job = json.loads(job_data)
            current_status = job["status"]
            
            if current_status != last_status:
                event_data = {
                    "status": current_status,
                    "progress": job["progress"],
                    "current_stage": job["current_stage"],
                    "timestamp": job["updated_at"]
                }
                if job.get("error"):
                    event_data["error"] = job["error"]
                if job.get("results"):
                    event_data["results"] = job["results"]
                
                yield f"event: status\ndata: {json.dumps(event_data)}\n\n"
                last_status = current_status
            
            if current_status in ["completed", "failed"]:
                break
            
            await asyncio.sleep(1)
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/v1/storage/upload")
def upload_to_storage(file_key: str, file_path: str) -> dict[str, str]:
    """Upload a file to object storage."""
    if not s3_client:
        raise HTTPException(status_code=500, detail="Object storage not configured")
    
    try:
        s3_client.upload_file(file_path, OBJECT_STORAGE_BUCKET, file_key)
        return {"status": "uploaded", "uri": f"s3://{OBJECT_STORAGE_BUCKET}/{file_key}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/v1/storage/download/{file_key}")
def download_from_storage(file_key: str):
    """Download a file from object storage."""
    if not s3_client:
        raise HTTPException(status_code=500, detail="Object storage not configured")
    
    try:
        response = s3_client.get_object(Bucket=OBJECT_STORAGE_BUCKET, Key=file_key)
        return StreamingResponse(
            response["Body"],
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={file_key}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)