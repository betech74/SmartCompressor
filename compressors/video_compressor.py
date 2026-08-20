import subprocess
import os
import config

from utils.paths import bundled_path
from utils.process import hidden_process_kwargs

def compress(src, dst, use_gpu=False, progress_callback=None, control=None):
    try:
        if not os.path.isfile(src):
            raise FileNotFoundError(f"Source vidéo introuvable: {src}")

        os.makedirs(os.path.dirname(dst), exist_ok=True)
        ext_lower = os.path.splitext(src)[1].lower()
        crf = config.VIDEO_CRF

        ffmpeg = str(bundled_path("ffmpeg/ffmpeg.exe"))
        ffprobe = str(bundled_path("ffmpeg/ffprobe.exe"))
        env = os.environ.copy()
        ff_dir = str(bundled_path("ffmpeg"))
        env["PATH"] = ff_dir + os.pathsep + env.get("PATH", "")

        if ext_lower in (".mp4", ".mov", ".mkv"):
            final_codec = "libx265"
            use_nvenc = False
        elif use_gpu:
            final_codec = "hevc_nvenc"
            use_nvenc = True
        else:
            final_codec = "libx265"
            use_nvenc = False

        total_duration = 0.0
        process_kwargs = hidden_process_kwargs()
        try:
            result = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", src],
                capture_output=True, text=True, env=env, **process_kwargs
            )
            if result.returncode != 0:
                details = (result.stderr or result.stdout or "échec de ffprobe").strip()
                raise RuntimeError(f"Vidéo illisible: {details[-500:]}")
            out = (result.stdout or "").strip()
            total_duration = float(out) if out else 0.0
        except (OSError, ValueError, subprocess.SubprocessError):
            total_duration = 0.0

        if use_nvenc:
            cmd = [
                ffmpeg, "-y", "-i", src,
                "-c:v", final_codec, "-rc", "vbr_hq", "-cq", str(crf),
                "-b:v", "0", "-preset", "slow",
                "-c:a", "aac",
                "-progress", "pipe:1",
                dst
            ]
        else:
            cmd = [
                ffmpeg, "-y", "-i", src,
                "-c:v", final_codec,
                "-preset", "medium",
                "-crf", str(crf),
                "-x265-params",
                "threads=auto:rc-lookahead=20:b-intra=0:aq-mode=2:psy-rd=1.0:sao=0",
                "-c:a", "aac",
                "-progress", "pipe:1",
                dst
            ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            **process_kwargs
        )

        if process.stdout:
            for line in process.stdout:
                if control is not None and control.stop_event.is_set():
                    process.terminate()
                    break
                if progress_callback and total_duration > 0:
                    line = line.strip()
                    if line.startswith("out_time_ms="):
                        try:
                            out_ms = int(line.split("=", 1)[1].strip())
                            percent = min(100.0, (out_ms / (total_duration * 1_000_000.0)) * 100.0)
                            progress_callback(percent)
                        except ValueError:
                            continue

        process.wait()

        if process.returncode != 0 or not os.path.isfile(dst):
            raise RuntimeError(
                f"FFmpeg a échoué (code {process.returncode}) ou n'a pas créé la sortie"
            )

        if progress_callback:
            progress_callback(100)
        return True

    except Exception:
        try:
            if os.path.isfile(dst):
                os.remove(dst)
        except OSError:
            pass
        if progress_callback:
            progress_callback(100)
        return False
