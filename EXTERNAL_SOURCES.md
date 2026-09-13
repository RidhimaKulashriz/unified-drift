# DRIFT external sources and compatibility matrix

This catalog records the external datasets, checkpoints, repositories, and runtimes supplied for the twelve DRIFT pipelines. Links are references; a source is marked usable only after it is downloaded, licensed for the intended use, and passed to the matching adapter.

| Pipeline | Required input | Supplied sources | Current execution rule |
|---|---|---|---|
| GIS AI workspace | RGB image or GeoTIFF | Mustatil releases; Archaeoscape | Runs only when the upstream package and compatible image/GeoTIFF are present. |
| Zero-shot archaeology | Satellite/LiDAR input and notebook runtime | Foundation Models Archaeology; Archaeoscape | Executes the selected upstream notebook; no video is substituted. |
| Archaeological features | ALS/LiDAR GeoTIFF | ADAF; Archaeoscape | Requires a real GeoTIFF and Jupyter/GeoPandas stack. |
| Archaeology benchmark | Arran dataset/predictions | Arran repository and Drive dataset | Performs benchmark input audit/scoring; it is not a video detector. |
| Synthetic training data | DEM and stream vectors | USGS National Map Downloader; generator repository | Runs the upstream generator with DEM/vector inputs. |
| Thermal GPS geolocation | Thermal video and matching DJI SRT | DJI Mavic 3 Thermal dataset | Runs SRT parsing and geolocation projection only with paired telemetry. |
| Drone object tracking | RGB video and checkpoint | Drone Tracker releases/repository | Runs the real tracker when its checkpoint is present. |
| Thermal aerial detection | Thermal frame/video and checkpoint | Thermal YOLOv12; HIT-UAV; Aerial Thermal repository | Runs the thermal detector; RGB footage is not treated as thermal. |
| Thermal SAR comparison | Thermal frame and two checkpoints | SAR demo; Thermal YOLOv12 | Runs the dual-model comparison when weights and compatible thermal input exist. |
| RGB-T fusion | Synchronized RGB and thermal pair plus ONNX model | Caltech RGB-T; DRTV30K; RGB-T ONNX; RGB-T Fusion repository | Requires synchronized paired inputs; one RGB video alone is insufficient. |
| Disaster robot simulation | ROS2 Humble and Gazebo | ROS2 Humble docs; gz_ros2_control; robot repository | Runs only on a worker with ROS2/Gazebo installed. |
| Drone ground station | MAVLink `.tlog` | DroneKit public `flight.tlog`; ground-station repository | Runs telemetry parsing/visualization; it is not an image detector. |

## Test policy

The executor reports `COMPLETED` only when the matching upstream path executes and produces its expected artifact. It reports `INPUT_REQUIRED`, `DEPENDENCY_REQUIRED`, `RUNTIME_REQUIRED`, or `FAILED` when the required source or runtime is unavailable. Synthetic demo outputs remain explicitly labeled `SIMULATED` and are never merged into real findings.

The complete machine-readable catalog is available at [`/source-catalog.json`](./client/public/source-catalog.json).
