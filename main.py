from setup_check import run_all_checks
from scanner import scan_folder
from dispatcher import run
from gpu import has_nvenc
from report import generate
import os

def main(src_dir, dst_dir):
    run_all_checks()
    files = scan_folder(src_dir)
    use_gpu = has_nvenc()

    tasks = []

    for f in files:
        rel = os.path.relpath(f, src_dir)
        dst = os.path.join(dst_dir, rel)
        ext = os.path.splitext(f)[1].lower()
        tasks.append((f, dst, ext, use_gpu))

    run(tasks)
    generate("rapport.csv", [(t[0], t[1]) for t in tasks])

if __name__ == "__main__":
    print("Utilisé via la GUI")
