# Import Video Tab UI Module
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2, threading, time, os, json
from app.core.video_processor import VideoProcessor
from app.core.clip_recorder   import ClipRecorder
from app.utils.config         import *
from app.utils.helpers        import cv2_to_imgtk_fit, format_duration


class ImportVideoTab(ttk.Frame):
    SIDEBAR_W = 260

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.configure(style="Dark.TFrame")
        self._cap     = None
        self._run     = False
        self._pause   = False
        self._thread  = None
        self._proc    = VideoProcessor()
        self._rec     = None
        self._total   = 0
        self._fps     = 25.0
        self._clips   = 0
        self._was_rec = False
        self._img_id  = None
        self._build()
        threading.Thread(target=self._proc.load_model, daemon=True).start()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, minsize=self.SIDEBAR_W, weight=0)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self, style="Dark.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(10, 4), pady=10)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)

        # File bar
        fb = tk.Frame(left, bg=BG_PANEL, pady=5)
        fb.grid(row=0, column=0, sticky="ew")
        fb.columnconfigure(1, weight=1)
        tk.Button(fb, text="📂  Browse…", command=self._browse,
                  bg=ACCENT, fg="#fff", font=(FONT_UI[0], 10, "bold"),
                  relief="flat", padx=12, pady=5,
                  activebackground="#2ea043", cursor="hand2").grid(
                  row=0, column=0, padx=(10, 8), pady=5)
        self._path_v = tk.StringVar(value="No file selected")
        tk.Label(fb, textvariable=self._path_v, bg=BG_PANEL, fg=FG_MUTED,
                 font=(FONT_UI[0], 9)).grid(row=0, column=1, sticky="w")

        # Playback bar
        pb = tk.Frame(left, bg=BG_PANEL, pady=4)
        pb.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self._btn_play = tk.Button(pb, text="▶  Analyse", command=self._play,
            bg=ACCENT, fg="#fff", font=(FONT_UI[0], 10, "bold"),
            relief="flat", padx=12, pady=5, state="disabled",
            activebackground="#2ea043", cursor="hand2")
        self._btn_play.pack(side="left", padx=(10, 6))
        self._btn_pause = tk.Button(pb, text="⏸  Pause", command=self._toggle_pause,
            bg=BG_CARD, fg=FG_PRIMARY, font=FONT_UI, relief="flat",
            padx=10, pady=5, state="disabled", activebackground=BORDER, cursor="hand2")
        self._btn_pause.pack(side="left", padx=(0, 4))
        self._btn_stop = tk.Button(pb, text="■  Stop", command=self._stop,
            bg=BG_CARD, fg=FG_PRIMARY, font=FONT_UI, relief="flat",
            padx=10, pady=5, state="disabled", activebackground=BORDER, cursor="hand2")
        self._btn_stop.pack(side="left", padx=(0, 10))
        tk.Frame(pb, bg=BORDER, width=1).pack(side="left", fill="y", padx=8)
        self._obj_v = tk.BooleanVar(value=True)
        self._mot_v = tk.BooleanVar(value=True)
        tk.Checkbutton(pb, text="Objects", variable=self._obj_v,
            command=lambda: self._proc.set_detect_objects(self._obj_v.get()),
            bg=BG_PANEL, fg=FG_PRIMARY, selectcolor=BG_CARD,
            activebackground=BG_PANEL, font=FONT_UI).pack(side="left", padx=4)
        tk.Checkbutton(pb, text="Motion", variable=self._mot_v,
            command=lambda: self._proc.set_detect_motion(self._mot_v.get()),
            bg=BG_PANEL, fg=FG_PRIMARY, selectcolor=BG_CARD,
            activebackground=BG_PANEL, font=FONT_UI).pack(side="left", padx=4)
        tk.Frame(pb, bg=BORDER, width=1).pack(side="left", fill="y", padx=8)
        tk.Label(pb, text="Speed:", bg=BG_PANEL, fg=FG_MUTED, font=FONT_UI).pack(side="left")
        self._spd_v = tk.DoubleVar(value=1.0)
        spd = ttk.Combobox(pb, textvariable=self._spd_v,
                           values=[0.25, 0.5, 1.0, 2.0, 4.0],
                           width=5, style="Dark.TCombobox", state="readonly")
        spd.pack(side="left", padx=4)
        spd.set("1.0")
        self._rec_v = tk.StringVar(value="")
        tk.Label(pb, textvariable=self._rec_v, bg=BG_PANEL, fg=ACCENT_ALERT,
                 font=(FONT_UI[0], 10, "bold")).pack(side="right", padx=10)

        # Canvas — letterboxed, black bars fill unused space
        cw = tk.Frame(left, bg=BORDER, bd=1)
        cw.grid(row=2, column=0, sticky="nsew", pady=(6, 0))
        cw.rowconfigure(0, weight=1)
        cw.columnconfigure(0, weight=1)
        self._canvas = tk.Canvas(cw, bg="#000", highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._img_id = self._canvas.create_image(0, 0, anchor="nw", tags="feed")
        self._canvas.bind("<Configure>", self._on_canvas_resize)

        # Seek bar
        sr = ttk.Frame(left, style="Dark.TFrame")
        sr.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        sr.columnconfigure(0, weight=1)
        self._seek_v = tk.DoubleVar(value=0)
        self._seekbar = ttk.Scale(sr, from_=0, to=100, variable=self._seek_v,
                                  orient="horizontal", command=self._on_seek)
        self._seekbar.grid(row=0, column=0, sticky="ew")
        self._time_v = tk.StringVar(value="00:00 / 00:00")
        ttk.Label(sr, textvariable=self._time_v,
                  style="Muted.TLabel").grid(row=0, column=1, padx=(8, 0))

        # Fixed sidebar
        sb = tk.Frame(self, bg=BG_PANEL, width=self.SIDEBAR_W)
        sb.grid(row=0, column=1, sticky="nsew", padx=(4, 10), pady=10)
        sb.grid_propagate(False)
        sb.columnconfigure(0, weight=1)
        sb.rowconfigure(2, weight=1)

        ic = self._card(sb, "VIDEO INFO", 0)
        self._info_v = tk.StringVar(value="No video loaded")
        tk.Label(ic, textvariable=self._info_v, bg=BG_CARD, fg=FG_MUTED,
                 font=(FONT_UI[0], 9), wraplength=220, justify="left").pack(
                 anchor="w", padx=10, pady=(0, 8))

        cc = self._card(sb, "CLIPS SAVED", 1)
        self._saved_v = tk.StringVar(value="0 clips saved")
        tk.Label(cc, textvariable=self._saved_v, bg=BG_CARD, fg=FG_PRIMARY,
                 font=FONT_MONO).pack(anchor="w", padx=10, pady=(0, 4))
        tk.Button(cc, text="📋  View Last Report", command=self._view_report,
                  bg=BG_CARD, fg=ACCENT_INFO, font=(FONT_UI[0], 9),
                  relief="flat", cursor="hand2").pack(anchor="w", padx=8, pady=(0, 8))

        ec = self._card(sb, "EVENTS", 2, expand=True)
        ei = tk.Frame(ec, bg=BG_CARD)
        ei.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        ei.rowconfigure(0, weight=1)
        ei.columnconfigure(0, weight=1)
        self._ev = tk.Text(ei, bg=BG_DARK, fg=FG_MUTED, font=FONT_MONO,
                           wrap="word", relief="flat", bd=0, state="disabled", width=28)
        esb = tk.Scrollbar(ei, orient="vertical", command=self._ev.yview,
                           bg=BG_CARD, troughcolor=BG_DARK)
        self._ev.configure(yscrollcommand=esb.set)
        self._ev.grid(row=0, column=0, sticky="nsew")
        esb.grid(row=0, column=1, sticky="ns")

    def _card(self, parent, title, row, expand=False):
        o = tk.Frame(parent, bg=BG_CARD)
        o.grid(row=row, column=0, sticky="nsew" if expand else "ew", padx=8, pady=(6, 0))
        if expand:
            o.rowconfigure(1, weight=1)
            o.columnconfigure(0, weight=1)
        tk.Label(o, text=title, bg=BG_CARD, fg=FG_MUTED,
                 font=(FONT_UI[0], 8, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        tk.Frame(o, bg=BORDER, height=1).pack(fill="x", padx=10, pady=(0, 6))
        return o

    def _on_canvas_resize(self, event=None):
        if not self._run:
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
        self._canvas.create_text(cw // 2, ch // 2 - 14, tags="ph",
            text="No Video Loaded", fill=FG_MUTED, font=(FONT_UI[0], 15))
        self._canvas.create_text(cw // 2, ch // 2 + 14, tags="ph",
            text='Click "Browse…" to open a video file', fill=BORDER, font=FONT_UI)

    def on_show(self):
        if not self._run:
            self._canvas.after(50, self._draw_placeholder)

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv"),
                       ("All files", "*.*")])
        if path:
            self._stop()
            self._load(path)

    def _load(self, path):
        if self._cap:
            self._cap.release()
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            messagebox.showerror("Error", f"Cannot open:\n{path}")
            return
        self._cap     = cap
        self._clips   = 0
        self._was_rec = False
        self._proc.reset()
        fps   = cap.get(cv2.CAP_PROP_FPS) or 25
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fw    = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        fh    = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._total = total
        self._fps   = fps
        src = os.path.splitext(os.path.basename(path))[0][:20]
        self._rec = ClipRecorder(fw, fh, fps, source=src,
                                 on_saved=self._on_clip_saved)
        self._seekbar.configure(to=max(total - 1, 1))
        self._seek_v.set(0)
        self._path_v.set(os.path.basename(path))
        self._info_v.set(
            f"Resolution: {fw}×{fh}\n"
            f"FPS: {fps:.1f}\n"
            f"Frames: {total}\n"
            f"Duration: {format_duration(total / fps)}")
        self._time_v.set(f"00:00 / {format_duration(total / fps)}")
        self._saved_v.set("0 clips saved")
        self._rec_v.set("")
        self._btn_play.configure(state="normal")
        self._ev.configure(state="normal")
        self._ev.delete("1.0", "end")
        self._ev.configure(state="disabled")
        # Show first frame at correct aspect ratio
        ret, frame = cap.read()
        if ret:
            self._show_frame(frame)
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def _play(self):
        if not self._cap or self._run:
            return
        self._run   = True
        self._pause = False
        self._btn_play.configure(state="disabled")
        self._btn_pause.configure(state="normal")
        self._btn_stop.configure(state="normal")
        self._canvas.delete("ph")
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _toggle_pause(self):
        self._pause = not self._pause
        self._btn_pause.configure(text="▶  Resume" if self._pause else "⏸  Pause")

    def _stop(self):
        self._run   = False
        self._pause = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        if self._rec:
            self._rec.release()
        self._btn_play.configure(state="normal" if self._cap else "disabled")
        self._btn_pause.configure(state="disabled", text="⏸  Pause")
        self._btn_stop.configure(state="disabled")

    def _on_seek(self, _=None):
        if self._cap and not self._run:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, int(self._seek_v.get()))
            ret, f = self._cap.read()
            if ret:
                self._show_frame(f)

    def _loop(self):
        delay = 1.0 / max(self._fps * float(self._spd_v.get()), 1)
        while self._run:
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
            r   = self._proc.process(frame)

            if self._rec:
                self._rec.push(r["annotated"], dets=r["dets"], motion=r["motion"])
                if r["motion"]:
                    self._rec.trigger()
                elif self._was_rec and not r["motion"]:
                    self._rec.stop_recording()
                self._was_rec = r["motion"] or self._rec.is_recording

            self.after(0, self._update, r["annotated"], pos, r)
            time.sleep(max(delay, 0.001))

    def _show_frame(self, frame):
        cw = max(self._canvas.winfo_width(), 4)
        ch = max(self._canvas.winfo_height(), 4)
        imgtk = cv2_to_imgtk_fit(frame, cw, ch)
        self._canvas.imgtk = imgtk
        self._canvas.delete("ph")
        self._canvas.itemconfig(self._img_id, image=imgtk)

    def _update(self, frame, pos, r):
        self._show_frame(frame)
        cur = pos / (self._fps or 25)
        dur = self._total / (self._fps or 25)
        self._time_v.set(f"{format_duration(cur)} / {format_duration(dur)}")
        self._seek_v.set(pos)
        n = self._clips
        self._saved_v.set(f"{n} clip{'s' if n != 1 else ''} saved")
        self._rec_v.set("⏺  REC" if (self._rec and self._rec.is_recording) else "")
        if r["motion"] or r["dets"]:
            msg = f"[{format_duration(cur)}]"
            if r["motion"]:
                msg += " motion"
            names = [d["name"] for d in r["dets"]]
            if names:
                msg += " | " + ", ".join(names)
            self._ev.configure(state="normal")
            self._ev.insert("end", msg + "\n")
            self._ev.see("end")
            if int(self._ev.index("end-1c").split(".")[0]) > 600:
                self._ev.delete("1.0", "100.0")
            self._ev.configure(state="disabled")

    def _end(self):
        self._run = False
        if self._rec:
            self._rec.release()
        self._btn_play.configure(state="normal")
        self._btn_pause.configure(state="disabled")
        self._btn_stop.configure(state="disabled")
        self._rec_v.set("")
        n = self._clips
        self._saved_v.set(f"Done — {n} clip{'s' if n != 1 else ''} saved")

    def _view_report(self):
        reports = sorted(
            [f for f in os.listdir(CLIPS_DIR) if f.endswith("_report.json")],
            reverse=True)
        if not reports:
            messagebox.showinfo("No Reports",
                "No reports yet. Analyse a video with motion first.")
            return
        try:
            with open(os.path.join(CLIPS_DIR, reports[0])) as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        win = tk.Toplevel(self)
        win.title(f"Report — {reports[0]}")
        win.geometry("560x480")
        win.configure(bg=BG_DARK)
        tk.Label(win, text="📋  Incident Report", bg=BG_DARK, fg=FG_PRIMARY,
                 font=(FONT_UI[0], 13, "bold")).pack(anchor="w", padx=16, pady=(14, 2))
        tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=16)
        sc = tk.Frame(win, bg=BG_CARD)
        sc.pack(fill="x", padx=16, pady=(10, 6))
        for k, v in [("Source",   data.get("source", "")),
                     ("Clip",     data.get("clip", "")),
                     ("Started",  data.get("started", "")),
                     ("Ended",    data.get("ended", "")),
                     ("Duration", f"{data.get('duration_s', 0)}s"),
                     ("Events",   str(data.get("events", 0)))]:
            row = tk.Frame(sc, bg=BG_CARD)
            row.pack(fill="x", padx=10, pady=2)
            tk.Label(row, text=f"{k}:", bg=BG_CARD, fg=FG_MUTED,
                     font=(FONT_UI[0], 9), width=10, anchor="w").pack(side="left")
            tk.Label(row, text=v, bg=BG_CARD, fg=FG_PRIMARY,
                     font=(FONT_UI[0], 9)).pack(side="left")
        tk.Label(win, text="LOG", bg=BG_DARK, fg=FG_MUTED,
                 font=(FONT_UI[0], 8, "bold")).pack(anchor="w", padx=16, pady=(6, 2))
        tf = tk.Frame(win, bg=BG_DARK)
        tf.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        tf.rowconfigure(0, weight=1)
        tf.columnconfigure(0, weight=1)
        txt = tk.Text(tf, bg=BG_CARD, fg=FG_PRIMARY, font=FONT_MONO,
                      relief="flat", bd=0, wrap="none")
        sy = tk.Scrollbar(tf, orient="vertical", command=txt.yview,
                          bg=BG_CARD, troughcolor=BG_DARK)
        sx = tk.Scrollbar(tf, orient="horizontal", command=txt.xview,
                          bg=BG_CARD, troughcolor=BG_DARK)
        txt.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        txt.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        txt.insert("end",
            f"{'Frame':<8}{'Time':<22}{'Motion':<8}Detections\n" + "─" * 70 + "\n")
        for ev in data.get("log", []):
            d = ", ".join(
                f"{x['name']}({x['conf']:.0%})" for x in ev.get("dets", [])) or "—"
            txt.insert("end",
                f"{ev['frame']:<8}{ev['time']:<22}"
                f"{'yes' if ev['motion'] else 'no':<8}{d}\n")
        txt.configure(state="disabled")

    def _on_clip_saved(self):
        self._clips += 1
        n = self._clips
        self.after(0, self._saved_v.set, f"{n} clip{'s' if n != 1 else ''} saved")

    def on_hide(self):
        self._stop()