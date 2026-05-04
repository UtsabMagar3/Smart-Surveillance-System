import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from src.config import CAMERA_INDEX, CLIPS_DIR
from src.camera import open_video_source
from src.surveillance import ensure_dirs, run_surveillance


BG = "#0f0f0f"
CARD = "#1a1a1a"
FG = "#e8e8e8"
ACCENT = "#3d5a80"
ACCENT_HOVER = "#4a6fa5"


def _open_path(path: str):
    path = os.path.normpath(path)
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


def _style_root(root: tk.Tk):
    root.title("Smart Surveillance")
    root.configure(bg=BG)
    root.minsize(640, 480)
    try:
        if sys.platform == "win32":
            root.state("zoomed")
        elif sys.platform == "darwin":
            root.state("zoomed")
        else:
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            root.geometry(f"{sw}x{sh}+0+0")
            try:
                root.attributes("-zoomed", True)
            except tk.TclError:
                pass
    except tk.TclError:
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{sw}x{sh}+0+0")


def _btn(parent, text, command):
    b = tk.Button(
        parent,
        text=text,
        command=command,
        font=("Segoe UI", 11),
        bg=CARD,
        fg=FG,
        activebackground=ACCENT_HOVER,
        activeforeground=FG,
        relief=tk.FLAT,
        padx=20,
        pady=14,
        cursor="hand2",
        highlightthickness=0,
        bd=0,
    )
    b.bind("<Enter>", lambda e: b.configure(bg=ACCENT))
    b.bind("<Leave>", lambda e: b.configure(bg=CARD))
    return b


class SurveillanceApp:
    def __init__(self):
        self.root = tk.Tk()
        _style_root(self.root)
        ensure_dirs()

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        main = tk.Frame(self.root, bg=BG)
        main.pack(fill=tk.BOTH, expand=True, padx=28, pady=24)

        tk.Label(
            main,
            text="Smart Surveillance",
            font=("Segoe UI Semibold", 18),
            bg=BG,
            fg=FG,
        ).pack(anchor=tk.W, pady=(0, 4))
        tk.Label(
            main,
            text="Choose a source or open saved clips.",
            font=("Segoe UI", 10),
            bg=BG,
            fg="#888888",
        ).pack(anchor=tk.W, pady=(0, 20))

        btns = tk.Frame(main, bg=BG)
        btns.pack(fill=tk.BOTH, expand=True)
        for text, cmd in (
            ("Live camera", self._on_live),
            ("Import video…", self._on_import),
            ("Saved clips", self._on_clips),
        ):
            f = tk.Frame(btns, bg=BG)
            f.pack(fill=tk.X, pady=6)
            _btn(f, text, cmd).pack(fill=tk.X)

        self._status = tk.StringVar(value="Ready")
        tk.Label(
            main,
            textvariable=self._status,
            font=("Segoe UI", 9),
            bg=BG,
            fg="#666666",
        ).pack(anchor=tk.W, pady=(16, 0))

        stop_row = tk.Frame(main, bg=BG)
        stop_row.pack(fill=tk.X, pady=(12, 0))
        tk.Button(
            stop_row,
            text="Stop session",
            command=self._stop_session,
            font=("Segoe UI", 9),
            bg="#2a2a2a",
            fg=FG,
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
            highlightthickness=0,
        ).pack(anchor=tk.W)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_status(self, text: str):
        self.root.after(0, self._status.set, text)

    def _session_busy(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _start_session(self, source: int | str, label: str):
        if self._session_busy():
            messagebox.showinfo("Session active", "Stop the current session first.")
            return
        self._stop.clear()
        try:
            cap = open_video_source(source)
        except RuntimeError as e:
            messagebox.showerror("Could not open", str(e))
            return

        self._set_status(f"Running: {label} — press Q in the video window or Stop session.")

        def worker():
            try:
                run_surveillance(cap, stop_event=self._stop)
            except Exception as e:
                self._set_status("Error.")
                self.root.after(0, lambda: messagebox.showerror("Surveillance error", str(e)))
            else:
                self._set_status("Ready")

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def _on_live(self):
        self._start_session(CAMERA_INDEX, "Live camera")

    def _on_import(self):
        path = filedialog.askopenfilename(
            title="Select video",
            filetypes=[
                ("Video", "*.mp4 *.avi *.mkv *.mov *.webm"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        self._start_session(path, os.path.basename(path))

    def _on_clips(self):
        win = tk.Toplevel(self.root)
        win.title("Saved clips")
        win.configure(bg=BG)
        win.transient(self.root)
        win.update_idletasks()
        try:
            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
            w, h = max(800, int(sw * 0.92)), max(600, int(sh * 0.88))
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
            win.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            win.geometry("1200x800")

        top = tk.Frame(win, bg=BG)
        top.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        tk.Label(top, text="Saved clips", font=("Segoe UI Semibold", 14), bg=BG, fg=FG).pack(
            anchor=tk.W
        )

        list_frame = tk.Frame(top, bg=CARD)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 8))

        scroll = ttk.Scrollbar(list_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        lb = tk.Listbox(
            list_frame,
            font=("Consolas", 10),
            bg=CARD,
            fg=FG,
            selectbackground=ACCENT,
            highlightthickness=0,
            bd=0,
            yscrollcommand=scroll.set,
        )
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=lb.yview)

        def refresh():
            lb.delete(0, tk.END)
            ensure_dirs()
            if not os.path.isdir(CLIPS_DIR):
                return
            files = [
                os.path.join(CLIPS_DIR, f)
                for f in os.listdir(CLIPS_DIR)
                if f.lower().endswith((".mp4", ".avi", ".mkv", ".mov"))
            ]
            files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            for p in files:
                lb.insert(tk.END, os.path.basename(p))
            lb._paths = files  # type: ignore[attr-defined]

        def open_selected():
            sel = lb.curselection()
            if not sel:
                messagebox.showinfo("Clips", "Select a clip first.")
                return
            paths = getattr(lb, "_paths", [])
            idx = sel[0]
            if idx < len(paths):
                _open_path(paths[idx])

        def open_folder():
            ensure_dirs()
            if os.path.isdir(CLIPS_DIR):
                _open_path(CLIPS_DIR)

        refresh()

        def on_double(_):
            open_selected()

        lb.bind("<Double-Button-1>", on_double)

        row = tk.Frame(top, bg=BG)
        row.pack(fill=tk.X)
        tk.Button(
            row,
            text="Refresh",
            command=refresh,
            font=("Segoe UI", 9),
            bg="#2a2a2a",
            fg=FG,
            relief=tk.FLAT,
            padx=10,
            pady=6,
        ).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(
            row,
            text="Open clip",
            command=open_selected,
            font=("Segoe UI", 9),
            bg="#2a2a2a",
            fg=FG,
            relief=tk.FLAT,
            padx=10,
            pady=6,
        ).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(
            row,
            text="Open folder",
            command=open_folder,
            font=("Segoe UI", 9),
            bg="#2a2a2a",
            fg=FG,
            relief=tk.FLAT,
            padx=10,
            pady=6,
        ).pack(side=tk.LEFT)

    def _stop_session(self):
        self._stop.set()
        self._set_status("Stopping…")

    def _on_close(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    SurveillanceApp().run()
