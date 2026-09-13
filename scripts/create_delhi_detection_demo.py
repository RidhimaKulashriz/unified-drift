from pathlib import Path
from ultralytics import YOLO

root = Path(__file__).resolve().parents[1]
source = root / 'client/public/delhi-demo/delhi-traffic-source.jpg'
out = root / 'client/public/delhi-demo/delhi-traffic-yolo11n.jpg'
model = YOLO('yolo11n.pt')
results = model.predict(source=str(source), conf=0.25, save=False, verbose=False)
annotated = results[0].plot()
import cv2
cv2.imwrite(str(out), annotated)
print(out)
