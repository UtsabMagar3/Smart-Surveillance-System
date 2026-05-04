import os
import cv2
from collections import deque
from datetime import datetime

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def clip_name(prefix="event"):
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

class ClipRecorder:
    def __init__(self, clips_dir: str, fps: float, frame_size, prebuffer_sec: float):
        self.clips_dir = clips_dir
        self.fps = fps
        self.frame_size = frame_size
        self.prebuffer = deque(maxlen=int(max(1, prebuffer_sec * fps)))
        self.writer = None
        ensure_dir(self.clips_dir)

    def push_prebuffer(self, frame):
        self.prebuffer.append(frame.copy())

    def start(self):
        if self.writer is not None:
            return None
        path = os.path.join(self.clips_dir, clip_name("motion"))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writer = cv2.VideoWriter(path, fourcc, self.fps, self.frame_size)
        for f in self.prebuffer:
            self.writer.write(f)
        return path

    def write(self, frame):
        if self.writer is not None:
            self.writer.write(frame)

    def stop(self):
        if self.writer is None:
            return
        self.writer.release()
        self.writer = None