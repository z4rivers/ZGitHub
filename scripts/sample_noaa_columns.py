import tarfile, csv
from pathlib import Path
import sys


def safe_print(*args):
    try:
        print(*args)
    except UnicodeEncodeError:
        encoded = " ".join(str(a) for a in args).encode("utf-8", errors="replace")
        sys.stdout.buffer.write(encoded + b"\n")


tar_path = Path("us-climate-normals_2006-2020_v1.0.1_annualseasonal_multivariate_by-station_c20230404.tar.gz")
with tarfile.open(tar_path, "r:gz") as tar:
    # Just peek at first 5 CSVs
    count = 0
    for m in tar:
        if m.name.endswith(".csv"):
            f = tar.extractfile(m)
            head = f.read().decode("utf-8", errors="replace").splitlines()[:2]
            safe_print(f"{m.name} -> {head}")
            count += 1
            if count == 5:
                break
