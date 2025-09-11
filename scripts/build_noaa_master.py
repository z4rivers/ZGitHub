#!/usr/bin/env python3
"""Build a master JSON index of NOAA climate normals (2006-2020) by streaming the
large station-level tar archive. Designed to stay memory-efficient and commit
partial progress every 5 000 stations when invoked from a Git-controlled repo.

Writes incremental output to data/noaa_station_master.json as a JSON array.
Also logs progress and writes a final Markdown summary to reports/noaa_build_summary.md.

Usage:  python scripts/build_noaa_master.py [<tar_path>]
"""
from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List

TAR_DEFAULT = (
    "us-climate-normals_2006-2020_v1.0.1_annualseasonal_multivariate_by-station_c20230404.tar.gz"
)

OUTPUT_PATH = Path("data/noaa_station_master.json")
REPORT_PATH = Path("reports/noaa_build_summary.md")

COMMIT_CHUNK = 5_000  # commit every N stations
PROGRESS_EVERY = 1_000

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def git_available() -> bool:
    return shutil.which("git") is not None and (Path(".git").exists())


def git_commit(message: str) -> None:
    if not git_available():
        return
    subprocess.run(["git", "add", str(OUTPUT_PATH)], check=False)
    subprocess.run(["git", "commit", "-m", message], check=False)


def yield_station_csv_members(tar: tarfile.TarFile) -> Iterator[tarfile.TarInfo]:
    """Yield CSV members representing station normals (one per station)."""
    for m in tar:
        if m.isfile() and m.name.endswith(".csv"):
            yield m


def parse_station_csv(fileobj: Any) -> Dict[str, Any] | None:
    """Parse the NOAA CSV for a single station and return our record dict.

    Expected columns include ID, NAME, LATITUDE, LONGITUDE, HDD, CDD, etc.
    Because file formats vary slightly, we attempt to map common column names.
    """
    try:
        text = fileobj.read().decode("utf-8", errors="replace").splitlines()
    except Exception:
        return None
    reader = csv.DictReader(text)
    rows = list(reader)
    if not rows:
        return None
    row = rows[0]
    # Column name variants
    id_ = row.get("STATION_ID") or row.get("station_id") or row.get("STAID")
    name = row.get("STATION_NAME") or row.get("NAME")
    lat = row.get("LAT") or row.get("LATITUDE") or row.get("Latitude") or row.get("lat")
    lon = row.get("LON") or row.get("LONGITUDE") or row.get("Longitude") or row.get("lon")
    state = row.get("STATE") or row.get("State") or row.get("state") or row.get("ST")
    hdd = row.get("HDD") or row.get("HDD65") or row.get("HDD_ANNUAL") or row.get("HDD_65F")
    cdd = row.get("CDD") or row.get("CDD65") or row.get("CDD_ANNUAL") or row.get("CDD_65F")
    # Design temps may exist – else leave None
    heat99 = row.get("TMIN_PCTL_99") or row.get("PCTL_99_HEAT")
    cool01 = row.get("TMAX_PCTL_01") or row.get("PCTL_01_COOL")

    def as_float(x):
        try:
            return round(float(x), 3)
        except Exception:
            return None

    record = {
        "station_id": id_,
        "station_name": name,
        "lat": as_float(lat),
        "lon": as_float(lon),
        "state": state,
        "hdd": as_float(hdd),
        "cdd": as_float(cdd),
        "heat99": as_float(heat99),
        "cool01": as_float(cool01),
    }
    # require minimal fields
    if not id_ or record["lat"] is None or record["lon"] is None:
        return None
    return record


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_master(tar_path: Path) -> Dict[str, Any]:
    start = time.time()
    counters = Counter()
    stations_out: List[str] = []  # just station IDs in order for checkpointing

    total_members = 0
    with tarfile.open(tar_path, "r:gz") as tar:
        total_members = sum(1 for m in tar if m.name.endswith(".csv"))

    # Reopen for streaming read
    with tarfile.open(tar_path, "r:gz") as tar, OUTPUT_PATH.open("w", encoding="utf-8") as out:
        out.write("[")
        first_written = False
        processed = 0
        last_commit = 0
        eta_base = None
        for member in yield_station_csv_members(tar):
            fileobj = tar.extractfile(member)
            if not fileobj:
                continue
            rec = parse_station_csv(fileobj)
            processed += 1
            if rec:
                if first_written:
                    out.write(",")
                json.dump(rec, out, separators=(',', ':'), ensure_ascii=False)
                stations_out.append(rec["station_id"])
                counters[rec.get("state") or "unknown"] += 1
                first_written = True

            # progress log
            if processed % PROGRESS_EVERY == 0:
                elapsed = time.time() - start
                if eta_base is None:
                    eta_base = (elapsed / processed) * total_members
                pct = processed * 100 / total_members
                print(
                    f"{processed}/{total_members} ({pct:0.1f}%) elapsed {elapsed:0.1f}s ETA {eta_base - elapsed:0.1f}s"
                )
            # staged commits
            if processed - last_commit >= COMMIT_CHUNK:
                out.flush()
                git_commit(f"partial NOAA index – {processed} done")
                last_commit = processed
            # timeout – double of eta_base
            if eta_base and time.time() - start > eta_base * 2:
                print("Runtime exceeded ETA ×2; aborting.")
                break
        out.write("]")
    total_time = time.time() - start
    summary = {
        "stations": processed,
        "states": len(counters),
        "top_states": counters.most_common(10),
        "elapsed_sec": round(total_time, 1),
        "file_size_mb": round(OUTPUT_PATH.stat().st_size / 1_048_576, 2),
    }
    return summary


def write_report(summary: Dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as md:
        md.write(f"# NOAA Master Index Build – {datetime.utcnow().date()}\n\n")
        md.write(json.dumps(summary, indent=2))


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tar_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(TAR_DEFAULT)
    if not tar_path.exists():
        sys.stderr.write(f"ERROR: {tar_path} not found\n")
        sys.exit(1)

    print("Starting master index build…")
    summary = build_master(tar_path)
    write_report(summary)
    print("Build complete:", json.dumps(summary, indent=2))
    git_commit("chore: NOAA master index – complete")

