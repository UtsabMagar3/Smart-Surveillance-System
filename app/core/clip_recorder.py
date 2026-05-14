import os, cv2, json, threading
import numpy as np
from collections import deque
from datetime import datetime
from app.utils.config import CLIPS_DIR, CLIP_FPS, CLIP_PRE_SECONDS, CLIP_POST_SECONDS
from app.utils.helpers import timestamp_filename


def _annotate(frame, ts, source, frame_no, dets, motion):
    out  = frame.copy()
    h, w = out.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.rectangle(out, (0, 0), (w, 18), (20, 20, 20), -1)
    cv2.putText(out, f"{ts}  src:{source}", (5, 13), font, 0.35, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.rectangle(out, (0, h - 16), (w, h), (20, 20, 20), -1)
    cv2.putText(out, f"f:{frame_no}", (5, h - 4), font, 0.32, (130, 130, 130), 1, cv2.LINE_AA)
    if motion:
        cv2.putText(out, "MOTION", (w - 58, h - 4), font, 0.32, (80, 80, 255), 1, cv2.LINE_AA)
    if dets:
        labels = ", ".join({d["name"] for d in dets})
        cv2.putText(out, labels, (70, h - 4), font, 0.32, (160, 220, 160), 1, cv2.LINE_AA)
    return out


class ClipRecorder:
    def __init__(self, fw=640, fh=480, fps=CLIP_FPS, source="live", on_saved=None):
        self.fw, self.fh, self.fps, self.source = fw, fh, fps, source
        self._on_saved = on_saved          # callback() fired when a clip is finalised
        self._pre   = deque(maxlen=int(fps * CLIP_PRE_SECONDS))
        self._writer= None
        self._post  = 0
        self._lock  = threading.Lock()
        self._path  = None
        self._start = None
        self._fno   = 0
        self._evts  = []

    def push(self, annotated_frame, dets=None, motion=False):
        with self._lock:
            dets = dets or []
            self._pre.append((annotated_frame.copy(), list(dets), motion))
            if self._writer:
                self._write(annotated_frame, dets, motion)
                if self._post > 0:
                    self._post -= 1
                    if self._post == 0:
                        self._close()

    def trigger(self):
        with self._lock:
            if self._writer:
                self._post = int(self.fps * CLIP_POST_SECONDS)
                return
            self._open()

    def stop_recording(self):
        with self._lock:
            if self._writer:
                self._post = int(self.fps * CLIP_POST_SECONDS)

    @property
    def is_recording(self):
        with self._lock:
            return self._writer is not None

    def release(self):
        with self._lock:
            self._close()

    def _open(self):
        path = os.path.join(CLIPS_DIR, timestamp_filename("clip", "avi"))
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        self._writer = cv2.VideoWriter(path, fourcc, self.fps, (self.fw, self.fh))
        self._path   = path
        self._start  = datetime.now()
        self._fno    = 0
        self._evts   = []
        for (ann, d, m) in self._pre:
            self._write(ann, d, m)
        self._post = int(self.fps * CLIP_POST_SECONDS)

    def _write(self, frame, dets, motion):
        ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ann = _annotate(frame, ts, self.source, self._fno, dets, motion)
        self._writer.write(cv2.resize(ann, (self.fw, self.fh)))
        self._fno += 1
        if dets or motion:
            self._evts.append({
                "frame": self._fno, "time": ts, "motion": motion,
                "dets": [{"name": d["name"], "group": d["group"],
                          "conf": round(d["conf"], 2)} for d in dets],
            })

    def _close(self):
        if not self._writer:
            return
        self._writer.release()
        self._writer = None
        if self._path and self._start:
            ended = datetime.now()
            report = {
                "source": self.source,
                "clip": os.path.basename(self._path),
                "started": self._start.strftime("%Y-%m-%d %H:%M:%S"),
                "ended":   ended.strftime("%Y-%m-%d %H:%M:%S"),
                "duration_s": round((ended - self._start).total_seconds(), 1),
                "frames": self._fno,
                "events": len(self._evts),
                "log": self._evts,
            }
            try:
                with open(self._path.replace(".avi", "_report.json"), "w") as f:
                    json.dump(report, f, indent=2)
            except OSError:
                pass
        self._post = 0
        self._fno  = 0
        self._evts = []
        self._path = None
        self._start= None
        # Fire callback AFTER lock work is done (called while lock is still held,
        # but callback only sets an atomic int — safe)
        if self._on_saved:
            self._on_saved()