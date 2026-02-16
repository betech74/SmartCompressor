import os
import sys
import logging
import traceback
from datetime import datetime
import time
import threading
import json
import config
from tkinter import (
    Tk,
    Toplevel,
    Frame,
    Label,
    Text,
    BooleanVar,
    IntVar,
    StringVar,
    X,
    Y,
    BOTH,
    TOP,
    BOTTOM,
    LEFT,
    RIGHT,
    W,
    END,
    HORIZONTAL,
)
from tkinter import filedialog, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from scanner import scan_folder
from estimations import estimate_size
from dispatcher import dispatch
from gpu import has_nvenc
from utils.paths import settings_path, bundled_path, log_dir
from config import SUPPORTED_IMAGE, SUPPORTED_VIDEO, SUPPORTED_TEXT, SUPPORTED_PDF
from config import VERSION, COPYRIGHT_YEAR
from utils.humanize import human
from setup_check import run_all_checks

def configure_dpi_awareness():
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

def load_translations(lang: str) -> dict:
    path = bundled_path(f"assets/locales/{lang}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def tr(i18n: dict, key: str, **kwargs) -> str:
    text = i18n.get(key, key)
    try:
        return text.format(**kwargs)
    except Exception:
        return text

class AppDialog(Toplevel):
    def __init__(self, parent, title: str, message: str, kind: str = "info", ok_text: str = "OK", log_folder: str | None = None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.configure(bg=THEME["bg"])
        apply_window_theme(self)

        self.transient(parent)
        self.grab_set()
        log_event(f"Dialog opened: kind={kind}")

        header = Frame(self, bg=THEME["bg"], height=44)
        header.pack(fill=X, side=TOP)
        Label(
            header,
            text=title,
            font=("Segoe UI Variable", 12, "bold"),
            fg=THEME["text"],
            bg=THEME["bg"],
        ).pack(pady=(10, 8))
        Frame(self, bg=THEME["border"], height=1).pack(fill=X, pady=(0, 10))

        body = Frame(self, bg=THEME["bg"])
        body.pack(fill=BOTH, expand=True, padx=16, pady=(0, 6))

        color = THEME["text"]
        if kind == "error":
            color = THEME["danger"]
        elif kind == "warning":
            color = THEME["log_warn"]
        elif kind == "success":
            color = THEME["log_success"]

        Label(
            body,
            text=message,
            font=("Segoe UI Variable", 10),
            fg=color,
            bg=THEME["bg"],
            justify=LEFT,
            wraplength=360,
        ).pack(anchor=W)

        footer = Frame(self, bg=THEME["bg"])
        footer.pack(fill=X, padx=16, pady=(8, 12))

        if log_folder:
            def open_logs():
                try:
                    if os.name == "nt":
                        os.startfile(log_folder)
                    else:
                        import subprocess
                        subprocess.Popen(["xdg-open", log_folder])
                    log_event(f"Open logs folder: {log_folder}")
                except Exception:
                    log_event(f"Failed to open logs folder: {log_folder}")
                    pass
            ttk.Button(
                footer,
                text=tr(load_translations(config.LANG), "btn_open_logs"),
                command=open_logs,
                width=14,
                style="Uiverse.TButton",
            ).pack(side=LEFT)

        ttk.Button(
            footer,
            text=ok_text,
            command=self.destroy,
            width=10,
            style="Uiverse.Primary.TButton",
        ).pack(side=RIGHT)

        self.update_idletasks()
        apply_window_theme(self)
        self._center_over_parent(parent)

    def _center_over_parent(self, parent):
        try:
            self.update_idletasks()
            if parent is None:
                return
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            w = self.winfo_width()
            h = self.winfo_height()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
            self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        except Exception:
            pass

THEMES = {
    "light": {
        "bg": "#FFFFFF",
        "surface": "#FFFFFF",
        "primary": "#1E5BFF",
        "primary_hover": "#184AE0",
        "text": "#111827",
        "muted": "#6B7280",
        "border": "#D1D5DB",
        "shadow_hint": "#E5E7EB",
        "danger": "#E53935",
        "log_info": "#1E5BFF",
        "log_success": "#1B7F3A",
        "log_warn": "#B45309",
        "log_error": "#B42318",
        "titlebar_dark": False,
    },
    "dark": {
        "bg": "#0B0F14",
        "surface": "#0F141B",
        "primary": "#3B82F6",
        "primary_hover": "#2563EB",
        "text": "#E5E7EB",
        "muted": "#9CA3AF",
        "border": "#1F2937",
        "shadow_hint": "#111827",
        "danger": "#EF4444",
        "hover": "#151B23",
        "hover_border": "#2A3545",
        "log_info": "#60A5FA",
        "log_success": "#34D399",
        "log_warn": "#F59E0B",
        "log_error": "#F87171",
        "titlebar_dark": True,
    },
}

THEME = THEMES.get(config.THEME, THEMES["light"])

LOG_DIR = log_dir("SmartCompressor")
LOG_FILE = LOG_DIR / "app.log"
_current_app = None


def init_logging():
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("")
    except Exception:
        pass
    logging.basicConfig(
        filename=str(LOG_FILE),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logging.info("Application started")


def log_event(message: str):
    try:
        logging.info(message)
    except Exception:
        pass


def handle_exception(exctype, value, tb):
    logging.critical("Unhandled exception", exc_info=(exctype, value, tb))
    try:
        stamp = datetime.now().strftime("%d_%m_%Y-%H_%M_%S")
        crash_file = LOG_DIR / f"CRASH-{stamp}.log"
        with open(crash_file, "w", encoding="utf-8") as f:
            f.write(f"=== Crash Traceback ({datetime.now().isoformat()}) ===\n")
            f.write("".join(traceback.format_exception(exctype, value, tb)))
            f.write(f"\n=== app.log ({datetime.now().isoformat()}) ===\n")
            try:
                if LOG_FILE.exists():
                    f.write(LOG_FILE.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                f.write("(Failed to read app.log)\n")
    except Exception:
        crash_file = LOG_FILE
    msg = tr(
        load_translations(config.LANG),
        "crash_message",
        path=str(crash_file),
        filename=os.path.basename(str(crash_file)),
    )
    title = tr(load_translations(config.LANG), "crash_title")
    try:
        if _current_app and _current_app.winfo_exists():
            _current_app.show_dialog(title, msg, "error", log_folder=str(LOG_DIR))
            return
    except Exception:
        pass
    try:
        root = Tk()
        root.withdraw()
        AppDialog(
            root,
            title,
            msg,
            "error",
            ok_text=tr(load_translations(config.LANG), "btn_ok"),
            log_folder=str(LOG_DIR),
        )
        root.destroy()
    except Exception:
        pass

def apply_ttk_theme(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    default_font = ("Segoe UI Variable", 10)
    fallback_font = ("Segoe UI", 10)
    try:
        style.configure(".", font=default_font)
    except Exception:
        style.configure(".", font=fallback_font)

    style.configure("TFrame", background=THEME["bg"])
    style.configure("TLabel", background=THEME["bg"], foreground=THEME["text"])
    style.configure("Muted.TLabel", background=THEME["bg"], foreground=THEME["muted"])

    style.configure("Card.TFrame", background=THEME["surface"])
    style.configure("CardInner.TFrame", background=THEME["surface"])

    style.configure(
        "TCheckbutton",
        background=THEME["bg"],
        foreground=THEME["text"],
        focuscolor=THEME["primary"],
    )

    style.configure(
        "Blue.Horizontal.TProgressbar",
        troughcolor=THEME["shadow_hint"],
        background=THEME["primary"],
        bordercolor=THEME["border"],
        lightcolor=THEME["primary"],
        darkcolor=THEME["primary"],
    )

    style.configure(
        "TCombobox",
        fieldbackground=THEME["surface"],
        background=THEME["surface"],
        foreground=THEME["text"],
        arrowcolor=THEME["text"],
        bordercolor=THEME["border"],
    )
    style.map(
        "TCombobox",
        fieldbackground=[
            ("readonly", THEME["surface"]),
            ("active", THEME.get("hover", THEME["surface"])),
        ],
        foreground=[
            ("readonly", THEME["text"]),
        ],
    )
    style.configure(
        "TScale",
        troughcolor=THEME["surface"],
        background=THEME["bg"],
    )

    style.configure(
        "Vertical.TScrollbar",
        background=THEME.get("hover", THEME["shadow_hint"]),
        troughcolor=THEME["surface"],
        bordercolor=THEME["surface"],
        lightcolor=THEME.get("hover_border", THEME["shadow_hint"]),
        darkcolor=THEME.get("hover_border", THEME["shadow_hint"]),
        arrowsize=10,
        width=10,
    )
    style.map(
        "Vertical.TScrollbar",
        background=[
            ("active", THEME.get("hover", THEME["shadow_hint"])),
            ("pressed", THEME.get("hover_border", THEME["shadow_hint"])),
        ],
        lightcolor=[
            ("active", THEME.get("hover_border", THEME["shadow_hint"])),
            ("pressed", THEME.get("hover_border", THEME["shadow_hint"])),
        ],
        darkcolor=[
            ("active", THEME.get("hover_border", THEME["shadow_hint"])),
            ("pressed", THEME.get("hover_border", THEME["shadow_hint"])),
        ],
        troughcolor=[
            ("active", THEME["surface"]),
        ],
    )

    style.configure(
        "Uiverse.TButton",
        padding=(14, 8),
        background=THEME["surface"],
        foreground=THEME["text"],
        bordercolor=THEME["border"],
        focusthickness=2,
        focuscolor=THEME["primary"],
    )
    style.map(
        "Uiverse.TButton",
        background=[
            ("pressed", THEME["shadow_hint"]),
            ("active",  THEME.get("hover", "#EEF1F6")),
        ],
        bordercolor=[
            ("pressed", THEME.get("hover_border", "#BFC7D4")),
            ("active",  THEME.get("hover_border", "#C8D2E1")),
        ],
        foreground=[
            ("disabled", THEME["muted"]),
        ],
    )

    style.configure(
        "Uiverse.Primary.TButton",
        padding=(14, 8),
        background=THEME["primary"],
        foreground="white",
        bordercolor=THEME["primary_hover"],
        focusthickness=2,
        focuscolor=THEME["primary"],
    )
    style.map(
        "Uiverse.Primary.TButton",
        background=[
            ("pressed", "#1443CC"),
            ("active",  THEME["primary_hover"]),
        ],
        bordercolor=[
            ("pressed", "#123BB3"),
            ("active",  "#173FD0"),
        ],
        foreground=[
            ("disabled", "#FFFFFF"),
        ],
    )

    style.map(
        "TCheckbutton",
        background=[
            ("active", THEME.get("hover", THEME["bg"])),
        ],
    )

def apply_window_theme(root):
    if os.name != "nt":
        return
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = 1 if THEME.get("titlebar_dark") else 0
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(ctypes.c_int(value)),
            ctypes.sizeof(ctypes.c_int),
        )
    except Exception:
        pass

class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self._apply_scaling()
        try:
            self.iconbitmap(default=str(bundled_path("assets/sc.ico")))
        except Exception:
            pass
        apply_window_theme(self)
        self.lang = config.LANG
        self._i18n = load_translations(self.lang)
        self._i18n_widgets = []
        self.title(self.t("app_title"))
        self.geometry("950x780")
        self.state("zoomed")

        apply_ttk_theme(self)
        self.configure(bg=THEME["bg"])

        self.src_dir = ""
        self.dst_dir = ""
        self.files_to_process = []
        self.log_color_enabled = config.LOG_COLOR
        self._border_frames = []
        self._bg_frames = []
        self._settings_apply_theme = None
        self._settings_window = None

        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self.on_drop)

        self.frame_header = Frame(self, bg=THEME["bg"], height=48)
        self.frame_header.pack(fill=X, side=TOP)
        self._bg_frames.append(self.frame_header)

        self.header_title = Label(
            self.frame_header,
            font=("Segoe UI Variable", 18, "bold"),
            fg=THEME["text"],
            bg=THEME["bg"]
        )
        self.header_title.pack(pady=(10, 6))
        self._register_text(self.header_title, "header_title")

        header_sep = Frame(self, bg=THEME["border"], height=1)
        header_sep.pack(fill=X, pady=(0, 6))
        self._border_frames.append(header_sep)

        self.frame_footer = Frame(self, bg=THEME["bg"], height=26)
        self.frame_footer.pack(fill=X, side=BOTTOM)
        self._bg_frames.append(self.frame_footer)

        footer_sep = Frame(self.frame_footer, bg=THEME["border"], height=1)
        footer_sep.pack(fill=X, side=TOP)
        self._border_frames.append(footer_sep)

        self.footer_label = Label(
            self.frame_footer,
            font=("Segoe UI Variable", 9),
            fg=THEME["muted"],
            bg=THEME["bg"]
        )
        self.footer_label.pack(pady=4)

        frame_options_outer = ttk.Frame(self, style="TFrame")
        frame_options_outer.pack(pady=(0, 6), padx=16, fill=X)

        frame_options_border = Frame(frame_options_outer, bg=THEME["border"])
        frame_options_border.pack(fill=X)
        self._border_frames.append(frame_options_border)

        frame_options = ttk.Frame(frame_options_border, style="Card.TFrame")
        frame_options.pack(fill=X, padx=1, pady=1)

        inner_options = ttk.Frame(frame_options, style="CardInner.TFrame")
        inner_options.pack(fill=X, padx=10, pady=8)

        self.auto_analyse_var = BooleanVar(value=False)
        self.auto_analyse_var.trace_add("write", lambda *_: log_event(f"Auto analyze toggled: {self.auto_analyse_var.get()}"))

        btn_analyze = ttk.Button(
            inner_options,
            text=self.t("btn_analyze"),
            command=lambda: self._debounced("btn_analyze") and self.analyse(),
            width=12,
            style="Uiverse.Primary.TButton"
        )
        btn_analyze.grid(row=0, column=0, padx=6, pady=4, sticky=W)
        self._register_text(btn_analyze, "btn_analyze")

        chk_auto_analyze = ttk.Checkbutton(
            inner_options,
            text=self.t("chk_auto_analyze"),
            variable=self.auto_analyse_var
        )
        chk_auto_analyze.grid(row=0, column=1, padx=6, pady=4, sticky=W)
        self._register_text(chk_auto_analyze, "chk_auto_analyze")

        btn_destination = ttk.Button(
            inner_options,
            text=self.t("btn_destination"),
            command=lambda: self._debounced("btn_destination") and self.select_destination(),
            width=12,
            style="Uiverse.TButton"
        )
        btn_destination.grid(row=1, column=0, padx=6, pady=4, sticky=W)
        self._register_text(btn_destination, "btn_destination")

        self.dst_label = ttk.Label(
            inner_options,
            text=self.t("dst_not_selected"),
            style="Muted.TLabel"
        )
        self.dst_label.grid(row=1, column=1, padx=6, pady=4, sticky=W)

        btn_compress = ttk.Button(
            inner_options,
            text=self.t("btn_compress"),
            command=lambda: self._debounced("btn_compress") and threading.Thread(target=self.compress_thread).start(),
            width=12,
            style="Uiverse.Primary.TButton"
        )
        btn_compress.grid(row=2, column=0, padx=6, pady=(8, 4), sticky=W)
        self._register_text(btn_compress, "btn_compress")

        btn_settings = ttk.Button(
            inner_options,
            text=self.t("btn_settings"),
            command=self.open_settings_window,
            width=12,
            style="Uiverse.TButton"
        )
        btn_settings.grid(row=3, column=0, padx=6, pady=4, sticky=W)
        self._register_text(btn_settings, "btn_settings")

        frame_drag_outer = ttk.Frame(self, style="TFrame")
        frame_drag_outer.pack(pady=0, padx=16, fill=X)

        frame_drag_border = Frame(frame_drag_outer, bg=THEME["border"])
        frame_drag_border.pack(fill=X)
        self._border_frames.append(frame_drag_border)

        frame_drag_info = ttk.Frame(frame_drag_border, style="Card.TFrame")
        frame_drag_info.pack(fill=X, padx=1, pady=1)

        inner_drag = ttk.Frame(frame_drag_info, style="CardInner.TFrame")
        inner_drag.pack(fill=X, padx=10, pady=8)

        lbl_drag_hint = ttk.Label(
            inner_drag,
            text=self.t("drag_drop_hint"),
            style="Muted.TLabel"
        )
        lbl_drag_hint.pack(anchor=W, pady=(0, 6))
        self._register_text(lbl_drag_hint, "drag_drop_hint")

        btn_source = ttk.Button(
            inner_drag,
            text=self.t("btn_source"),
            command=lambda: self._debounced("btn_source") and self.select_folder(),
            width=12,
            style="Uiverse.TButton"
        )
        btn_source.pack(anchor=W)
        self._register_text(btn_source, "btn_source")

        frame_progress_outer = ttk.Frame(self, style="TFrame")
        frame_progress_outer.pack(pady=6, padx=16, fill=X)

        frame_progress_border = Frame(frame_progress_outer, bg=THEME["border"])
        frame_progress_border.pack(fill=X)
        self._border_frames.append(frame_progress_border)

        frame_progress = ttk.Frame(frame_progress_border, style="Card.TFrame")
        frame_progress.pack(fill=X, padx=1, pady=1)

        inner_progress = ttk.Frame(frame_progress, style="CardInner.TFrame")
        inner_progress.pack(fill=X, padx=10, pady=8)

        self.lbl_progress_global = ttk.Label(inner_progress, text=self.t("progress_global"), style="Muted.TLabel")
        self.lbl_progress_global.pack(anchor=W)
        self._register_text(self.lbl_progress_global, "progress_global")
        self.progress_global = ttk.Progressbar(
            inner_progress,
            mode="determinate",
            style="Blue.Horizontal.TProgressbar"
        )
        self.progress_global.pack(fill=X, expand=True, pady=(6, 4))
        self.progress_global_label = ttk.Label(inner_progress, text="0%", style="Muted.TLabel")
        self.progress_global_label.pack(anchor=W)

        frame_file_outer = ttk.Frame(self, style="TFrame")
        frame_file_outer.pack(pady=(0, 6), padx=16, fill=X)

        frame_file_border = Frame(frame_file_outer, bg=THEME["border"])
        frame_file_border.pack(fill=X)
        self._border_frames.append(frame_file_border)

        self.frame_prog_file = ttk.Frame(frame_file_border, style="Card.TFrame")
        self.frame_prog_file.pack(fill=X, padx=1, pady=1)

        inner_file = ttk.Frame(self.frame_prog_file, style="CardInner.TFrame")
        inner_file.pack(fill=X, padx=10, pady=8)

        self.lbl_prog_file = ttk.Label(inner_file, text=self.t("progress_file"), style="Muted.TLabel")
        self.lbl_prog_file.pack(anchor=W)
        self._register_text(self.lbl_prog_file, "progress_file")

        self.progress_file = ttk.Progressbar(
            inner_file,
            mode="determinate",
            style="Blue.Horizontal.TProgressbar"
        )
        self.progress_file.pack(fill=X, expand=True, pady=(6, 4))

        self.progress_file_label = ttk.Label(inner_file, text="0%", style="Muted.TLabel")
        self.progress_file_label.pack(anchor=W)

        frame_log_outer = ttk.Frame(self, style="TFrame")
        frame_log_outer.pack(fill=BOTH, expand=True, padx=16, pady=(0, 8))

        frame_log_border = Frame(frame_log_outer, bg=THEME["border"])
        frame_log_border.pack(fill=BOTH, expand=True)
        self._border_frames.append(frame_log_border)

        frame_log = ttk.Frame(frame_log_border, style="Card.TFrame")
        frame_log.pack(fill=BOTH, expand=True, padx=1, pady=1)

        inner_log = ttk.Frame(frame_log, style="CardInner.TFrame")
        inner_log.pack(fill=BOTH, expand=True, padx=10, pady=8)

        top_log_row = ttk.Frame(inner_log, style="CardInner.TFrame")
        top_log_row.pack(fill=X)

        self.lbl_console = ttk.Label(top_log_row, text=self.t("console_title"), style="Muted.TLabel")
        self.lbl_console.pack(side=LEFT)
        self._register_text(self.lbl_console, "console_title")

        log_row = ttk.Frame(inner_log, style="CardInner.TFrame")
        log_row.pack(fill=BOTH, expand=True, pady=(6, 0))

        self.log_widget = Text(
            log_row,
            height=25,
            bg=THEME["bg"],
            fg=THEME["text"],
            insertbackground=THEME["primary"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=THEME["border"],
            highlightcolor=THEME["primary"],
            padx=10,
            pady=10,
            font=("Segoe UI Emoji", 10),
            wrap="word"
        )
        self.log_widget.pack(side=LEFT, fill=BOTH, expand=True)
        self.log_widget.config(state="disabled")
        self.log_widget.bind("<Key>", lambda e: "break")
        self.log_widget.bind("<Button-1>", lambda e: "break")
        self.log_widget.bind("<Button-2>", lambda e: "break")
        self.log_widget.bind("<Button-3>", lambda e: "break")
        self.log_widget.bind("<B1-Motion>", lambda e: "break")

        self.log_scroll_visible = True
        self.log_scroll = ttk.Scrollbar(
            log_row,
            orient="vertical",
            command=self.log_widget.yview,
            style="Vertical.TScrollbar",
        )
        self.log_scroll.pack(side=LEFT, fill=Y, padx=(10, 0))
        self.log_widget.configure(yscrollcommand=self._on_log_scroll)

        frame_clear = ttk.Frame(log_row, style="CardInner.TFrame")
        frame_clear.pack(side=RIGHT, fill=Y, padx=(8, 0))

        btn_clear = ttk.Button(
            frame_clear,
            text=self.t("btn_clear"),
            command=lambda: self._debounced("btn_clear") and self.clear_log(),
            width=8,
            style="Uiverse.TButton"
        )
        btn_clear.pack(pady=2)
        self._register_text(btn_clear, "btn_clear")

        self.total_original = 0
        self.total_compressed = 0

        self._refresh_texts()
        self._configure_log_tags()
        self.update_idletasks()
        apply_window_theme(self)
        log_event("Main window initialized")
        self.protocol("WM_DELETE_WINDOW", self._on_main_close)

    def _on_main_close(self):
        log_event("Application closing")
        self.destroy()

    def report_callback_exception(self, exc, val, tb):
        handle_exception(exc, val, tb)

    def _register_text(self, widget, key: str, attr: str = "text"):
        self._i18n_widgets.append((widget, key, attr))

    def t(self, key: str, **kwargs) -> str:
        return tr(self._i18n, key, **kwargs)

    def set_language(self, lang: str):
        self.lang = lang
        self._i18n = load_translations(lang)
        self._refresh_texts()

    def apply_theme(self, theme: str):
        global THEME
        THEME = THEMES.get(theme, THEMES["light"])
        log_event(f"Theme applied: {theme}")
        apply_ttk_theme(self)
        apply_window_theme(self)
        self.configure(bg=THEME["bg"])
        self._configure_log_tags()
        self._refresh_texts()
        if callable(self._settings_apply_theme):
            self._settings_apply_theme()
        for frame in self._bg_frames:
            try:
                frame.configure(bg=THEME["bg"])
            except Exception:
                pass
        for frame in self._border_frames:
            try:
                frame.configure(bg=THEME["border"])
            except Exception:
                pass
        try:
            self.log_widget.configure(
                bg=THEME["bg"],
                fg=THEME["text"],
                insertbackground=THEME["primary"],
                highlightbackground=THEME["border"],
                highlightcolor=THEME["primary"],
            )
        except Exception:
            pass
        try:
            self.header_title.configure(bg=THEME["bg"], fg=THEME["text"])
            self.footer_label.configure(bg=THEME["bg"], fg=THEME["muted"])
        except Exception:
            pass
        try:
            self.log_scroll.configure(style="Vertical.TScrollbar")
        except Exception:
            pass

    def _refresh_texts(self):
        self.title(self.t("app_title"))
        for widget, key, attr in self._i18n_widgets:
            try:
                widget.configure(**{attr: self.t(key)})
            except Exception:
                pass
        self.footer_label.config(text=self.t("footer_text", version=VERSION, year=COPYRIGHT_YEAR))
        if not self.dst_dir:
            self.dst_label.config(text=self.t("dst_not_selected"))
        else:
            self.dst_label.config(text=self.t("dst_selected", path=self.dst_dir))

    def show_dialog(self, title: str, message: str, kind: str = "info", log_folder: str | None = None):
        log_event(f"Dialog requested: kind={kind}")
        AppDialog(self, title, message, kind, ok_text=self.t("btn_ok"), log_folder=log_folder)

    def _configure_log_tags(self):
        self.log_widget.tag_configure("log_info", foreground=THEME["log_info"])
        self.log_widget.tag_configure("log_success", foreground=THEME["log_success"])
        self.log_widget.tag_configure("log_warn", foreground=THEME["log_warn"])
        self.log_widget.tag_configure("log_error", foreground=THEME["log_error"])

    def _tag_for_log_line(self, text: str) -> str | None:
        if not self.log_color_enabled:
            return None
        t = text.lower()
        if "total compress" in t:
            return None
        if "erreur" in t or "error" in t or "échec" in t or "fail" in t:
            return "log_error"
        if "attention" in t or "warning" in t or "warn" in t:
            return "log_warn"
        if "✅" in text or "termin" in t or "finished" in t or "done" in t:
            return "log_success"
        if "analyse" in t or "analysis" in t or "compression" in t or "compress" in t:
            return "log_info"
        return None

    def _apply_scaling(self):
        try:
            pixels_per_inch = self.winfo_fpixels("1i")
            scaling = pixels_per_inch / 72.0
            self.tk.call("tk", "scaling", scaling)
        except Exception:
            pass

    def _debounced(self, key: str, delay_ms: int = 1000) -> bool:
        now = time.monotonic()
        if not hasattr(self, "_debounce_state"):
            self._debounce_state = {}
        last = self._debounce_state.get(key, 0.0)
        if (now - last) * 1000 < delay_ms:
            log_event(f"Click ignored (debounce): {key}")
            return False
        self._debounce_state[key] = now
        log_event(f"Button clicked: {key}")
        return True

    def _on_log_scroll(self, first: str, last: str):
        try:
            f = float(first)
            last_pos = float(last)
        except Exception:
            f = 0.0
            last_pos = 1.0
        if f <= 0.0 and last_pos >= 1.0:
            if self.log_scroll_visible:
                self.log_scroll.pack_forget()
                self.log_scroll_visible = False
        else:
            if not self.log_scroll_visible:
                self.log_scroll.pack(side=LEFT, fill=Y, padx=(10, 0))
                self.log_scroll_visible = True
        self.log_scroll.set(first, last)

    def log(self, text: str):
        self.log_widget.config(state="normal")
        log_event("UI log appended")
        tag = self._tag_for_log_line(text)
        if tag:
            self.log_widget.insert(END, text + "\n", tag)
        else:
            self.log_widget.insert(END, text + "\n")
        self.log_widget.see(END)
        self.log_widget.config(state="disabled")
        self.update_idletasks()

    def select_folder(self, event=None):
        path = filedialog.askdirectory(title=self.t("select_folder_title"))
        if path:
            self.src_dir = path
            self.log(self.t("log_folder_selected", path=path))
            log_event(f"Source selected: {path}")
            if self.auto_analyse_var.get():
                self.analyse()

    def on_drop(self, event):
        path = event.data.strip("{}")
        if os.path.isdir(path):
            self.src_dir = path
            self.log(self.t("log_folder_dropped", path=path))
            log_event(f"Source dropped: {path}")
            if self.auto_analyse_var.get():
                self.analyse()

    def analyse(self):
        if not self.src_dir:
            self.show_dialog(self.t("msg_warn_title"), self.t("msg_select_folder_first"), "warning")
            log_event("Analyze blocked: no source selected")
            return

        self.files_to_process.clear()
        self.total_original = 0
        total_estimated = 0
        log_event(f"Analyze started: source={self.src_dir}")

        self.log("\n" + self.t("log_analyzing"))

        for f in scan_folder(self.src_dir):
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_IMAGE + SUPPORTED_VIDEO + SUPPORTED_TEXT + SUPPORTED_PDF:
                self.files_to_process.append(f)
                o = os.path.getsize(f)
                e = estimate_size(f)
                self.total_original += o
                total_estimated += e
                self.log(
                    self.t(
                        "log_analyze_line",
                        name=os.path.basename(f),
                        original=human(o),
                        estimated=human(e),
                        gain=human(o - e),
                    )
                )

        self.log("\n" + self.t("log_separator"))
        self.log(self.t("log_total_original", value=human(self.total_original)))
        self.log(self.t("log_total_estimated", value=human(total_estimated)))
        self.log(self.t("log_total_gain", value=human(self.total_original - total_estimated)))
        self.log(self.t("log_separator") + "\n")
        log_event(
            "Analyze finished: "
            f"total_original={self.total_original} "
            f"total_estimated={total_estimated} "
            f"files={len(self.files_to_process)}"
        )

    def clear_log(self):
        self.log_widget.config(state="normal")
        self.log_widget.delete("1.0", END)
        self.log_widget.config(state="disabled")
        log_event("UI log cleared")

    def select_destination(self):
        path = filedialog.askdirectory(title=self.t("select_destination_title"))
        if path:
            self.dst_dir = path
            self.dst_label.config(text=self.t("dst_selected", path=self.dst_dir))
            log_event(f"Destination selected: {path}")

    def compress_thread(self):
        if not self.files_to_process:
            self.show_dialog(self.t("msg_warn_title"), self.t("msg_analyze_first"), "warning")
            log_event("Compress blocked: analyze not done")
            return

        if not self.dst_dir:
            self.show_dialog(self.t("msg_warn_title"), self.t("msg_select_destination"), "warning")
            log_event("Compress blocked: no destination selected")
            return

        self.clear_log()

        use_gpu = has_nvenc()
        log_event(f"Compression started: files={len(self.files_to_process)} use_gpu={use_gpu}")
        total_files = len(self.files_to_process)
        self.progress_global["maximum"] = total_files
        self.progress_global["value"] = 0
        self.total_compressed = 0

        for i, f in enumerate(self.files_to_process, 1):
            source_folder_name = os.path.basename(os.path.normpath(self.src_dir))
            rel = os.path.relpath(f, self.src_dir)
            dst = os.path.join(self.dst_dir, source_folder_name, rel)
            ext = os.path.splitext(f)[1].lower()

            self.log(self.t("log_compressing", name=os.path.basename(f)))
            log_event(f"Compressing file: {f}")

            f_size = os.path.getsize(f)
            if f_size > 10 * 1024 * 1024:
                self.lbl_prog_file.pack()
                self.progress_file.pack(pady=(8, 6))
                self.progress_file_label.pack()
                self.progress_file["value"] = 0
                self.progress_file["maximum"] = 100
                self.progress_file_label.config(text="0%")
                cb = self.update_file_progress
            else:
                self.lbl_prog_file.pack_forget()
                self.progress_file.pack_forget()
                self.progress_file_label.pack_forget()
                cb = None

            dispatch((f, dst, ext, use_gpu, cb))

            original_size = f_size
            compressed_size = os.path.getsize(dst)
            self.total_compressed += compressed_size

            percent_file = (compressed_size / original_size) * 100 if original_size > 0 else 100
            if cb:
                self.progress_file["value"] = 100
                self.progress_file_label.config(text=f"{percent_file:.1f}%")
            self.log(
                self.t(
                    "log_compressed_percent",
                    name=os.path.basename(f),
                    percent=f"{percent_file:.1f}%",
                )
            )
            log_event(
                "Compressed file: "
                f"path={f} original={original_size} compressed={compressed_size} "
                f"percent={percent_file:.1f}"
            )

            self.progress_global["value"] = i
            global_percent = ((i - 1) + self.progress_file["value"] / 100) / total_files * 100
            self.progress_global_label.config(
                text=self.t(
                    "progress_files",
                    percent=f"{global_percent:.1f}%",
                    current=i,
                    total=total_files,
                )
            )
            self.update_idletasks()

        self.log(
            "\n"
            + self.t(
                "log_done",
                path=os.path.join(self.dst_dir, source_folder_name),
            )
        )
        log_event(
            "Compression finished: "
            f"total_original={self.total_original} "
            f"total_compressed={self.total_compressed} "
            f"output={os.path.join(self.dst_dir, source_folder_name)}"
        )
        self.log(self.t("log_separator"))
        self.log(self.t("log_total_original", value=human(self.total_original)))
        self.log(self.t("log_total_compressed", value=human(self.total_compressed)))
        self.log(self.t("log_total_gain", value=human(self.total_original - self.total_compressed)))
        self.log(self.t("log_separator"))
        self.progress_global_label.config(text="100%")
        self.progress_file_label.config(text="100%")

    def update_file_progress(self, percent):
        self.progress_file["value"] = percent
        self.progress_file_label.config(text=f"{percent:.1f}%")
        self.update_idletasks()

    def open_settings_window(self):
        if self._settings_window and self._settings_window.winfo_exists():
            self._settings_window.lift()
            self._settings_window.focus_force()
            log_event("Settings window focused")
            return

        win = Toplevel(self)
        self._settings_window = win
        log_event("Settings window opened")
        win.title(self.t("settings_title"))
        win.geometry("320x400")
        win.resizable(False, False)
        win.configure(bg=THEME["bg"])
        apply_window_theme(win)

        header = Frame(win, bg=THEME["bg"], height=44)
        header.pack(fill=X, side=TOP)
        lbl_settings_header = Label(
            header,
            font=("Segoe UI Variable", 12, "bold"),
            fg=THEME["text"],
            bg=THEME["bg"]
        )
        lbl_settings_header.pack(pady=(10, 8))
        header_sep = Frame(win, bg=THEME["border"], height=1)
        header_sep.pack(fill=X, pady=(0, 10))

        lbl_img_quality = ttk.Label(win, style="Muted.TLabel")
        lbl_img_quality.pack(pady=(0, 0))
        lbl_img_quality_value = ttk.Label(win, style="Muted.TLabel")
        lbl_img_quality_value.pack(pady=(0, 0))
        img_var = IntVar(value=config.IMAGE_QUALITY)
        img_var.trace_add("write", lambda *_: log_event(f"Image quality changed: {img_var.get()}"))
        def update_img_value(_=None):
            lbl_img_quality_value.config(text=self.t("settings_value", value=img_var.get()))
        ttk.Scale(
            win,
            from_=10,
            to=100,
            orient=HORIZONTAL,
            variable=img_var,
            command=lambda _v: update_img_value()
        ).pack(fill=X, padx=20, pady=(0, 10))
        update_img_value()

        lbl_video_crf = ttk.Label(win, style="Muted.TLabel")
        lbl_video_crf.pack(pady=(0, 0))
        lbl_video_crf_value = ttk.Label(win, style="Muted.TLabel")
        lbl_video_crf_value.pack(pady=(0, 0))
        crf_var = IntVar(value=config.VIDEO_CRF)
        crf_var.trace_add("write", lambda *_: log_event(f"Video CRF changed: {crf_var.get()}"))
        def update_crf_value(_=None):
            lbl_video_crf_value.config(text=self.t("settings_value", value=crf_var.get()))
        ttk.Scale(
            win,
            from_=0,
            to=51,
            orient=HORIZONTAL,
            variable=crf_var,
            command=lambda _v: update_crf_value()
        ).pack(fill=X, padx=20)
        update_crf_value()

        lbl_lang = ttk.Label(win, style="Muted.TLabel")
        lbl_lang.pack(pady=(10, 0))
        lang_var = StringVar()
        lang_display = {"fr": "Français", "en": "English"}
        display_to_code = {v: k for k, v in lang_display.items()}
        lang_values = list(lang_display.values())
        lang_var.set(lang_display.get(self.lang, "Français"))
        lang_combo = ttk.Combobox(win, textvariable=lang_var, values=lang_values, state="readonly")
        lang_combo.pack(fill=X, padx=20, pady=(0, 4))
        lang_var.trace_add("write", lambda *_: log_event(f"Language selection changed: {lang_var.get()}"))

        theme_combo_label = ttk.Label(win, style="Muted.TLabel")
        theme_combo_label.pack(pady=(6, 0))
        theme_var = StringVar()
        theme_display = {"light": self.t("theme_light"), "dark": self.t("theme_dark")}
        display_to_theme = {v: k for k, v in theme_display.items()}
        theme_values = list(theme_display.values())
        theme_var.set(theme_display.get(config.THEME, self.t("theme_light")))
        theme_combo = ttk.Combobox(win, textvariable=theme_var, values=theme_values, state="readonly")
        theme_combo.pack(fill=X, padx=20, pady=(0, 4))
        theme_var.trace_add("write", lambda *_: log_event(f"Theme selection changed: {theme_var.get()}"))

        log_color_var = BooleanVar(value=config.LOG_COLOR)
        chk_log_color = ttk.Checkbutton(win, variable=log_color_var)
        chk_log_color.pack(pady=(6, 0))
        log_color_var.trace_add("write", lambda *_: log_event(f"Log color toggled: {log_color_var.get()}"))

        def save():
            data = {
                "IMAGE_QUALITY": img_var.get(),
                "VIDEO_CRF": crf_var.get(),
                "LANG": display_to_code.get(lang_var.get(), "fr"),
                "LOG_COLOR": bool(log_color_var.get()),
                "THEME": display_to_theme.get(theme_var.get(), "light"),
            }
            try:
                with open(settings_path(), "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)

                config.reload_settings()
                self.set_language(config.LANG)
                refresh_settings_texts()
                self.log_color_enabled = config.LOG_COLOR
                self.apply_theme(config.THEME)
                log_event(
                    "Settings saved: "
                    f"IMAGE_QUALITY={config.IMAGE_QUALITY} "
                    f"VIDEO_CRF={config.VIDEO_CRF} "
                    f"LANG={config.LANG} "
                    f"LOG_COLOR={config.LOG_COLOR} "
                    f"THEME={config.THEME}"
                )

                self.show_dialog(
                    self.t("settings_saved_title"),
                    self.t("settings_saved_message"),
                    "success",
                )

            except Exception as e:
                self.show_dialog(self.t("settings_error_title"), str(e), "error")
                log_event(f"Settings save error: {e}")

        btn_save = ttk.Button(win, command=lambda: self._debounced("btn_save") and save(), width=12, style="Uiverse.Primary.TButton")
        btn_save.pack(pady=15)

        def apply_settings_theme():
            win.configure(bg=THEME["bg"])
            header.configure(bg=THEME["bg"])
            lbl_settings_header.configure(bg=THEME["bg"], fg=THEME["text"])
            header_sep.configure(bg=THEME["border"])
            apply_window_theme(win)

        self._settings_apply_theme = apply_settings_theme

        def on_close():
            try:
                self._settings_window = None
            finally:
                win.destroy()
                log_event("Settings window closed")

        win.protocol("WM_DELETE_WINDOW", on_close)

        def refresh_settings_texts():
            win.title(self.t("settings_title"))
            lbl_settings_header.config(text=self.t("settings_header"))
            lbl_img_quality.config(text=self.t("settings_image_quality"))
            lbl_video_crf.config(text=self.t("settings_video_crf"))
            lbl_lang.config(text=self.t("settings_language"))
            theme_display.update({"light": self.t("theme_light"), "dark": self.t("theme_dark")})
            display_to_theme.clear()
            display_to_theme.update({v: k for k, v in theme_display.items()})
            theme_combo.config(values=list(theme_display.values()))
            theme_var.set(theme_display.get(config.THEME, self.t("theme_light")))
            theme_combo_label.config(text=self.t("settings_theme"))
            chk_log_color.config(text=self.t("settings_log_color"))
            btn_save.config(text=self.t("btn_save"))
            update_img_value()
            update_crf_value()
            apply_settings_theme()

        refresh_settings_texts()
        win.update_idletasks()
        apply_window_theme(win)

def main():
    init_logging()
    sys.excepthook = handle_exception
    def _thread_hook(args):
        handle_exception(args.exc_type, args.exc_value, args.exc_traceback)
    threading.excepthook = _thread_hook
    configure_dpi_awareness()
    missing = run_all_checks()

    if missing is True or not missing:
        missing_list = []
    elif isinstance(missing, (list, tuple, set)):
        missing_list = list(missing)
    else:
        missing_list = [str(missing)]

    if missing_list:
        root = Tk()
        root.withdraw()
        i18n = load_translations(config.LANG)
        msg = tr(i18n, "setup_incomplete_message", missing="\n".join(missing_list))
        AppDialog(root, tr(i18n, "setup_incomplete_title"), msg, "error", ok_text=tr(i18n, "btn_ok"))
        root.destroy()
        return

    global _current_app
    app = App()
    _current_app = app
    app.mainloop()

if __name__ == "__main__":
    main()
