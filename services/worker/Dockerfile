FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/services/worker \
    TDM_CACHE_DIR=/var/lib/drift/tdm-cache

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git curl ca-certificates build-essential libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/services/worker
COPY requirements-gpu.txt ./requirements-gpu.txt
RUN pip install --upgrade pip && pip install -r requirements-gpu.txt \
    jupyter nbconvert rasterio geopandas shapely pyproj

COPY . .
RUN mkdir -p /app/vendor /app/models && \
    git clone --depth=1 https://github.com/tarekwasfy01/Mustatil-YOLO-AI-Model-Trainer-.git /app/vendor/mustatil && \
    git clone --depth=1 https://github.com/juergenlandauer/FoundationModelsArchaeology.git /app/vendor/foundation-models-archaeology && \
    git clone --depth=1 https://github.com/EarthObservation/adaf.git /app/vendor/adaf && \
    git clone --depth=1 https://github.com/ickramer/Arran.git /app/vendor/arran && \
    git clone --depth=1 https://github.com/NMC-CRS/simulated-training-data-for-archaeological-site-detection.git /app/vendor/simulated-training-data && \
    git clone --depth=1 https://github.com/Gruzver/uav-thermal-person-geolocation.git /app/vendor/uav-thermal-person-geolocation && \
    git clone --depth=1 https://github.com/Gruzver/drone-tracker.git /app/vendor/drone-tracker && \
    git clone --depth=1 https://github.com/kiuyha/Aerial-Thermal-Detection-RT-DETRv2-and-YOLOv12.git /app/vendor/aerial-thermal-detection && \
    git clone --depth=1 https://huggingface.co/spaces/Kiuyha/Aerial-Thermal-SAR-Detection-Demo /app/vendor/aerial-thermal-sar-detection-demo && \
    git clone --depth=1 https://github.com/hiungn/RGBT-Fusion-Drone-SAR.git /app/vendor/rgbt-fusion-drone-sar && \
    git clone --depth=1 https://github.com/newton-adhikari/ros2-disaster-robot-sim.git /app/vendor/ros2-disaster-robot-sim && \
    git clone --depth=1 https://github.com/thuyminh2112/Drone-control-monitoring-system.git /app/vendor/drone-control-monitoring-system && \
    curl -L --fail --retry 3 -o /app/models/aerial-thermal-rtdetrv2-best.pt https://huggingface.co/Kiuyha/rtdetrv2-human-detection-thermal-uav/resolve/main/best.pt && \
    curl -L --fail --retry 3 -o /app/models/aerial-thermal-yolov12-best.pt https://huggingface.co/Kiuyha/yolov12-human-detection-thermal-uav/resolve/main/best.pt && \
    curl -L --fail --retry 3 -o /app/models/fusion_progressive_finetune.onnx https://huggingface.co/hiuS04/RGBT-Fusion-Drone-SAR/resolve/main/fusion_progressive_finetune.onnx && \
    mkdir -p /var/lib/drift/tdm-cache/files/dronekit-flight-tlog /var/lib/drift/tdm-cache/files/rgbt-onnx && \
    curl -L --fail --retry 3 -o /var/lib/drift/tdm-cache/files/dronekit-flight-tlog/flight.tlog https://raw.githubusercontent.com/dronekit/dronekit-la-testdata/master/flight.tlog && \
    echo '16c79fedb900a61e9f67bca6133dd49a40a66f6b431e75138c8d9023c9a31523  /var/lib/drift/tdm-cache/files/dronekit-flight-tlog/flight.tlog' | sha256sum -c - && \
    curl -L --fail --retry 3 -o /var/lib/drift/tdm-cache/files/rgbt-onnx/fusion_progressive_finetune.onnx https://huggingface.co/hiuS04/RGBT-Fusion-Drone-SAR/resolve/main/fusion_progressive_finetune.onnx && \
    echo 'bf3ac91da61aca89e7a83b2cc2838dddbdc80edbc6e3b93e1402029bec13fd90  /var/lib/drift/tdm-cache/files/rgbt-onnx/fusion_progressive_finetune.onnx' | sha256sum -c - && \
    cp /var/lib/drift/tdm-cache/files/rgbt-onnx/fusion_progressive_finetune.onnx /app/models/fusion_progressive_finetune.onnx && \
    python verify_tdm_assets.py

CMD ["python", "gpu_worker.py"]
