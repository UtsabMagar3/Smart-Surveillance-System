import cv2


def open_camera(index: int):
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera index {index}")
    return cap


def open_video_source(source: int | str):
    """
    Open a capture from a camera index (int) or a video file path (str).
    """
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        if isinstance(source, int):
            raise RuntimeError(f"Could not open camera index {source}")
        raise RuntimeError(f"Could not open video file: {source}")
    return cap

def read_frame(cap):
    ok, frame = cap.read()
    if not ok or frame is None:
        return None
    return frame

def get_fps(cap, fallback=25.0):
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps is None or fps <= 1:
        return fallback
    return float(fps)