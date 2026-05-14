import cv2
import numpy as np
from PIL import Image, ImageTk
from datetime import datetime


def cv2_to_imgtk_fit(frame: np.ndarray, canvas_w: int, canvas_h: int) -> ImageTk.PhotoImage:
    fh, fw = frame.shape[:2]
    scale  = min(canvas_w / fw, canvas_h / fh)
    nw, nh = int(fw * scale), int(fh * scale)
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
    out     = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)
    x0      = (canvas_w - nw) // 2
    y0      = (canvas_h - nh) // 2
    out[y0:y0+nh, x0:x0+nw] = resized
    rgb = cv2.cvtColor(out, cv2.COLOR_BGR2RGB)
    return ImageTk.PhotoImage(image=Image.fromarray(rgb))


def timestamp_filename(prefix="clip", ext="avi") -> str:
    return f"{prefix}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.{ext}"


def format_duration(seconds: float) -> str:
    m, s = divmod(int(max(seconds, 0)), 60)
    return f"{m:02d}:{s:02d}"


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")