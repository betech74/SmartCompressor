import subprocess
import os
import config
import shutil

from utils.paths import bundled_path

def compress(src, dst, use_gpu=False, progress_callback=None):
    try:
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
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            result = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", src],
                capture_output=True, text=True, env=env, creationflags=creationflags
            )
            out = (result.stdout or "").strip()
            total_duration = float(out) if out else 0.0
        except Exception:
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
            creationflags=creationflags
        )

        if process.stdout:
            for line in process.stdout:
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

        if progress_callback:
            progress_callback(100)

    except Exception as e:
        print(f"Erreur compression vidéo {src} : {e}")

        try:
            shutil.copy2(src, dst)
        except Exception as e2:
            print(f"Erreur fallback copie {src} : {e2}")
        if progress_callback:
            progress_callback(100)
