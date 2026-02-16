from __future__ import annotations
import os
import sys
from pathlib import Path

def bundled_path(relative: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(os.getcwd())
    return base / relative

def user_data_dir(app_name: str = "SmartCompressor") -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        p = Path(appdata) / app_name
    else:
        p = Path.home() / f".{app_name}"
    p.mkdir(parents=True, exist_ok=True)
    return p

def settings_dir(app_name: str = "SmartCompressor") -> Path:
    p = user_data_dir(app_name) / "settings"
    p.mkdir(parents=True, exist_ok=True)
    return p

def log_dir(app_name: str = "SmartCompressor") -> Path:
    p = user_data_dir(app_name) / "log"
    p.mkdir(parents=True, exist_ok=True)
    return p

def settings_path(app_name: str = "SmartCompressor") -> Path:
    return settings_dir(app_name) / "settings.json"
