# Motion Detection Module
import cv2
import numpy as np
from app.utils.config import MIN_MOTION_AREA

MOTION_COLOR = (100, 255, 0)


class MotionDetector:
    def __init__(self, min_area: int = MIN_MOTION_AREA):
        self.min_area = min_area
        self._bg = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=16, detectShadows=False
        )

    def detect(self, frame: np.ndarray):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (7, 7), 0)

        fg = self._bg.apply(gray)
        fg = cv2.threshold(fg, 100, 255, cv2.THRESH_BINARY)[1]
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel, iterations=1)
        fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel, iterations=1)
        fg = cv2.dilate(fg, kernel, iterations=1)

        cnts, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes, motion = [], False
        for c in cnts:
            if cv2.contourArea(c) < self.min_area:
                continue
            boxes.append(cv2.boundingRect(c))
            motion = True
        return motion, boxes

    def draw(self, frame: np.ndarray, boxes: list) -> np.ndarray:
        out = frame.copy()
        for (x, y, w, h) in boxes:
            cv2.rectangle(out, (x, y), (x + w, y + h), MOTION_COLOR, 1)
        return out

    def reset(self):
        self._bg = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=16, detectShadows=False
        )
