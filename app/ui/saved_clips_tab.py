# Saved Clips Tab UI Module
import tkinter as tk
from tkinter import ttk, messagebox
import cv2, os, threading, time
from app.utils.config  import (CLIPS_DIR, BG_DARK, BG_CARD, BG_PANEL,
                                FG_MUTED, FG_PRIMARY, FONT_MONO, FONT_UI, BORDER, ACCENT)
from app.utils.helpers import cv2_to_imgtk_fit, format_duration


class SavedClipsTab(ttk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.configure(style="Dark.TFrame")
        self._cap    = None
        self._playing= False
        self._pause  = False
        self._thread = None
        self._clips  : list[str] = []
        self._total  = 0
        self._fps_n  = 25.0
        self._img_id = None
        self._build()
        self._refresh()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        # Left — clip list
        left = ttk.Frame(self, style="Panel.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        hdr = ttk.Frame(left, style="Panel.TFrame")
        hdr.grid(row=0, column=0, sticky="ew", pady=(6, 4))
        hdr.columnconfigure(0, weight=1)
        ttk.Label(hdr, text="SAVED CLIPS",
                  style="SectionHead.TLabel").grid(row=0, column=0, sticky="w", padx=8)
        br = ttk.Frame(hdr, style="Panel.TFrame")
        br.grid(row=1, column=0, sticky="ew", padx=4, pady=(2, 4))
        ttk.Button(br, text="↻  Refresh",     command=self._refresh,
                   style="Dark.TButton").pack(side="left", padx=4)
        ttk.Button(br, text="🗑  Delete",      command=self._delete,
                   style="Dark.TButton").pack(side="left", padx=4)
        ttk.Button(br, text="📂  Open folder", command=self._open_folder,
                   style="Dark.TButton").pack(side="left", padx=4)

        lf = ttk.Frame(left, style="Card.TFrame")
        lf.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        lf.rowconfigure(0, weight=1)
        lf.columnconfigure(0, weight=1)
        self._lb = tk.Listbox(lf, bg=BG_CARD, fg=FG_PRIMARY,
                               selectbackground=ACCENT, selectforeground="#fff",
                               font=FONT_MONO, relief="flat", bd=0, activestyle="none")
        lsb = ttk.Scrollbar(lf, orient="vertical", command=self._lb.yview)
        self._lb.configure(yscrollcommand=lsb.set)
        self._lb.grid(row=0, column=0, sticky="nsew")
        lsb.grid(row=0, column=1, sticky="ns")
        self._lb.bind("<<ListboxSelect>>", self._on_sel)
        self._lb.bind("<Double-Button-1>",
                      lambda _: (self._on_sel(), self._play_clip()))

        self._count_v = tk.StringVar(value="0 clips")
        ttk.Label(left, textvariable=self._count_v,
                  style="Muted.TLabel").grid(row=2, column=0, sticky="w",
                                              padx=8, pady=(0, 6))

        # Right — player
        right = ttk.Frame(self, style="Dark.TFrame")
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        ctrl = ttk.Frame(right, style="Panel.TFrame")
        ctrl.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self._btn_play = ttk.Button(ctrl, text="▶  Play", command=self._play_clip,
                                    style="Accent.TButton", state="disabled")
        self._btn_play.pack(side="left", padx=6, pady=4)
        self._btn_pause = ttk.Button(ctrl, text="⏸  Pause", command=self._toggle_pause,
                                     style="Dark.TButton", state="disabled")
        self._btn_pause.pack(side="left")
        self._btn_stop = ttk.Button(ctrl, text="■  Stop", command=self._stop_play,
                                    style="Dark.TButton", state="disabled")
        self._btn_stop.pack(side="left", padx=6)
        self._name_v = tk.StringVar(value="No clip selected")
        ttk.Label(ctrl, textvariable=self._name_v,
                  style="Muted.TLabel").pack(side="right", padx=10)

        # Canvas
        cc = tk.Frame(right, bg=BORDER, bd=1)
        cc.grid(row=1, column=0, sticky="nsew")
        cc.rowconfigure(0, weight=1)
        cc.columnconfigure(0, weight=1)
        self._canvas = tk.Canvas(cc, bg="#000", highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._img_id = self._canvas.create_image(0, 0, anchor="nw", tags="feed")
        self._canvas.bind("<Configure>", self._on_canvas_resize)

        # Seek bar
        sr = ttk.Frame(right, style="Dark.TFrame")
        sr.grid(row=2, column=0, sticky="ew", pady=(4, 2))
        sr.columnconfigure(0, weight=1)
        self._seek_v = tk.DoubleVar(value=0)
        ttk.Scale(sr, from_=0, to=100, variable=self._seek_v,
                  orient="horizontal").grid(row=0, column=0, sticky="ew")
        self._time_v = tk.StringVar(value="00:00 / 00:00")
        ttk.Label(sr, textvariable=self._time_v,
                  style="Muted.TLabel").grid(row=0, column=1, padx=(8, 0))

        info = ttk.Frame(right, style="Card.TFrame")
        info.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        self._info_v = tk.StringVar(value="")
        ttk.Label(info, textvariable=self._info_v,
                  style="Muted.TLabel", wraplength=620).pack(
                  anchor="w", padx=10, pady=6)

    def _on_canvas_resize(self, event=None):
        if not self._playing:
            cw = event.width  if event else self._canvas.winfo_width()
            ch = event.height if event else self._canvas.winfo_height()
            self._draw_placeholder(cw, ch)

    def _draw_placeholder(self, cw=None, ch=None):
        self._canvas.itemconfig(self._img_id, image="")
        self._canvas.delete("ph")
        cw = cw or self._canvas.winfo_width()
        ch = ch or self._canvas.winfo_height()
        if cw < 10 or ch < 10:
            return
        self._canvas.create_text(cw // 2, ch // 2 - 12, tags="ph",
            text="No Clip Playing", fill=FG_MUTED, font=(FONT_UI[0], 15))
        self._canvas.create_text(cw // 2, ch // 2 + 14, tags="ph",
            text="Select a clip and press  ▶ Play", fill=BORDER, font=FONT_UI)

    def _refresh(self):
        files = sorted(
            [f for f in os.listdir(CLIPS_DIR) if f.lower().endswith(".avi")],
            reverse=True)
        self._clips = files
        self._lb.delete(0, "end")
        for f in files:
            self._lb.insert("end", f)
        self._count_v.set(f"{len(files)} clip{'s' if len(files) != 1 else ''}")

    def _on_sel(self, _=None):
        sel = self._lb.curselection()
        if not sel:
            return
        self._load_clip(os.path.join(CLIPS_DIR, self._clips[sel[0]]))

    def _load_clip(self, path):
        self._stop_play()
        self._rel_cap()
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            messagebox.showerror("Error", f"Cannot open:\n{path}")
            return
        self._cap   = cap
        fps   = cap.get(cv2.CAP_PROP_FPS) or 25
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fw    = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        fh    = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._total = total
        self._fps_n = fps
        self._name_v.set(os.path.basename(path))
        self._info_v.set(
            f"File: {os.path.basename(path)}   |   "
            f"{fw}×{fh}   |   {fps:.1f} fps   |   "
            f"{format_duration(total / fps)}")
        self._btn_play.configure(state="normal")
        # Show first frame letterboxed
        ret, frame = cap.read()
        if ret:
            self._draw_frame(frame)
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def _delete(self):
        sel = self._lb.curselection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a clip first.")
            return
        fname = self._clips[sel[0]]
        path  = os.path.join(CLIPS_DIR, fname)
        if not messagebox.askyesno("Delete", f"Delete '{fname}'?"):
            return
        # Stop playback and fully release file handle before deleting
        self._stop_play()
        self._rel_cap()
        time.sleep(0.15)
        try:
            os.remove(path)
        except OSError as e:
            messagebox.showerror("Delete Failed", str(e))
            return
        # Refresh list and FULLY clear the canvas — no ghost frame
        self._refresh()
        # Use after() so canvas geometry is settled before redrawing placeholder
        self._canvas.after(10, self._draw_placeholder)
        self._name_v.set("No clip selected")
        self._info_v.set("")
        self._time_v.set("00:00 / 00:00")
        self._seek_v.set(0)
        self._btn_play.configure(state="disabled")

    def _rel_cap(self):
        if self._cap:
            self._cap.release()
            self._cap = None

    def _open_folder(self):
        import subprocess, sys
        if sys.platform == "win32":
            os.startfile(CLIPS_DIR)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", CLIPS_DIR])
        else:
            subprocess.Popen(["xdg-open", CLIPS_DIR])

    def _play_clip(self):
        if not self._cap or self._playing:
            return
        self._playing = True
        self._pause   = False
        self._btn_play.configure(state="disabled")
        self._btn_pause.configure(state="normal")
        self._btn_stop.configure(state="normal")
        self._canvas.delete("ph")
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _toggle_pause(self):
        self._pause = not self._pause
        self._btn_pause.configure(text="▶  Resume" if self._pause else "⏸  Pause")

    def _stop_play(self):
        self._playing = False
        self._pause   = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        if self._cap:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self._btn_play.configure(state="normal" if self._cap else "disabled")
        self._btn_pause.configure(state="disabled", text="⏸  Pause")
        self._btn_stop.configure(state="disabled")

    def _loop(self):
        fps   = self._fps_n or 25
        delay = 1.0 / fps
        while self._playing:
            if self._pause:
                time.sleep(0.05)
                continue
            if not self._cap:
                break
            ret, frame = self._cap.read()
            if not ret:
                self.after(0, self._end)
                break
            pos = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))
            self.after(0, self._update, frame, pos)
            time.sleep(max(delay, 0.001))

    def _draw_frame(self, frame):
        cw = max(self._canvas.winfo_width(), 4)
        ch = max(self._canvas.winfo_height(), 4)
        imgtk = cv2_to_imgtk_fit(frame, cw, ch)
        self._canvas.imgtk = imgtk
        self._canvas.delete("ph")
        self._canvas.itemconfig(self._img_id, image=imgtk)

    def _update(self, frame, pos):
        if not self._playing:
            return
        self._draw_frame(frame)
        fps = self._fps_n or 25
        self._time_v.set(
            f"{format_duration(pos / fps)} / "
            f"{format_duration(self._total / fps)}")
        self._seek_v.set(pos)

    def _end(self):
        self._playing = False
        self._btn_play.configure(state="normal")
        self._btn_pause.configure(state="disabled")
        self._btn_stop.configure(state="disabled")
        if self._cap:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def on_show(self):
        self._refresh()
        if not self._playing:
            self._canvas.after(50, self._draw_placeholder)

    def on_hide(self):
        self._stop_play()
        self._rel_cap()