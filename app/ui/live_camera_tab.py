# Live Camera Tab UI Module
import tkinter as tk
from tkinter import ttk, messagebox
import cv2, threading, time
from app.core.video_processor import VideoProcessor
from app.core.clip_recorder   import ClipRecorder
from app.utils.config         import *
from app.utils.helpers        import cv2_to_imgtk_fit, now_str


class _Tip:
    def __init__(self, w, text):
        self._w, self._text, self._win = w, text, None
        w.bind("<Enter>", self._show)
        w.bind("<Leave>", self._hide)

    def _show(self, _=None):
        x = self._w.winfo_rootx() + 20
        y = self._w.winfo_rooty() + self._w.winfo_height() + 4
        self._win = tw = tk.Toplevel(self._w)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self._text, justify="left", background="#2d333b",
                 foreground="#cdd9e5", relief="flat", bd=1, padx=8, pady=5,
                 font=("Segoe UI", 9), wraplength=280).pack()

    def _hide(self, _=None):
        if self._win:
            self._win.destroy()
            self._win = None


class LiveCameraTab(ttk.Frame):
    SIDEBAR_W = 260

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.configure(style="Dark.TFrame")
        self._cap     = None
        self._run     = False
        self._thread  = None
        self._proc    = VideoProcessor()
        self._rec     = None
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
        left.rowconfigure(1, weight=1)

        tb = tk.Frame(left, bg=BG_PANEL, pady=6)
        tb.grid(row=0, column=0, sticky="ew")

        cg = tk.Frame(tb, bg=BG_PANEL)
        cg.pack(side="left", padx=(10, 0))
        tk.Label(cg, text="Camera Index", bg=BG_PANEL, fg=FG_PRIMARY,
                 font=(FONT_UI[0], 10, "bold")).pack(anchor="w")
        tk.Label(cg, text="0 = built-in webcam,  1/2… = USB camera",
                 bg=BG_PANEL, fg=FG_MUTED, font=(FONT_UI[0], 8)).pack(anchor="w")
        self._cam_var = tk.IntVar(value=0)
        sp = tk.Spinbox(cg, from_=0, to=9, textvariable=self._cam_var, width=3,
                        bg=BG_CARD, fg=FG_PRIMARY, insertbackground=FG_PRIMARY,
                        relief="flat", buttonbackground=BG_CARD, font=FONT_UI)
        sp.pack(anchor="w", pady=(2, 0))
        _Tip(sp, "0 = built-in webcam (most common)\n1, 2… = USB cameras\nTry 0 first.")

        tk.Frame(tb, bg=BORDER, width=1).pack(side="left", fill="y", padx=12)

        self._btn_start = tk.Button(tb, text="▶  Start", command=self._start,
            bg=ACCENT, fg="#fff", font=(FONT_UI[0], 10, "bold"),
            relief="flat", padx=14, pady=6, activebackground="#2ea043", cursor="hand2")
        self._btn_start.pack(side="left", padx=(0, 6))
        self._btn_stop = tk.Button(tb, text="■  Stop", command=self._stop,
            bg=BG_CARD, fg=FG_PRIMARY, font=FONT_UI, relief="flat",
            padx=14, pady=6, state="disabled", activebackground=BORDER, cursor="hand2")
        self._btn_stop.pack(side="left")

        tk.Frame(tb, bg=BORDER, width=1).pack(side="left", fill="y", padx=12)

        tog = tk.Frame(tb, bg=BG_PANEL)
        tog.pack(side="left")
        self._obj_var = tk.BooleanVar(value=True)
        self._mot_var = tk.BooleanVar(value=True)

        or_ = tk.Frame(tog, bg=BG_PANEL)
        or_.pack(anchor="w")
        obj_cb = tk.Checkbutton(or_, text="Objects", variable=self._obj_var,
            command=lambda: self._proc.set_detect_objects(self._obj_var.get()),
            bg=BG_PANEL, fg=FG_PRIMARY, selectcolor=BG_CARD, activebackground=BG_PANEL,
            font=(FONT_UI[0], 10, "bold"), cursor="hand2")
        obj_cb.pack(side="left")
        tk.Label(or_, text="— YOLOv8: identify person / vehicle / animal",
                 bg=BG_PANEL, fg=FG_MUTED, font=(FONT_UI[0], 8)).pack(side="left", padx=4)
        _Tip(obj_cb, "Object Detection (YOLOv8n)\nLabels each detected object with its category.\nPerson=blue  Vehicle=cyan  Animal=green  Other=grey")

        mr = tk.Frame(tog, bg=BG_PANEL)
        mr.pack(anchor="w")
        mot_cb = tk.Checkbutton(mr, text="Motion", variable=self._mot_var,
            command=lambda: self._proc.set_detect_motion(self._mot_var.get()),
            bg=BG_PANEL, fg=FG_PRIMARY, selectcolor=BG_CARD, activebackground=BG_PANEL,
            font=(FONT_UI[0], 10, "bold"), cursor="hand2")
        mot_cb.pack(side="left")
        tk.Label(mr, text="— MOG2: detect movement, auto-save clips",
                 bg=BG_PANEL, fg=FG_MUTED, font=(FONT_UI[0], 8)).pack(side="left", padx=4)
        _Tip(mot_cb, "Motion Detection (MOG2 background subtraction)\n"
             "Detects moving regions — triggers auto clip recording.\n"
             f"Pre-buffer: {CLIP_PRE_SECONDS}s  Post-buffer: {CLIP_POST_SECONDS}s")

        self._rec_lbl = tk.Label(tb, text="", bg=BG_PANEL, fg=ACCENT_ALERT,
                                  font=(FONT_UI[0], 11, "bold"))
        self._rec_lbl.pack(side="right", padx=12)

        # Canvas — black bg, placeholder drawn on Configure so coords are always correct
        cw = tk.Frame(left, bg=BORDER, bd=1)
        cw.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        cw.rowconfigure(0, weight=1)
        cw.columnconfigure(0, weight=1)
        self._canvas = tk.Canvas(cw, bg="#000", highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        # Pre-create image item once — updated via itemconfig, never recreated
        self._img_id = self._canvas.create_image(0, 0, anchor="nw", tags="feed")
        # Draw placeholder after layout settles
        self._canvas.bind("<Configure>", self._on_canvas_resize)

        self._status = tk.StringVar(value="Idle — press  ▶ Start  to begin")
        tk.Label(left, textvariable=self._status, bg=BG_DARK, fg=FG_MUTED,
                 font=(FONT_UI[0], 9)).grid(row=2, column=0, sticky="w", pady=(4, 0))

        # Fixed-width sidebar
        sb = tk.Frame(self, bg=BG_PANEL, width=self.SIDEBAR_W)
        sb.grid(row=0, column=1, sticky="nsew", padx=(4, 10), pady=10)
        sb.grid_propagate(False)
        sb.columnconfigure(0, weight=1)
        sb.rowconfigure(3, weight=1)

        sc = self._card(sb, "LIVE STATS", 0)
        self._v_fps = tk.StringVar(value="FPS:         –")
        self._v_mot = tk.StringVar(value="Motion:      –")
        self._v_obj = tk.StringVar(value="Objects:     –")
        self._v_cl  = tk.StringVar(value="Clips saved: 0")
        for v in (self._v_fps, self._v_mot, self._v_obj, self._v_cl):
            tk.Label(sc, textvariable=v, bg=BG_CARD, fg=FG_PRIMARY,
                     font=FONT_MONO, anchor="w").pack(fill="x", padx=10, pady=2)
        tk.Frame(sc, bg=BG_CARD, height=4).pack()

        lc = self._card(sb, "COLOUR LEGEND", 1)
        for col, lbl in [("#5050FF", "Person"), ("#00C8FF", "Vehicle"),
                          ("#00E650", "Animal"), ("#B4B4B4", "Other"),
                          ("#64FF00", "Motion region")]:
            r = tk.Frame(lc, bg=BG_CARD)
            r.pack(fill="x", padx=10, pady=2)
            tk.Frame(r, bg=col, width=13, height=13).pack(side="left")
            tk.Label(r, text=f"  {lbl}", bg=BG_CARD, fg=FG_PRIMARY,
                     font=(FONT_UI[0], 9)).pack(side="left")
        tk.Frame(lc, bg=BG_CARD, height=4).pack()

        log = self._card(sb, "DETECTION LOG", 3, expand=True)
        li = tk.Frame(log, bg=BG_CARD)
        li.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        li.rowconfigure(0, weight=1)
        li.columnconfigure(0, weight=1)
        self._log = tk.Text(li, bg=BG_DARK, fg=FG_MUTED, font=FONT_MONO,
                            wrap="word", relief="flat", bd=0, state="disabled", width=28)
        lsb = tk.Scrollbar(li, orient="vertical", command=self._log.yview,
                           bg=BG_CARD, troughcolor=BG_DARK)
        self._log.configure(yscrollcommand=lsb.set)
        self._log.grid(row=0, column=0, sticky="nsew")
        lsb.grid(row=0, column=1, sticky="ns")

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
            text="No Camera Feed", fill=FG_MUTED, font=(FONT_UI[0], 15))
        self._canvas.create_text(cw // 2, ch // 2 + 14, tags="ph",
            text="Select Camera Index and press  ▶ Start", fill=BORDER, font=FONT_UI)

    def on_show(self):
        if not self._run:
            self._canvas.after(50, self._draw_placeholder)

    def _start(self):
        idx = self._cam_var.get()
        cap = cv2.VideoCapture(idx, cv2.CAP_ANY)
        if not cap.isOpened():
            messagebox.showerror("Camera Not Found",
                f"Cannot open camera {idx}.\n0 = built-in, 1/2… = USB.")
            return
        self._cap     = cap
        self._run     = True
        self._clips   = 0
        self._was_rec = False
        fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._rec = ClipRecorder(fw, fh, source="live",
                                 on_saved=self._on_clip_saved)
        self._btn_start.configure(state="disabled")
        self._btn_stop.configure(state="normal")
        self._canvas.delete("ph")
        self._canvas.itemconfig(self._img_id, image="")
        self._status.set(f"Live — Camera {idx}  ({fw}×{fh})")
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _stop(self):
        self._run = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        if self._cap:
            self._cap.release()
            self._cap = None
        if self._rec:
            self._rec.release()
            self._rec = None
        self._btn_start.configure(state="normal")
        self._btn_stop.configure(state="disabled")
        self._rec_lbl.configure(text="")
        self._status.set("Stopped")
        self._draw_placeholder()

    def _loop(self):
        prev = time.time()
        while self._run and self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if not ret:
                break
            r = self._proc.process(frame)

            if self._rec:
                self._rec.push(r["annotated"], dets=r["dets"], motion=r["motion"])
                if r["motion"]:
                    self._rec.trigger()
                elif self._was_rec and not r["motion"]:
                    self._rec.stop_recording()
                self._was_rec = r["motion"] or self._rec.is_recording

            now = time.time()
            fps = 1.0 / max(now - prev, 1e-9)
            prev = now
            self.after(0, self._update, r["annotated"], r, fps)
            time.sleep(0.001)

    def _update(self, frame, r, fps):
        if not self._run:
            return
        cw = max(self._canvas.winfo_width(), 4)
        ch = max(self._canvas.winfo_height(), 4)
        imgtk = cv2_to_imgtk_fit(frame, cw, ch)
        self._canvas.imgtk = imgtk
        self._canvas.itemconfig(self._img_id, image=imgtk)

        self._v_fps.set(f"FPS:         {fps:.1f}")
        self._v_mot.set(f"Motion:      {'YES 🔴' if r['motion'] else 'no'}")
        names = ", ".join({d['name'] for d in r['dets']}) or "none"
        self._v_obj.set(f"Objects:     {names[:22]}")
        self._v_cl.set(f"Clips saved: {self._clips}")
        self._rec_lbl.configure(
            text="⏺  REC" if (self._rec and self._rec.is_recording) else "")

        if r["dets"]:
            self._log_add(
                f"[{now_str()}] " +
                ", ".join(f"{d['group']}:{d['name']}" for d in r["dets"][:3]) + "\n")
        elif r["motion"]:
            self._log_add(f"[{now_str()}] Motion detected\n")

    def _log_add(self, msg):
        self._log.configure(state="normal")
        self._log.insert("end", msg)
        self._log.see("end")
        if int(self._log.index("end-1c").split(".")[0]) > 500:
            self._log.delete("1.0", "100.0")
        self._log.configure(state="disabled")

    def _on_clip_saved(self):
        self._clips += 1
        self.after(0, self._v_cl.set, f"Clips saved: {self._clips}")

    def on_hide(self):
        self._stop()