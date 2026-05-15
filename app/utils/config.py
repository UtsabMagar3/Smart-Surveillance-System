# Configuration Module
import os

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIPS_DIR  = os.path.join(BASE_DIR, "saved_clips")
os.makedirs(CLIPS_DIR, exist_ok=True)

VEHICLE_LABELS = {"car","bus","truck","motorcycle","bicycle","airplane","boat","train"}
ANIMAL_LABELS  = {"cat","dog","bird","cow","horse","sheep","elephant","bear","zebra","giraffe"}
PERSON_LABELS  = {"person"}

CONFIDENCE_THRESHOLD = 0.50
MIN_MOTION_AREA      = 1500
DETECT_EVERY_N       = 2

CLIP_FPS         = 20
CLIP_PRE_SECONDS = 3.0
CLIP_POST_SECONDS= 5.0

APP_TITLE  = "Smart Surveillance System"
APP_WIDTH  = 1280
APP_HEIGHT = 780

BG_DARK    = "#0d1117"
BG_PANEL   = "#161b22"
BG_CARD    = "#21262d"
ACCENT     = "#238636"
ACCENT_ALERT = "#da3633"
ACCENT_INFO  = "#1f6feb"
FG_PRIMARY = "#e6edf3"
FG_MUTED   = "#8b949e"
BORDER     = "#30363d"

FONT_MONO = ("Consolas", 10)
FONT_UI   = ("Segoe UI", 10)
