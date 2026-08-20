import os
import json
import subprocess
from tkinter import Tk, filedialog
from PIL import Image
import fitz
import brotli
from tqdm import tqdm
import config
from utils.process import hidden_process_kwargs
from utils.paths import bundled_path

IMAGE_QUALITY = 75
VIDEO_CRF = 28
USE_GPU = True

SUPPORTED_VIDEO = (".mp4", ".mkv", ".avi")
SUPPORTED_IMAGE = (".jpg", ".jpeg", ".png")
SUPPORTED_TEXT = (".txt", ".json", ".csv")

def t(key, **kwargs):
    try:
        path = bundled_path(f"assets/locales/{config.LANG}.json")
        with open(path, "r", encoding="utf-8") as f:
            translations = json.load(f)
        text = translations.get(key, key)
    except Exception:
        text = key

    try:
        return text.format(**kwargs)
    except Exception:
        return text

def choose_folder(title):
    root = Tk()
    root.withdraw()
    return filedialog.askdirectory(title=title)

def get_size(path):
    return os.path.getsize(path)

def human(size):
    for unit in ["B","KB","MB","GB","TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

def estimate_compressed_size(path):
    size = get_size(path)
    ext = os.path.splitext(path)[1].lower()

    ratios = {
        ".jpg": 0.6, ".jpeg": 0.6,
        ".png": 0.7,
        ".pdf": 0.65,
        ".txt": 0.2, ".json": 0.2, ".csv": 0.2
    }

    if ext in SUPPORTED_VIDEO:
        return int(size * 0.4)

    return int(size * ratios.get(ext, 1.0))

def compress_image(src, dst):
    img = Image.open(src)
    img.save(dst, optimize=True, quality=IMAGE_QUALITY)

def compress_pdf(src, dst):
    doc = fitz.open(src)
    doc.save(dst, garbage=4, deflate=True)
    doc.close()

def compress_text(src, dst):
    with open(src, "rb") as f:
        data = f.read()
    compressed = brotli.compress(data)
    with open(dst + ".br", "wb") as f:
        f.write(compressed)

def compress_video(src, dst):
    cmd = ["ffmpeg", "-y", "-i", src]

    if USE_GPU:
        cmd += ["-c:v", "h264_nvenc", "-cq", str(VIDEO_CRF)]
    else:
        cmd += ["-c:v", "libx264", "-crf", str(VIDEO_CRF)]

    cmd += ["-preset", "slow", "-c:a", "aac", dst]
    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **hidden_process_kwargs(),
    )

def main():
    print(t("cli_select_source"))
    src_dir = choose_folder(t("cli_source_dialog"))
    if not src_dir:
        return

    files = []
    total_original = 0
    total_estimated = 0

    print(t("cli_analyzing"))
    for root, _, filenames in os.walk(src_dir):
        for f in filenames:
            path = os.path.join(root, f)
            ext = os.path.splitext(f)[1].lower()

            if ext not in SUPPORTED_IMAGE + SUPPORTED_VIDEO + SUPPORTED_TEXT + (".pdf",):
                continue

            orig = get_size(path)
            est = estimate_compressed_size(path)

            total_original += orig
            total_estimated += est

            files.append((path, ext))
    print(t("cli_analysis_done", count=len(files)))
    print(t("cli_original_size", size=human(total_original)))
    print(t("cli_estimated_size", size=human(total_estimated)))

    confirm = input(t("cli_confirm"))
    if confirm.strip().upper() != "OK":
        print(t("cli_cancelled"))
        return

    print(t("cli_select_destination"))
    dst_dir = choose_folder(t("cli_destination_dialog"))
    if not dst_dir:
        return

    print(t("cli_compressing"))

    for path, ext in tqdm(files, desc=t("cli_progress")):
        rel = os.path.relpath(path, src_dir)
        dst_path = os.path.join(dst_dir, rel)
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

        try:
            if ext in SUPPORTED_IMAGE:
                compress_image(path, dst_path)
            elif ext in SUPPORTED_VIDEO:
                compress_video(path, dst_path)
            elif ext == ".pdf":
                compress_pdf(path, dst_path)
            elif ext in SUPPORTED_TEXT:
                compress_text(path, dst_path)
        except Exception as e:
            print(t("cli_skipped", path=path, error=e))

    print(t("cli_finished"))

if __name__ == "__main__":
    main()
