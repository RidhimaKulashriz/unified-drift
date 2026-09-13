# DRIFT Inference Worker (Render)

This worker consumes run jobs from Redis and writes normalized findings plus artifacts back to object storage. The actual Python image should install the dependencies for the enabled adapter only, rather than importing every upstream project into one process.

Recommended order of implementation:

1. RGB-T fusion with ONNX Runtime.
2. Thermal person detection and geolocation with recorded video plus SRT telemetry.
3. YOLOv12 / RT-DETRv2 aerial thermal detection.
4. ALS-aware archaeology analysis through ADAF and foundation-model adapters.

Model weights are intentionally not committed to git. Mount or download them from object storage at worker startup.
