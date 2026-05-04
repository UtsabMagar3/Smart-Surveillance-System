import cv2
import numpy as np

class MotionDetector:
    def __init__(self, min_area: int):
        self.min_area = min_area
        self.bg = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=25, detectShadows=True)

    def detect(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        fg = self.bg.apply(gray)
        fg = cv2.threshold(fg, 200, 255, cv2.THRESH_BINARY)[1]  # remove shadows
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=2)
        fg = cv2.dilate(fg, None, iterations=2)

        cnts, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        motion_boxes = []
        motion = False
        for c in cnts:
            area = cv2.contourArea(c)
            if area < self.min_area:
                continue
            x, y, w, h = cv2.boundingRect(c)
            motion_boxes.append((x, y, w, h))
            motion = True

        return motion, motion_boxes, fg