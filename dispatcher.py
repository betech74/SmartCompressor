import os
from concurrent.futures import ThreadPoolExecutor
from config import SUPPORTED_IMAGE, SUPPORTED_VIDEO, SUPPORTED_TEXT, SUPPORTED_PDF
from compressors import (
    image_compressor,
    video_compressor,
    pdf_compressor,
    text_compressor
)

IMAGE_WORKERS = min(8, os.cpu_count() or 4)
VIDEO_WORKERS = min(8, os.cpu_count() or 4)

VIDEO_PARALLEL_THRESHOLD = 10 * 1024 * 1024

def dispatch(task):
    try:
        if len(task) == 5:
            src, dst, ext, use_gpu, progress_callback = task
        else:
            src, dst, ext, use_gpu = task
            progress_callback = None

        os.makedirs(os.path.dirname(dst), exist_ok=True)
        ext_lower = ext.lower()

        if ext_lower in SUPPORTED_IMAGE:
            image_compressor.compress(src, dst, use_gpu=use_gpu, progress_callback=progress_callback)
        elif ext_lower in SUPPORTED_VIDEO:
            video_compressor.compress(src, dst, use_gpu=use_gpu, progress_callback=progress_callback)
        elif ext_lower in SUPPORTED_TEXT:
            text_compressor.compress(src, dst, progress_callback=progress_callback)
        elif ext_lower in SUPPORTED_PDF:
            pdf_compressor.compress(src, dst, progress_callback=progress_callback)

    except Exception as e:
        print(f"Erreur lors du traitement de {task[0]} : {e}")

        try:
            import shutil
            shutil.copy2(task[0], task[1])
        except Exception as e2:
            print(f"Erreur fallback copie {task[0]} : {e2}")

    return task[0], task[1]

def run(tasks):
    """
    Tri des tâches par priorité et exécution
    PDF -> Textes -> Images -> Vidéos
    """
    pdf_tasks = []
    text_tasks = []
    image_tasks = []
    video_small_tasks = []
    video_large_tasks = []

    for task in tasks:
        ext = task[2].lower()
        if ext in SUPPORTED_PDF:
            pdf_tasks.append(task)
        elif ext in SUPPORTED_TEXT:
            text_tasks.append(task)
        elif ext in SUPPORTED_IMAGE:
            image_tasks.append(task)
        elif ext in SUPPORTED_VIDEO:
            size = os.path.getsize(task[0])
            if size <= VIDEO_PARALLEL_THRESHOLD:
                video_small_tasks.append(task)
            else:
                video_large_tasks.append(task)

    for task in pdf_tasks:
        dispatch(task)

    for task in text_tasks:
        dispatch(task)

    with ThreadPoolExecutor(max_workers=IMAGE_WORKERS) as executor:
        list(executor.map(dispatch, image_tasks))

    if video_small_tasks:
        with ThreadPoolExecutor(max_workers=VIDEO_WORKERS) as executor:
            list(executor.map(dispatch, video_small_tasks))

    for task in video_large_tasks:
        dispatch(task)
