# DRIFT — Unified Drone Intelligence

A thin, monochrome control surface for routing one drone video through modular thermal SAR, RGB-T fusion, aerial detection, geolocation, and archaeology inference runners.

## What this repository contains

- `client/`: Vercel-ready React dashboard. Upload one video, enable/disable modules, start a run, inspect progress, and review a unified evidence stream.
- `server/`: the current web app API shell. It is intentionally kept separate from model execution.
- `deployment/`: recommended Render service boundaries for GPU/custom-runtime inference.

The repository now includes an execution-first worker at `services/worker/run_pipeline.py`. It performs real `ffprobe` metadata inspection and `ffmpeg` keyframe extraction, then evaluates every listed upstream repository against the supplied inputs. It never invents detector findings: an upstream adapter is marked `FULLY RUNNING` only when its source, runtime, compatible input, and checkpoint are present.

## Recommended production topology

| Layer | Deploy to | Responsibility |
| --- | --- | --- |
| Dashboard | Vercel | React UI, auth callback, result rendering |
| Orchestrator API | Render web service | Accept upload, create run, dispatch jobs, return run status |
| Inference workers | Render background workers or GPU provider | Python/ROS2/ONNX/PyTorch model execution |
| Object storage | S3-compatible storage | Original video, annotated MP4, GeoJSON, CSV, thumbnails |
| Queue | Render Redis or managed Redis | Fan-out/fan-in job coordination |

## Runner adapters

Each repository should be wrapped by one adapter with the same contract:

```text
analyze(input_video, telemetry?, config?) -> normalized_findings.json + artifacts
```

The orchestrator should normalize all outputs into a shared event format:

```json
{
  "runId": "DRF-26-0913",
  "module": "thermal-sar",
  "frame": 428,
  "timestampMs": 14280,
  "label": "person",
  "confidence": 0.94,
  "bbox": [0.27, 0.33, 0.12, 0.18],
  "location": {"lat": 24.7136, "lon": 46.6753, "accuracyM": 0.8},
  "artifacts": []
}
```

This is the integration seam that makes separate open-source projects feel like one product without forcing their dependencies into one process.

## Verified execution matrix

The worker distinguishes a repository's presence from successful execution. The following path is currently verified by `services/worker/test_real_mission.py`:

| Repository | Real execution | Model/runtime | Current result |
| --- | --- | --- | --- |
| Aerial Thermal Detection RT-DETRv2 + YOLOv12 | **Yes** | Kiuyha RT-DETRv2 `best.pt` from Hugging Face + Ultralytics | Thermal MP4 → real detections → normalized DRIFT findings |
| UAV Thermal Person Geolocation | **Partial: Yes with SRT** | Upstream `SRTParser` + `GeoCalculator`; ROS2 Humble + repository-trained YOLOv8x checkpoint still absent | With thermal detections and SRT, real upstream telemetry parsing and pixel-to-GPS projection execute; the ROS2 detector node remains blocked |
| RGB-T Fusion Drone SAR | Blocked | ONNX or PyTorch fusion checkpoint | Demo source is vendored, but no usable trained checkpoint is published in the repository |
| ADAF | Input-gated | ALS/LiDAR/GeoTIFF | Not a regular RGB-video model; activates only with supported geospatial input |
| FoundationModelsArchaeology | Dataset/input-gated | Notebook workflows + satellite/LiDAR data | Not a one-click video inference entrypoint |
| Mustatil | Tool/input-gated | GIS/review/training workspace | Not a frame inference runtime |
| Arran | Dataset/benchmark only | Benchmark assets | No inference runtime |
| Simulated Training Data | Training/input-gated | Raster training/inference scripts | Requires GeoTIFF/training assets, not ordinary video |
| ROS2 Disaster Robot Simulator | Simulator only | ROS2 simulation | No video detector |
| Drone Search & Rescue Ground Station | Ground-station only | Telemetry/MAVLink UI | No video detector |

The RT-DETRv2 model is fetched by `scripts/download_models.sh`; the 64 MB checkpoint is intentionally excluded from git. A fresh worker must run that script before the adapter can be marked `FULLY RUNNING`.

## Repository notes

The thermal person geolocation project requires ROS2 Humble and a model checkpoint plus matching SRT telemetry for the highest-fidelity offline path. The RGB-T fusion project provides a demo path with ONNX Runtime and is a good first production adapter. ADAF is designed for ALS data rather than ordinary RGB video, so its adapter should activate only when an ALS/GeoTIFF input is present or when a separate terrain product is supplied. Mustatil is best treated as a review/training/GIS export workspace rather than as a frame-by-frame video model.

## Local development

```bash
pnpm install
pnpm dev
```

### Worker smoke test

Install `ffmpeg`/`ffprobe`, then run one uploaded video through the worker:

```bash
python3 services/worker/run_pipeline.py ./mission.mp4 ./runs/mission
cat ./runs/mission/run.json
```

Optional inputs are accepted with `--thermal-video`, `--srt`, `--geotiff`, and `--als`. Each adapter result contains `repository`, `model`, `executionStatus`, `reason`, and `ran`, so the dashboard or an API layer can show exactly which repository contributed computation and which dependency prevented execution.

Run the acceptance mission after downloading the checkpoint:

```bash
python3 services/worker/test_real_mission.py
```

The dashboard's **Run real pipeline** action calls `mission.run`, passes the uploaded media to the Python worker, and renders the worker's actual repository/model/status/output contribution records. Thermal mode deliberately reuses the selected file as the thermal stream only when the operator explicitly enables **Mark as thermal**; it does not silently convert RGB footage into thermal data.

## Vercel

Deploy the frontend with the Vite build output. Set the API base URL to the Render orchestrator service in the production environment.

## Render

Use a separate Python service for the orchestrator and workers. Do not run ROS2, large PyTorch models, or long video jobs inside the Vercel request lifecycle. Store all model weights outside git and load them from persistent object storage or an attached volume.

## License note

The upstream repositories have different licenses and model-weight terms. Keep each adapter's license and attribution with its runner, and review whether a combined hosted service is compatible with the relevant licenses before public deployment.
