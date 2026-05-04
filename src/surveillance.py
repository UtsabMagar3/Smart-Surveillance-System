import os
import threading
import time
import cv2

from src.config import (
    SHOW_WINDOW,
    WINDOW_NAME,
    MIN_MOTION_AREA,
    MOTION_COOLDOWN_SEC,
    OUTPUT_DIR,
    CLIPS_DIR,
    SNAPSHOTS_DIR,
    FPS_OVERRIDE,
    PREBUFFER_SEC,
    POSTBUFFER_SEC,
    YOLO_MODEL,
    DETECT_EVERY_N_FRAMES,
    CONF_THRESH,
)
from src.camera import read_frame, get_fps
from src.motion import MotionDetector
from src.detector import ObjectDetector
from src.recorder import ClipRecorder
from src.annotate import draw_timestamp, draw_motion, draw_boxes


def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CLIPS_DIR, exist_ok=True)
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)


def run_surveillance(cap: cv2.VideoCapture, stop_event: threading.Event | None = None):
    """
    Motion + YOLO pipeline. Release cap and destroy OpenCV windows when done.
    If stop_event is set, exit the loop cooperatively.
    """
    ensure_dirs()

    fps = FPS_OVERRIDE or get_fps(cap)
    frame = read_frame(cap)
    if frame is None:
        cap.release()
        raise RuntimeError("Could not read first frame from source")

    h, w = frame.shape[:2]
    frame_size = (w, h)

    motion = MotionDetector(min_area=MIN_MOTION_AREA)
    detector = ObjectDetector(model_path=YOLO_MODEL, conf_thresh=CONF_THRESH)
    recorder = ClipRecorder(
        clips_dir=CLIPS_DIR, fps=fps, frame_size=frame_size, prebuffer_sec=PREBUFFER_SEC
    )

    recording = False
    last_motion_time = 0.0
    frame_idx = 0
    last_dets = []

    if SHOW_WINDOW:
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

    try:
        while True:
            if stop_event is not None and stop_event.is_set():
                break

            frame = read_frame(cap)
            if frame is None:
                break

            recorder.push_prebuffer(frame)

            motion_now, _, _ = motion.detect(frame)
            now = time.time()
            if motion_now:
                last_motion_time = now

            if frame_idx % DETECT_EVERY_N_FRAMES == 0 and (motion_now or recording):
                last_dets = detector.detect(frame)

            if motion_now and not recording:
                recorder.start()
                recording = True

            if recording:
                if (now - last_motion_time) <= (MOTION_COOLDOWN_SEC + POSTBUFFER_SEC):
                    pass
                else:
                    recorder.stop()
                    recording = False

            draw_timestamp(frame)
            draw_motion(frame, motion_now)
            draw_boxes(frame, last_dets)

            if recording:
                recorder.write(frame)

            if SHOW_WINDOW:
                cv2.imshow(WINDOW_NAME, frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                if stop_event is not None and stop_event.is_set():
                    break
            elif stop_event is not None and stop_event.is_set():
                break

            frame_idx += 1
    finally:
        recorder.stop()
        cap.release()
        if SHOW_WINDOW:
            cv2.destroyAllWindows()
