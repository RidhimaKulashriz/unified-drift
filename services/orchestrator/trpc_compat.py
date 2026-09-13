from __future__ import annotations

import json
from typing import Any, Callable

from fastapi import Request
from fastapi.responses import JSONResponse


def register(app, submit_run: Callable[[Any], dict[str, str]], mission_model):
    @app.post("/api/trpc/{procedure}")
    async def trpc_compat(request: Request, procedure: str):
        if procedure != "mission.run":
            return JSONResponse(status_code=404, content={"error": {"message": "Unknown procedure"}})
        try:
            body = await request.json()
            raw = body.get("0", body)
            data = raw.get("json", raw) if isinstance(raw, dict) else {}
            video_b64 = data.get("videoBase64")
            file_name = data.get("fileName")
            thermal_b64 = data.get("thermalVideoBase64")
            if not isinstance(video_b64, str) or not isinstance(file_name, str):
                return JSONResponse(status_code=400, content={"error": {"message": "videoBase64 and fileName are required"}})
            mission = mission_model(
                video_base64=video_b64,
                video_file_name=file_name,
                thermal_video_base64=thermal_b64,
                thermal_video_file_name=file_name if thermal_b64 else None,
            )
            queued = submit_run(mission)
            result = {
                "runId": queued["run_id"],
                "status": queued["status"],
                "findings": [],
                "adapters": [],
                "fusion": {"outputFindingCount": 0},
            }
            return JSONResponse(content={"result": {"data": {"json": result}}})
        except Exception as exc:
            return JSONResponse(status_code=500, content={"error": {"message": str(exc)}})
