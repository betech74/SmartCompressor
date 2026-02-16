import os
from config import SUPPORTED_IMAGE, SUPPORTED_VIDEO, SUPPORTED_TEXT, SUPPORTED_PDF

def scan_folder(folder: str):
    files = []
    for root, _, filenames in os.walk(folder):
        for f in filenames:
            path = os.path.join(root, f)
            ext = os.path.splitext(f)[1].lower()

            if ext in SUPPORTED_IMAGE + SUPPORTED_VIDEO + SUPPORTED_TEXT + SUPPORTED_PDF:
                files.append(path)
    return files
