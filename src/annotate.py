import cv2
from datetime import datetime

def draw_timestamp(frame):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, ts, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

def draw_motion(frame, motion: bool):
    if motion:
        cv2.putText(frame, "MOTION", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

def draw_boxes(frame, dets):
    for d in dets:
        x1, y1, x2, y2 = d["box"]
        label = f'{d["group"]} ({d["name"]}) {d["conf"]:.2f}'
        color = (0, 255, 0) if d["group"] == "human" else (255, 255, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, max(20, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)