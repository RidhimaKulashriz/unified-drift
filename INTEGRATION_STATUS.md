# DRIFT integration status

All 12 repositories from the supplied list are now vendored under `vendor/` using shallow clones. The authoritative mapping is `services/worker/adapter-manifest.json`.

## FULLY RUNNING Repositories (Real Execution Verified)

### 1. Aerial Thermal Detection RT-DETRv2 ✅
- **Status**: FULLY RUNNING
- **Input**: Thermal video/images
- **Adapter**: `services/worker/aerial_thermal_adapter.py`
- **Model**: RT-DETRv2 best.pt from Hugging Face
- **Real Output**: Actual detections with confidence scores and bounding boxes
- **Provenance**: Repository and model URLs tracked in output

### 2. Aerial Thermal SAR Detection Demo ✅
- **Status**: FULLY RUNNING
- **Input**: Thermal images
- **Adapter**: `services/worker/aerial_thermal_sar_demo_adapter.py`
- **Model**: YOLOv12 + RT-DETRv2 from Hugging Face
- **Real Output**: Dual model inference with annotated output images
- **Provenance**: Downloads models during execution, generates real detections

### 3. UAV Thermal Person Geolocation ✅
- **Status**: FULLY RUNNING
- **Input**: Thermal video + SRT telemetry
- **Adapter**: Integrated in `services/worker/run_pipeline.py`
- **Model**: GeoCalculator + SRTParser (upstream source)
- **Real Output**: GPS coordinates with location accuracy for each detection
- **Provenance**: Uses upstream SRT parser and pixel-to-GPS projection

## ADAPTER READY Repositories (Implementation Complete)

### 4. RGB-T Fusion Drone SAR ⚠️
- **Status**: ADAPTER READY
- **Input**: RGB + thermal video pair
- **Adapter**: `services/worker/rgbt_fusion_adapter.py`
- **Model**: RGB-T Fusion ONNX model from Hugging Face
- **Requirement**: Needs model download (fusion_progressive_finetune.onnx)
- **Implementation**: ONNX inference implementation complete

### 5. Drone Tracker ⚠️
- **Status**: ADAPTER READY
- **Input**: Video
- **Adapter**: `services/worker/drone_tracker_adapter.py`
- **Model**: YOLOv8 phase2_finetuned model
- **Requirement**: Needs trained model checkpoint
- **Implementation**: Tracking implementation with track ID management

### 6. ADAF ⚠️
- **Status**: ADAPTER READY
- **Input**: ALS/LiDAR/GeoTIFF data
- **Adapter**: `services/worker/adaf_adapter.py`
- **Model**: ADAF inference engine
- **Implementation**: Interface to ADAF's geospatial detection pipeline

### 7. Foundation Models Archaeology ⚠️
- **Status**: ADAPTER READY
- **Input**: Satellite/LiDAR/GeoTIFF
- **Adapter**: `services/worker/foundation_models_archaeology_adapter.py`
- **Model**: GPT/Gemini/SAM foundation models
- **Implementation**: Experiment listing and execution interface

### 8. Mustatil ⚠️
- **Status**: ADAPTER READY
- **Input**: Images/GeoTIFF/Satellite
- **Adapter**: `services/worker/mustatil_adapter.py`
- **Model**: Multi-model GIS toolkit
- **Implementation**: Workspace initialization with full capabilities

## DATASET/TOOL ONLY Repositories (Not Video Inference)

### 9. Arran ❌
- **Status**: DATASET ONLY
- **Purpose**: Benchmark dataset and evaluation metrics
- **Not**: Inference runtime

### 10. Simulated Training Data ❌
- **Status**: TRAINING ONLY
- **Purpose**: Procedural training data generation
- **Not**: Inference runtime

### 11. ROS2 Disaster Robot Simulator ❌
- **Status**: SIMULATOR ONLY
- **Purpose**: Robot navigation simulation
- **Not**: Video detector

### 12. Drone Control Monitoring System ❌
- **Status**: GROUND STATION ONLY
- **Purpose**: Telemetry display and control interface
- **Not**: Video detector

## Execution Modes

The DRIFT system now supports multiple execution modes based on input availability:

1. **Thermal Detection Mode**: Runs thermal detectors when thermal video is provided
2. **RGB Detection Mode**: Runs RGB detection and tracking when regular video is provided
3. **Fusion Mode**: Runs RGB-thermal fusion when both streams are available
4. **Geolocation Mode**: Projects detections to GPS when SRT telemetry is available
5. **Archaeology Mode**: Runs archaeology detection when GeoTIFF/ALS data is provided
6. **Workspace Mode**: Initializes specialized workspaces for annotation and training

## Summary

**8 out of 12 repositories are now fully functional or adapter-ready inside DRIFT:**

- ✅ **3 FULLY RUNNING**: Aerial Thermal Detection, Aerial Thermal SAR Demo, UAV Thermal Person Geolocation
- ⚠️ **5 ADAPTER READY**: RGB-T Fusion, Drone Tracker, ADAF, Foundation Models Archaeology, Mustatil
- ❌ **4 DATASET/TOOL ONLY**: Arran, Simulated Training Data, ROS2 Disaster Robot Simulator, Drone Control Monitoring System

The system now executes **real upstream code** with **provenance tracking** for each repository, providing actual detection results rather than mock outputs. Each adapter maintains repository attribution and model provenance in its output.

## Next Implementation Action

Deploy `services/orchestrator` and `services/worker` separately on Render. The worker should read the adapter manifest, accept `video`, optional `thermalVideo`, optional `srt`, and optional `als/geotiff` objects, then dispatch only compatible adapters and normalize outputs into DRIFT findings. Vercel should host the dashboard and call the Render orchestrator URL.
