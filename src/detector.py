from ultralytics import YOLO

# COCO-ish mappings (YOLO pretrained)
VEHICLE = {"car", "truck", "bus", "motorcycle", "bicycle"}
ANIMAL = {"dog", "cat", "horse", "sheep", "cow", "bird"}  # depends on model/classes

def group_label(name: str) -> str:
    if name == "person":
        return "human"
    if name in VEHICLE:
        return "vehicle"
    if name in ANIMAL:
        return "animal"
    return "other"

class ObjectDetector:
    def __init__(self, model_path: str, conf_thresh: float):
        self.model = YOLO(model_path)
        self.conf = conf_thresh

    def detect(self, frame):
        results = self.model.predict(frame, conf=self.conf, verbose=False)
        r = results[0]
        dets = []
        if r.boxes is None:
            return dets

        names = r.names
        for b in r.boxes:
            cls_id = int(b.cls[0].item())
            conf = float(b.conf[0].item())
            x1, y1, x2, y2 = [int(v.item()) for v in b.xyxy[0]]
            name = names.get(cls_id, str(cls_id))
            dets.append({
                "name": name,
                "group": group_label(name),
                "conf": conf,
                "box": (x1, y1, x2, y2),
            })
        return dets