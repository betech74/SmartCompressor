import fitz
import os

def compress(src, dst, use_gpu=False, progress_callback=None):
    os.makedirs(os.path.dirname(dst), exist_ok=True)

    doc = fitz.open(src)
    doc.save(dst, garbage=4, deflate=True)
    doc.close()

    if progress_callback:
        progress_callback(100)
