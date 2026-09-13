FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/services/worker

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
    curl -L --fail --retry 3 -o /app/models/aerial-thermal-rtdetrv2-best.pt https://huggingface.co/Kiuyha/rtdetrv2-human-detection-thermal-uav/resolve/main/best.pt

CMD ["python", "gpu_worker.py"]
