# Smart Surveillance System

A desktop surveillance application built with **OpenCV** and **Tkinter**, featuring real-time motion detection, object recognition (MobileNet SSD), automatic clip recording, and a video analysis tool.

---

## Features

| Tab          | Feature                                                                                        |
| ------------ | ---------------------------------------------------------------------------------------------- |
| Live Camera  | Real-time feed, motion detection (MOG2), object detection (MobileNet SSD), auto clip recording |
| Import Video | Load any video file, analyse for motion & objects at variable speed                            |
| Saved Clips  | Browse, play, and delete motion-triggered clips                                                |

**Detected object categories:** Person · Vehicle (car, bus, motorbike, bicycle…) · Animal (dog, cat, bird, horse…) · Other

---

## Installation

```bash
# 1. Clone / copy the project folder
cd smart_surveillance

# 2. Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python main.py
```

> **Model download:** On first launch the app automatically downloads MobileNet SSD weights (~23 MB) into the `models/` folder.

---

## Requirements

- Python 3.10+
- Webcam (optional, for Live Camera tab)
- Windows / macOS / Linux

---

## Project Structure

```
smart_surveillance/
├── main.py                     Entry point
├── requirements.txt
├── models/                     Auto-downloaded model weights
├── saved_clips/                Motion-triggered .avi clips
└── app/
    ├── ui/
    │   ├── main_window.py      Root window & theme
    │   ├── live_camera_tab.py  Live feed + detection
    │   ├── import_video_tab.py Video file analyser
    │   └── saved_clips_tab.py  Clip browser & player
    ├── core/
    │   ├── motion_detector.py  MOG2 background subtraction
    │   ├── object_detector.py  MobileNet SSD wrapper
    │   ├── clip_recorder.py    Pre/post buffer recorder
    │   └── video_processor.py  Unified pipeline
    └── utils/
        ├── config.py           Constants & paths
        └── helpers.py          Frame conversion utilities
```

---

## Configuration

Edit `app/utils/config.py` to adjust:

| Constant               | Default | Description                     |
| ---------------------- | ------- | ------------------------------- |
| `CONFIDENCE_THRESHOLD` | 0.40    | Object detection min confidence |
| `MOTION_THRESHOLD`     | 500     | Min contour area for motion     |
| `CLIP_PRE_SECONDS`     | 2       | Seconds before motion saved     |
| `CLIP_POST_SECONDS`    | 3       | Seconds after motion saved      |
| `CLIP_FPS`             | 20      | Output clip frame rate          |
