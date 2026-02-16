import os
import shutil

def compress(src, dst, use_gpu=False, progress_callback=None):
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(src, "r", encoding="utf-8") as f:
            lines = f.readlines()

        lines = [line.strip() for line in lines if line.strip()]

        with open(dst, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        if progress_callback:
            progress_callback(100)

    except Exception as e:
        print(f"Erreur compression texte pour {src} : {e}")
        shutil.copy2(src, dst)
        if progress_callback:
            progress_callback(100)
