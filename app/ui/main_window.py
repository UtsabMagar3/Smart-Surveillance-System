# Main Window UI Module
import tkinter as tk
from tkinter import ttk
from app.utils.config import *
from app.ui.live_camera_tab  import LiveCameraTab
from app.ui.import_video_tab import ImportVideoTab
from app.ui.saved_clips_tab  import SavedClipsTab


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.minsize(900, 600)
        self.configure(bg=BG_DARK)
        self._styles()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Dark.TFrame",   background=BG_DARK)
        s.configure("Panel.TFrame",  background=BG_PANEL)
        s.configure("Card.TFrame",   background=BG_CARD)
        s.configure("TLabel",              background=BG_DARK,  foreground=FG_PRIMARY, font=FONT_UI)
        s.configure("Muted.TLabel",        background=BG_DARK,  foreground=FG_MUTED,   font=FONT_UI)
        s.configure("SectionHead.TLabel",  background=BG_CARD,  foreground=FG_MUTED,   font=(FONT_UI[0], 9, "bold"))
        s.configure("TButton",      background=BG_CARD, foreground=FG_PRIMARY, font=FONT_UI, borderwidth=0, focusthickness=0, padding=6)
        s.map("TButton",            background=[("active", BORDER), ("disabled", BG_PANEL)], foreground=[("disabled", FG_MUTED)])
        s.configure("Accent.TButton", background=ACCENT, foreground="#fff", font=(FONT_UI[0], 10, "bold"), padding=6)
        s.map("Accent.TButton",     background=[("active", "#2ea043"), ("disabled", BG_PANEL)])
        s.configure("Dark.TButton", background=BG_CARD, foreground=FG_PRIMARY, font=FONT_UI, padding=6)
        s.map("Dark.TButton",       background=[("active", BORDER), ("disabled", BG_PANEL)])
        s.configure("Dark.TCheckbutton", background=BG_PANEL, foreground=FG_PRIMARY, font=FONT_UI)
        s.map("Dark.TCheckbutton",  background=[("active", BG_PANEL)], foreground=[("active", FG_PRIMARY)])
        s.configure("TNotebook",    background=BG_DARK, borderwidth=0)
        s.configure("TNotebook.Tab", background=BG_PANEL, foreground=FG_MUTED, font=(FONT_UI[0], 11), padding=(18, 9))
        s.map("TNotebook.Tab",      background=[("selected", BG_DARK)], foreground=[("selected", FG_PRIMARY)])
        s.configure("TScrollbar",   background=BG_CARD, troughcolor=BG_DARK, borderwidth=0, arrowsize=12)
        s.map("TScrollbar",         background=[("active", BORDER)])
        s.configure("Dark.TCombobox", background=BG_CARD, foreground=FG_PRIMARY, fieldbackground=BG_CARD, arrowcolor=FG_MUTED)
        s.map("Dark.TCombobox",     fieldbackground=[("readonly", BG_CARD)], foreground=[("readonly", FG_PRIMARY)])
        s.configure("TScale",       background=BG_DARK, troughcolor=BG_CARD)

    def _build(self):
        hdr = tk.Frame(self, bg=BG_PANEL, height=44)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🔍  Smart Surveillance System", bg=BG_PANEL, fg=FG_PRIMARY,
                 font=(FONT_UI[0], 13, "bold")).pack(side="left", padx=14, pady=10)
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True)

        self._t1 = LiveCameraTab( self._nb, style="Dark.TFrame")
        self._t2 = ImportVideoTab(self._nb, style="Dark.TFrame")
        self._t3 = SavedClipsTab( self._nb, style="Dark.TFrame")
        self._nb.add(self._t1, text="  📷  Live Camera  ")
        self._nb.add(self._t2, text="  🎬  Import Video  ")
        self._nb.add(self._t3, text="  💾  Saved Clips  ")
        self._nb.bind("<<NotebookTabChanged>>", self._tab_changed)

    def _tab_changed(self, _=None):
        idx  = self._nb.index(self._nb.select())
        tabs = [self._t1, self._t2, self._t3]
        for i, t in enumerate(tabs):
            if i == idx and hasattr(t, "on_show"): t.on_show()
            if i != idx and hasattr(t, "on_hide"): t.on_hide()

    def _close(self):
        for t in (self._t1, self._t2, self._t3):
            if hasattr(t, "on_hide"): t.on_hide()
        self.destroy()
