from __future__ import annotations
import hashlib
from pathlib import Path

EXPECTED = {
    "/var/lib/drift/tdm-cache/files/dronekit-flight-tlog/flight.tlog": "16c79fedb900a61e9f67bca6133dd49a40a66f6b431e75138c8d9023c9a31523",
    "/var/lib/drift/tdm-cache/files/rgbt-onnx/fusion_progressive_finetune.onnx": "bf3ac91da61aca89e7a83b2cc2838dddbdc80edbc6e3b93e1402029bec13fd90",
}
for raw, expected in EXPECTED.items():
    path = Path(raw)
    if not path.exists() or path.stat().st_size == 0:
        raise SystemExit(f"missing TDM asset: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected:
        raise SystemExit(f"sha256 mismatch for {path}: {digest}")

import onnxruntime as ort
session = ort.InferenceSession("/var/lib/drift/tdm-cache/files/rgbt-onnx/fusion_progressive_finetune.onnx", providers=["CPUExecutionProvider"])
if not session.get_inputs():
    raise SystemExit("RGB-T ONNX model has no inputs")

from ultralytics import YOLO
for path in ("/app/models/aerial-thermal-rtdetrv2-best.pt", "/app/models/aerial-thermal-yolov12-best.pt"):
    model = YOLO(path)
    if model is None:
        raise SystemExit(f"checkpoint did not load: {path}")
print("TDM assets verified: tlog sha256, RGB-T ONNX load, thermal checkpoints load")
