#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/vendor"
mkdir -p "$DEST"
clone_or_update() {
  local dir="$1"
  local url="$2"
  if [ -d "$DEST/$dir/.git" ]; then
    git -C "$DEST/$dir" fetch --depth=1 origin
    git -C "$DEST/$dir" reset --hard FETCH_HEAD
  else
    git clone --depth=1 "$url" "$DEST/$dir"
  fi
}
clone_or_update mustatil "https://github.com/tarekwasfy01/Mustatil-YOLO-AI-Model-Trainer-.git"
clone_or_update foundation-models-archaeology "https://github.com/juergenlandauer/FoundationModelsArchaeology.git"
clone_or_update adaf "https://github.com/EarthObservation/adaf.git"
clone_or_update arran "https://github.com/ickramer/Arran.git"
clone_or_update simulated-training-data "https://github.com/NMC-CRS/simulated-training-data-for-archaeological-site-detection.git"
clone_or_update uav-thermal-person-geolocation "https://github.com/Gruzver/uav-thermal-person-geolocation.git"
clone_or_update drone-tracker "https://github.com/Gruzver/drone-tracker.git"
clone_or_update aerial-thermal-detection "https://github.com/kiuyha/Aerial-Thermal-Detection-RT-DETRv2-and-YOLOv12.git"
clone_or_update rgbt-fusion-drone-sar "https://github.com/hiungn/RGBT-Fusion-Drone-SAR.git"
clone_or_update ros2-disaster-robot-sim "https://github.com/newton-adhikari/ros2-disaster-robot-sim.git"
clone_or_update drone-control-monitoring-system "https://github.com/thuyminh2112/Drone-control-monitoring-system.git"
if [ -d "$DEST/aerial-thermal-sar-detection-demo/.git" ]; then
  git -C "$DEST/aerial-thermal-sar-detection-demo" fetch --depth=1 origin
  git -C "$DEST/aerial-thermal-sar-detection-demo" reset --hard FETCH_HEAD
else
  git clone --depth=1 "https://huggingface.co/spaces/Kiuyha/Aerial-Thermal-SAR-Detection-Demo" "$DEST/aerial-thermal-sar-detection-demo"
fi
# Keep upstream source code while excluding oversized demo-only media from deployments.
rm -f \
  "$DEST/drone-tracker/docs/video_test_14.gif" \
  "$DEST/foundation-models-archaeology/Experiment_5_potsherds/out.mp4" \
  "$DEST/rgbt-fusion-drone-sar/docs/demo.gif" \
  "$DEST/simulated-training-data/docs/Figure_6.png"
printf '\nCloned upstream sources:\n'
find "$DEST" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort
