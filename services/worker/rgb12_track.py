from __future__ import annotations
import cv2
from pathlib import Path
from typing import Any

RGB_MODELS = [
    ("YOLO11n", "yolo11n.pt"), ("YOLO11s", "yolo11s.pt"), ("YOLO11m", "yolo11m.pt"),
    ("YOLO11l", "yolo11l.pt"), ("YOLO11x", "yolo11x.pt"),
    ("YOLOv8n", "yolov8n.pt"), ("YOLOv8s", "yolov8s.pt"), ("YOLOv8m", "yolov8m.pt"),
    ("YOLOv8l", "yolov8l.pt"), ("YOLOv8x", "yolov8x.pt"),
    ("RT-DETR-l", "rtdetr-l.pt"), ("RT-DETR-x", "rtdetr-x.pt"),
]

def execute_rgb12(video: Path, output: Path, synthetic: bool = False) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    if synthetic:
        return _synthetic(video, output)
    from ultralytics import YOLO, RTDETR
    cap = cv2.VideoCapture(str(video))
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise RuntimeError("RGB detector track could not read the supplied video")
    results = []
    for label, weights in RGB_MODELS:
        try:
            cls = RTDETR if weights.startswith("rtdetr") else YOLO
            model = cls(weights)
            prediction = model.predict(frame, conf=0.25, verbose=False)[0]
            annotated = prediction.plot()
            image = output / f"{label.lower().replace('-', '_')}.jpg"
            cv2.imwrite(str(image), annotated)
            findings = []
            names = prediction.names
            if prediction.boxes is not None:
                for box in prediction.boxes:
                    xyxy = [round(float(v), 3) for v in box.xyxy[0].tolist()]
                    confidence = round(float(box.conf[0]), 6)
                    class_id = int(box.cls[0])
                    findings.append({"type":"detection","label":names[class_id] if isinstance(names, dict) else str(class_id),"confidence":confidence,"bboxPixels":xyxy,"source":{"repository":"RGB detector track","model":label,"checkpoint":weights}})
            results.append({"adapterId": f"rgb12-{label.lower().replace('-', '-')}", "repository": f"RGB detector track / {label}", "model": label, "executionStatus":"COMPLETED", "ran":True, "reason":"Real pretrained RGB video detector executed", "visualArtifactPath":str(image), "findingRecords":findings})
        except Exception as exc:
            results.append({"adapterId":f"rgb12-{label.lower()}","repository":f"RGB detector track / {label}","model":label,"executionStatus":"FAILED","ran":False,"reason":str(exc),"findingRecords":[]})
    return {"mode":"rgb12","results":results}

def _synthetic(video: Path, output: Path) -> dict[str, Any]:
    cap = cv2.VideoCapture(str(video)); ok, frame = cap.read(); cap.release()
    if not ok or frame is None: raise RuntimeError("Synthetic track could not read video")
    h, w = frame.shape[:2]; results=[]
    for index, (label, _) in enumerate(RGB_MODELS):
        image = frame.copy(); x = int(w * (0.08 + (index % 4) * 0.2)); y = int(h * (0.12 + (index // 4) * 0.18)); x2=min(w-1,x+int(w*.18)); y2=min(h-1,y+int(h*.2))
        cv2.rectangle(image,(x,y),(x2,y2),(0,255,255),3); cv2.putText(image,f"SIMULATED / {label}",(x,max(24,y-8)),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,255,255),2)
        path=output/f"synthetic_{index:02d}.jpg"; cv2.imwrite(str(path),image)
        results.append({"adapterId":f"synthetic-{index:02d}","repository":f"Synthetic demo / {label}","model":label,"executionStatus":"SIMULATED","ran":False,"reason":"Synthetic visualization only; not an ML detection","visualArtifactPath":str(path),"findingRecords":[]})
    return {"mode":"synthetic","results":results}
