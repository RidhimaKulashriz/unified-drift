from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


def _unwrap_input(raw: Any) -> dict[str, Any]:
    """Extract the procedure input from tRPC single-call or batch envelopes."""
    if not isinstance(raw, dict):
        raise ValueError("Invalid tRPC request envelope")
    data = raw.get("json", raw)
    if not isinstance(data, dict):
        raise ValueError("Invalid tRPC input")
    return data


def _success(queued: dict[str, str]) -> dict[str, Any]:
    result = {
        "runId": queued["run_id"],
        "status": queued["status"],
        "findings": [],
        "adapters": [],
        "fusion": {"outputFindingCount": 0},
    }
    return {"result": {"data": {"json": result}}}


def _error(message: str, *, code: int = -32603, http_status: int = 500) -> dict[str, Any]:
    """Match the tRPC + superjson error envelope expected by the web client."""
    return {
        "error": {
            "json": {
                "message": message,
                "code": code,
                "data": {
                    "code": "INTERNAL_SERVER_ERROR" if http_status >= 500 else "BAD_REQUEST",
                    "httpStatus": http_status,
                    "path": "mission.run",
                },
            }
        }
    }


def register(app, submit_run: Callable[[Any], dict[str, str]], mission_model):
    @app.post("/api/trpc/{procedure}")
    async def trpc_compat(request: Request, procedure: str):
        if procedure != "mission.run":
            return JSONResponse(status_code=404, content=_error("Unknown procedure"))

        try:
            body = await request.json()
            is_batch = isinstance(body, list)
            calls = body if is_batch else [body]
            if not calls:
                return JSONResponse(status_code=400, content=_error("At least one tRPC call is required", code=-32600, http_status=400))

            responses: list[dict[str, Any]] = []
            for call in calls:
                data = _unwrap_input(call)
                video_b64 = data.get("videoBase64")
                video_uri = data.get("videoUri")
                file_name = data.get("fileName")
                thermal_b64 = data.get("thermalVideoBase64")
                thermal_uri = data.get("thermalVideoUri")
                if (not isinstance(video_b64, str) and not isinstance(video_uri, str)) or not isinstance(file_name, str):
                    responses.append(_error("videoUri or videoBase64 and fileName are required", code=-32600, http_status=400))
                    continue

                mission = mission_model(
                    video_base64=video_b64,
                    video_file_name=file_name,
                    video_uri=video_uri,
                    thermal_video_base64=thermal_b64,
                    thermal_video_file_name=file_name if thermal_b64 else None,
                    thermal_video_uri=thermal_uri,
                    enabled_modules=data.get("enabledModules") or [],
                )
                queued = submit_run(mission)
                responses.append(_success(queued))

            if is_batch:
                return JSONResponse(content=responses)
            return JSONResponse(content=responses[0])
        except Exception as exc:
            return JSONResponse(status_code=500, content=_error(str(exc)))

    return trpc_compat


__all__ = ["register"]
