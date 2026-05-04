import sys

from src.surveillance import ensure_dirs, run_surveillance
from src.config import CAMERA_INDEX
from src.camera import open_camera


def _cli_main():
    ensure_dirs()
    cap = open_camera(CAMERA_INDEX)
    run_surveillance(cap, stop_event=None)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        _cli_main()
    else:
        from src.ui import main as ui_main

        ui_main()
