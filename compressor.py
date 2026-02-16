import os
import subprocess
from tkinter import Tk, filedialog
from PIL import Image
import fitz
import brotli
from tqdm import tqdm

IMAGE_QUALITY = 75
VIDEO_CRF = 28
USE_GPU = True

SUPPORTED_VIDEO = (".mp4", ".mkv", ".avi")
SUPPORTED_IMAGE = (".jpg", ".jpeg", ".png")
SUPPORTED_TEXT = (".txt", ".json", ".csv")

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
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    print("\nSelect source folder")
    src_dir = choose_folder("Select folder to compress")
    if not src_dir:
        return

    files = []
    total_original = 0
    total_estimated = 0

    print("\nANALYSIS & ESTIMATION\n")
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
            print(f"{f}")
            print(f"  Original : {human(orig)}")
            print(f"  Estimated: {human(est)}")
            print(f"  Saved    : {human(orig - est)}\n")

    print("=================================")
    print(f"TOTAL ORIGINAL : {human(total_original)}")
    print(f"TOTAL ESTIMATED: {human(total_estimated)}")
    print(f"TOTAL SAVED   : {human(total_original - total_estimated)}")
    print("=================================\n")

    confirm = input("Type 'OK' to start compression: ")
    if confirm.strip().upper() != "OK":
        print("Cancelled")
        return

    print("\nSelect destination folder")
    dst_dir = choose_folder("Select destination folder")
    if not dst_dir:
        return

    print("\nCOMPRESSION IN PROGRESS...\n")

    for path, ext in tqdm(files):
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
            print(f"Error on {path}: {e}")

    print("\nCompression finished")

if __name__ == "__main__":
    main()
