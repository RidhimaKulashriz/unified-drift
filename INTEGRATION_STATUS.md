# DRIFT integration status

All repositories from the supplied list are now vendored under `vendor/` using shallow clones. The authoritative mapping is `services/worker/adapter-manifest.json`.

## What can run from one uploaded video

The compatible analysis path is:

1. RGB-T Fusion Drone SAR when both RGB and thermal streams are available, after downloading its ONNX model.
2. UAV Thermal Person Geolocation when the clip is thermal and an SRT telemetry file plus YOLOv8x checkpoint are supplied.
3. Aerial Thermal Detection when its model weights and runnable entrypoint are configured.
4. The Hugging Face SAR demo through a dedicated adapter.

## What cannot honestly run from ordinary RGB video alone

ADAF and the archaeology foundation-model repositories require ALS/LiDAR/GeoTIFF or satellite imagery. Arran and simulated-training-data are benchmark/training assets. The ROS2 disaster simulator and the drone ground station are simulation/telemetry systems, not video inference models. They are included in the repository but should be conditionally activated only when their required input exists.

## Next implementation action

Deploy `services/orchestrator` and `services/worker` separately on Render. The worker should read the adapter manifest, accept `video`, optional `thermalVideo`, optional `srt`, and optional `als/geotiff` objects, then dispatch only compatible adapters and normalize outputs into DRIFT findings. Vercel should host the dashboard and call the Render orchestrator URL.
