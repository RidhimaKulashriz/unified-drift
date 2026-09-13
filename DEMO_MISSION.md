# DRIFT demo mission

This repository now includes a reproducible synthetic mission pack for testing the all-12 execution contract without requiring field footage.

## Run it locally

```bash
python3 scripts/generate_demo_mission.py
python3 scripts/run_demo_mission.py
```

The harness always evaluates all twelve topics and writes the detailed execution report to `demo-mission/run-output/all12_execution.json`. The generated files are synthetic fixtures; they are not real archaeological, person-detection, or telemetry evidence.

## What this proves

The demo proves that the executor can accept a mission pack, dispatch all twelve topic handlers, and return one status record per topic. A `COMPLETED` record means that the upstream adapter produced its expected artifact. `INPUT_REQUIRED`, `DEPENDENCY_REQUIRED`, `RUNTIME_REQUIRED`, or `FAILED` records identify what must be supplied or installed before that topic can run.

## What it does not prove

Synthetic RGB and grayscale video cannot prove thermal model accuracy. A placeholder JSON file cannot replace a real GeoTIFF/ALS/LiDAR dataset, and a local machine without ROS2 cannot execute the robot simulator. Full production acceptance still requires the worker Docker image, upstream checkouts, model checkpoints, and the correct input mode for each topic.
