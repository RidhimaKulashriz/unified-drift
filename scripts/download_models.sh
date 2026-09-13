#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$ROOT/models"
python3 -m pip install --user 'ultralytics>=8.3.167'
curl -L --fail --retry 2 -o "$ROOT/models/aerial-thermal-rtdetrv2-best.pt" \
  'https://huggingface.co/Kiuyha/rtdetrv2-human-detection-thermal-uav/resolve/main/best.pt'
printf 'Installed upstream RT-DETRv2 checkpoint at %s\n' "$ROOT/models/aerial-thermal-rtdetrv2-best.pt"
