CAMERA_INDEX = 0  # change to 1/2 if needed

SHOW_WINDOW = True
WINDOW_NAME = "Smart Security Camera"

# Motion detection
MIN_MOTION_AREA = 2500          # increase to reduce false positives
MOTION_COOLDOWN_SEC = 2.0       # stop recording after this much no-motion

# Recording
OUTPUT_DIR = "output"
CLIPS_DIR = f"{OUTPUT_DIR}/clips"
SNAPSHOTS_DIR = f"{OUTPUT_DIR}/snapshots"
FPS_OVERRIDE = None             # None = use camera FPS if available
PREBUFFER_SEC = 3.0             # seconds saved before motion starts
POSTBUFFER_SEC = 5.0            # seconds saved after motion ends

# Detection
YOLO_MODEL = "yolov8n.pt"       # small & fast; auto-download by ultralytics
DETECT_EVERY_N_FRAMES = 3       # run YOLO every N frames (keeps it fast)
CONF_THRESH = 0.35

# Restricted zone (optional): list of (x,y) points in pixel coords.
# Leave as None to disable.
RESTRICTED_POLY = None