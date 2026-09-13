from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from trpc_compat import register


class Mission(BaseModel):
    video_base64: str | None = None
    video_file_name: str | None = None
    thermal_video_base64: str | None = None
    thermal_video_file_name: str | None = None
    enabled_modules: list[str] = []


def test_single_and_batch_envelopes():
    app = FastAPI()
    seen = []

    def submit(mission):
        seen.append(mission)
        return {"run_id": f"run-{len(seen)}", "status": "queued"}

    register(app, submit, Mission)
    client = TestClient(app)
    call = {"json": {"videoBase64": "data", "fileName": "test.mp4", "enabledModules": ["arran"]}}

    single = client.post("/api/trpc/mission.run", json=call)
    assert single.status_code == 200
    assert single.json()["result"]["data"]["json"]["runId"] == "run-1"

    batch = client.post("/api/trpc/mission.run?batch=1", json=[call])
    assert batch.status_code == 200
    assert batch.json()[0]["result"]["data"]["json"]["runId"] == "run-2"
    assert seen[-1].enabled_modules == ["arran"]


def test_invalid_batch_item_is_reported_without_crashing():
    app = FastAPI()
    register(app, lambda mission: {"run_id": "unused", "status": "queued"}, Mission)
    response = TestClient(app).post(
        "/api/trpc/mission.run?batch=1",
        json=[{"json": {"fileName": "missing-video.mp4"}}],
    )
    assert response.status_code == 200
    assert response.json()[0]["error"]["json"]["message"] == "videoUri or videoBase64 and fileName are required"
