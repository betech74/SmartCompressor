import csv
import os

def generate(csv_path, rows):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Fichier","Original","Compressé","Gain"])

        for src, dst in rows:
            if os.path.exists(dst):
                o = os.path.getsize(src)
                c = os.path.getsize(dst)
                w.writerow([src, o, c, o - c])
