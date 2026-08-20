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

def ok(msg):    print(f"✅ {msg}")
def warn(msg):  print(f"⚠️  {msg}")
def fail(msg):
    print(f"❌ {msg}")
    sys.exit(1)

def is_frozen_exe() -> bool:
    """True si lancé depuis un exe PyInstaller (onefile/onedir)."""
    return bool(getattr(sys, "frozen", False))

def get_ffmpeg_paths():
    """
    Retourne (ffmpeg_path, ffprobe_path, env) selon le contexte.
    - En exe : tente d'utiliser /ffmpeg/ffmpeg.exe et /ffmpeg/ffprobe.exe embarqués
    - En dev : utilise PATH
    """
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
    ok(f"Python {sys.version.split()[0]}")

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
        ok("FFmpeg détecté")
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
            ok("NVENC (GPU NVIDIA) disponible")
            return True
        else:
            warn("NVENC non détecté → CPU utilisé")
            return False
    except Exception:
        warn("Impossible de détecter NVENC")
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
        if check_module(module):
            ok(f"{label} installé")
        else:
            fail(f"Dépendance manquante : {label}")

def check_cpu():
    cores = os.cpu_count()
    if cores and cores < 2:
        warn("1 seul cœur CPU détecté")
    else:
        ok(f"{cores} cœurs CPU détectés")

def run_all_checks():
    """
    En dev : checks complets + retourne True/False pour NVENC
    En exe : ne bloque pas l'app (retourne juste has_nvenc() ou False)
    """

    if is_frozen_exe():
        print("\n🔍 Mode EXE détecté → checks dev ignorés.\n")

        try:
            return check_nvenc()
        except Exception:
            return False

    print("\n🔍 Vérification du setup...\n")
    check_python()
    check_ffmpeg()
    check_dependencies()
    check_cpu()
    nvenc = check_nvenc()
    print("\n✅ Environnement valide\n")
    return nvenc
