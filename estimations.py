import os
from config import SUPPORTED_VIDEO

RATIOS = {
    ".jpg": 0.6, ".jpeg": 0.6,
    ".png": 0.7,
    ".pdf": 0.65,
    ".txt": 0.2, ".json": 0.2, ".csv": 0.2
}

def estimate_size(path: str) -> int:
    size = os.path.getsize(path)
    ext = os.path.splitext(path)[1].lower()

    if ext in SUPPORTED_VIDEO:
        return int(size * 0.4)

    return int(size * RATIOS.get(ext, 1.0))
