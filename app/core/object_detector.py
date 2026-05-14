import cv2
import numpy as np
from app.utils.config import CONFIDENCE_THRESHOLD, VEHICLE_LABELS, ANIMAL_LABELS, PERSON_LABELS

_COLORS = {
    "person":  (255,  80,  80),
    "vehicle": (255, 200,   0),
    "animal":  ( 80, 230,   0),
    "other":   (180, 180, 180),
}


def _group(name: str) -> str:
    if name in PERSON_LABELS:  return "person"
    if name in VEHICLE_LABELS: return "vehicle"
    if name in ANIMAL_LABELS:  return "animal"
    return "other"


class ObjectDetector:
    def __init__(self, conf: float = CONFIDENCE_THRESHOLD):
        self.conf   = conf
        self._model = None
        self._ready = False

    def load(self, cb=None) -> bool:
        try:
            from ultralytics import YOLO
            self._model = YOLO("yolov8n.pt")
            self._ready = True
            return True
        except Exception as e:
            if cb: cb(str(e))
            return False

    @property
    def is_ready(self) -> bool:
        return self._ready

    def detect(self, frame: np.ndarray) -> list[dict]:
        if not self._ready:
            return []
        r = self._model.predict(frame, conf=self.conf, verbose=False)[0]
        out = []
        if r.boxes is None:
            return out
        for b in r.boxes:
            name = r.names[int(b.cls[0].item())]
            x1, y1, x2, y2 = [int(v.item()) for v in b.xyxy[0]]
            out.append({
                "name":  name,
                "group": _group(name),
                "conf":  float(b.conf[0].item()),
                "box":   (x1, y1, x2, y2),
            })
        return out

    def draw(self, frame: np.ndarray, dets: list[dict]) -> np.ndarray:
        out  = frame.copy()
        font = cv2.FONT_HERSHEY_SIMPLEX
        for d in dets:
            x1, y1, x2, y2 = d["box"]
            color = _COLORS.get(d["group"], _COLORS["other"])
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 1)
            tx, ty = x1 + 2, y1 - 3 if y1 > 12 else y1 + 11
            cv2.putText(out, d["name"], (tx + 1, ty + 1), font, 0.35, (0, 0, 0), 1, cv2.LINE_AA)
            cv2.putText(out, d["name"], (tx,     ty),     font, 0.35, color,      1, cv2.LINE_AA)
        return out
