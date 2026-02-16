from PIL import Image
import os
import shutil
import config

def compress(src, dst, use_gpu=False, progress_callback=None):
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        ext = os.path.splitext(src)[1].lower()
        original_size = os.path.getsize(src)
        quality = config.IMAGE_QUALITY

        with Image.open(src) as img:

            if img.mode == "P" and "transparency" in img.info:
                img = img.convert("RGBA")

            if ext in (".jpg", ".jpeg", ".png", ".webp"):

                if img.mode in ("RGBA", "LA"):
                    img = img.convert("RGB")

                if ext == ".webp":
                    img.save(
                        dst,
                        format="WEBP",
                        quality=quality,
                        method=6
                    )
                else:
                    img.save(dst, optimize=True, quality=quality)

            else:

                shutil.copy2(src, dst)
                if progress_callback:
                    progress_callback(100)
                return

        compressed_size = os.path.getsize(dst)
        if compressed_size >= original_size:

            try:
                os.remove(dst)
            except Exception:
                pass
            shutil.copy2(src, dst)

        if progress_callback:
            progress_callback(100)

    except PermissionError:
        try:
            shutil.copy2(src, dst)
        except Exception as e:
            print(f"Erreur copie fallback image {src} : {e}")
        if progress_callback:
            progress_callback(100)

    except Exception as e:
        print(f"Erreur compression image {src} : {e}")
        try:
            shutil.copy2(src, dst)
        except Exception:
            pass
        if progress_callback:
            progress_callback(100)
