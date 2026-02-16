import os
import sys
import subprocess

try:
    from utils.paths import bundled_path
except Exception:
    bundled_path = None

def _ffmpeg_cmd_and_env():
    """
    Retourne (cmd_ffmpeg, env) en fonction du contexte:
    - en exe PyInstaller: ffmpeg embarqué dans /ffmpeg/ffmpeg.exe
    - en dev: 'ffmpeg' via PATH
    """
    env = os.environ.copy()

    if getattr(sys, "frozen", False) and bundled_path is not None:
        ffmpeg = str(bundled_path("ffmpeg/ffmpeg.exe"))
        ff_dir = str(bundled_path("ffmpeg"))
        env["PATH"] = ff_dir + os.pathsep + env.get("PATH", "")
        return ffmpeg, env

    return "ffmpeg", env

def has_nvenc() -> bool:
    ffmpeg, env = _ffmpeg_cmd_and_env()
    try:
        r = subprocess.run(
            [ffmpeg, "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            env=env
        )
        out = r.stdout or ""
        return ("h264_nvenc" in out) or ("hevc_nvenc" in out)
    except Exception:
        return False
