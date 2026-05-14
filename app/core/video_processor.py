import cv2
import numpy as np
from datetime import datetime
from app.core.motion_detector import MotionDetector
from app.core.object_detector import ObjectDetector
from app.utils.config import DETECT_EVERY_N


class VideoProcessor:
    def __init__(self):
        self.motion   = MotionDetector()
        self.detector = ObjectDetector()
        self._do_obj  = True
        self._do_mot  = True
        self._n       = 0
        self._last_dets = []

    def load_model(self, cb=None) -> bool:
        return self.detector.load(cb)

    @property
    def model_ready(self) -> bool:
        return self.detector.is_ready

    def set_detect_objects(self, v: bool): self._do_obj = v
    def set_detect_motion(self,  v: bool): self._do_mot = v

    def process(self, frame: np.ndarray) -> dict:
        motion, boxes = False, []
        if self._do_mot:
            motion, boxes = self.motion.detect(frame)

        if self._do_obj and self.detector.is_ready and self._n % DETECT_EVERY_N == 0:
            self._last_dets = self.detector.detect(frame)
        self._n += 1
        dets = self._last_dets if self._do_obj else []

        ann = frame.copy()
        if boxes:
            ann = self.motion.draw(ann, boxes)
        if dets:
            ann = self.detector.draw(ann, dets)

        ts = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        cv2.putText(ann, ts, (7, ann.shape[0] - 6), cv2.FONT_HERSHEY_SIMPLEX,
                    0.32, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(ann, ts, (6, ann.shape[0] - 7), cv2.FONT_HERSHEY_SIMPLEX,
                    0.32, (160, 160, 160), 1, cv2.LINE_AA)

        return {"annotated": ann, "motion": motion, "boxes": boxes, "dets": dets}

    def reset(self):
        self.motion.reset()
        self._last_dets = []
        self._n = 0
