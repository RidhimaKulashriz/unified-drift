# DRIFT Orchestrator (Render)

This service is the production boundary between the Vercel dashboard and the model runners. It should expose:

- `GET /health`
- `POST /v1/runs` — accept an object-storage key plus enabled module IDs
- `GET /v1/runs/:runId` — return normalized progress and findings
- `GET /v1/runs/:runId/events` — stream normalized findings over SSE or pollable JSON

Keep this service stateless. Store uploaded video and outputs in object storage, and put run jobs on Redis. Do not run inference inline in the HTTP request.

The worker should dispatch these adapters behind a stable interface:

```python
class RunnerAdapter(Protocol):
    module_id: str

    def analyze(self, video_uri: str, telemetry_uri: str | None) -> list[dict]:
        ...
```

Start with `RGBT-Fusion-Drone-SAR` because its demo path has an ONNX Runtime option. Add the ROS2 thermal geolocation adapter separately because it requires ROS2 Humble and telemetry/model assets. Activate ADAF only when ALS/GeoTIFF input is available; ordinary RGB video is not a substitute for ALS data.

The Render service should return the normalized event shape documented in the repository root README. Keep all upstream license notices and model-weight terms with each adapter.
