import os
import json
from datetime import datetime
from utils.paths import settings_path

DEFAULT_SETTINGS = {
    "IMAGE_QUALITY": 75,
    "VIDEO_CRF": 28,
    "LANG": "en",
    "LOG_COLOR": True,
    "THEME": "light"
}

SETTINGS_FILE = settings_path()

def _ensure_settings_file():
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(DEFAULT_SETTINGS, indent=4), encoding="utf-8")

def _load_settings():
    _ensure_settings_file()
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_SETTINGS.copy()

settings = _load_settings()

IMAGE_QUALITY = int(settings.get("IMAGE_QUALITY", DEFAULT_SETTINGS["IMAGE_QUALITY"]))
VIDEO_CRF     = int(settings.get("VIDEO_CRF", DEFAULT_SETTINGS["VIDEO_CRF"]))
LANG          = str(settings.get("LANG", DEFAULT_SETTINGS["LANG"]))
LOG_COLOR     = bool(settings.get("LOG_COLOR", DEFAULT_SETTINGS["LOG_COLOR"]))
THEME         = str(settings.get("THEME", DEFAULT_SETTINGS["THEME"]))

IMAGE_QUALITY = max(10, min(100, IMAGE_QUALITY))
VIDEO_CRF     = max(0,  min(51,  VIDEO_CRF))

SUPPORTED_IMAGE = (".jpg", ".jpeg", ".png", ".webp")
SUPPORTED_VIDEO = (".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".3gp", ".ts", ".mts", ".m2ts", ".vob", ".ogv")
SUPPORTED_TEXT  = (".txt", ".json", ".csv")
SUPPORTED_PDF   = (".pdf",)

MAX_WORKERS = os.cpu_count()

VERSION = "1.1"
PROJECT_START_YEAR = 2026
CURRENT_YEAR = datetime.now().year
COPYRIGHT_YEAR = str(CURRENT_YEAR) if PROJECT_START_YEAR == CURRENT_YEAR else f"{PROJECT_START_YEAR}-{CURRENT_YEAR}"

def reload_settings():
    global IMAGE_QUALITY, VIDEO_CRF, LANG, LOG_COLOR, THEME
    data = _load_settings()
    IMAGE_QUALITY = int(data.get("IMAGE_QUALITY", DEFAULT_SETTINGS["IMAGE_QUALITY"]))
    VIDEO_CRF     = int(data.get("VIDEO_CRF", DEFAULT_SETTINGS["VIDEO_CRF"]))
    LANG          = str(data.get("LANG", DEFAULT_SETTINGS["LANG"]))
    LOG_COLOR     = bool(data.get("LOG_COLOR", DEFAULT_SETTINGS["LOG_COLOR"]))
    THEME         = str(data.get("THEME", DEFAULT_SETTINGS["THEME"]))
    IMAGE_QUALITY = max(10, min(100, IMAGE_QUALITY))
    VIDEO_CRF     = max(0,  min(51,  VIDEO_CRF))
