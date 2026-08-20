import sys
import shutil
import subprocess
import importlib.util
import os

from utils.process import hidden_process_kwargs

try:
    from utils.paths import bundled_path
except Exception:
    bundled_path = None

def fail(msg):
    sys.exit(1)

def is_frozen_exe() -> bool:
    return bool(getattr(sys, "frozen", False))

def get_ffmpeg_paths():
    env = os.environ.copy()

    if is_frozen_exe() and bundled_path is not None:
        ffmpeg = str(bundled_path("ffmpeg/ffmpeg.exe"))
        ffprobe = str(bundled_path("ffmpeg/ffprobe.exe"))

        ff_dir = str(bundled_path("ffmpeg"))
        env["PATH"] = ff_dir + os.pathsep + env.get("PATH", "")

        return ffmpeg, ffprobe, env

    return "ffmpeg", "ffprobe", env

def check_python():
    if sys.version_info < (3, 9):
        fail("Python 3.9+ requis")
    return True

def check_ffmpeg():
    ffmpeg, _, env = get_ffmpeg_paths()
    if ffmpeg == "ffmpeg":
        if not shutil.which("ffmpeg"):
            fail("FFmpeg introuvable dans le PATH")

    try:
        subprocess.run(
            [ffmpeg, "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            env=env,
            **hidden_process_kwargs(),
        )
        return True
    except Exception:
        fail("FFmpeg présent mais inutilisable")

def check_nvenc():
    ffmpeg, _, env = get_ffmpeg_paths()
    try:
        r = subprocess.run(
            [ffmpeg, "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            env=env,
            **hidden_process_kwargs(),
        )

        if ("h264_nvenc" in r.stdout) or ("hevc_nvenc" in r.stdout):
            return True
        else:
            return False
    except Exception:
        return False

def check_module(name):
    return importlib.util.find_spec(name) is not None

def check_dependencies():
    required = {
        "Pillow": "PIL",
        "PyMuPDF": "fitz",
        "brotli": "brotli",
        "tkinter": "tkinter"
    }

    for label, module in required.items():
        if not check_module(module):
            fail(f"Dépendance manquante : {label}")
    return True

def check_cpu():
    return os.cpu_count() or 1

def run_all_checks():
    if is_frozen_exe():
        try:
            return check_nvenc()
        except Exception:
            return False

    check_python()
    check_ffmpeg()
    check_dependencies()
    check_cpu()
    nvenc = check_nvenc()
    return nvenc
