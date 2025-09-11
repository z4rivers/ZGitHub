#!/usr/bin/env python3
"""
Build a nationwide Master Climate Index from NOAA normals CSVs (>=25 KB) located in
`data/NOAA_Filtered_25k`.

- Streams files in batches (configurable via --start/--end indices)
- Extracts STATION, NAME, LATITUDE, LONGITUDE, ELEVATION
- Captures all HTDD-BASE* and CLDD-BASE* fields plus TAVG/TMIN/TMAX normals and QC flags
- Prefers HTDD-BASE65 and CLDD-BASE65; if missing, attempts derivation/approximation and records method
- Appends JSONL to `data/master_climate_index.jsonl`
- Writes a simple checkpoint file to allow resumable runs
- Prints batch start/end timestamps and counts

Usage:
  python scripts/build_master_index.py
  python scripts/build_master_index.py --start 0 --end 200
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Iterable, List, Tuple

DATA_DIR = Path("data/NOAA_Filtered_25k")
OUTPUT_PATH = Path("data/master_climate_index.jsonl")
CHECKPOINT_PATH = Path("data/master_climate_index.checkpoint.json")
REPORT_PATH = Path("reports/master_index_summary.md")

REQUIRED_COLS = {"STATION", "NAME", "LATITUDE", "LONGITUDE", "ELEVATION"}

# Keys to keep: HDD/CDD bases and temps with flags
KEEP_PREFIXES = (
    "HTDD-BASE",  # match anywhere too
    "CLDD-BASE",  # match anywhere too
    "ANN-TAVG-",
    "ANN-TMIN-",
    "ANN-TMAX-",
    "MAM-TAVG-", "JJA-TAVG-", "SON-TAVG-", "DJF-TAVG-",
    "MAM-TMIN-", "JJA-TMIN-", "SON-TMIN-", "DJF-TMIN-",
    "MAM-TMAX-", "JJA-TMAX-", "SON-TMAX-", "DJF-TMAX-",
)
FLAG_PREFIXES = ("comp_flag_", "meas_flag_", "years_")


@dataclass
class Record:
    station: str
    name: str
    lat: float
    lon: float
    elev: float
    fields: Dict[str, Any]
    hdd65: float | None
    cdd65: float | None
    hdd65_method: str | None
    cdd65_method: str | None


def list_csv_files() -> List[Path]:
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"{DATA_DIR} not found")
    files = [p for p in sorted(DATA_DIR.iterdir()) if p.suffix.lower() == ".csv" and p.stat().st_size >= 25_000]
    return files


def parse_csv(path: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        header_map = {k: k for k in reader.fieldnames or []}
        rows = list(reader)
    return header_map, rows


def coerce_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, str):
            v = value.strip()
            if v == "" or v.upper() in {"NA", "N/A", "-9999", "-9999.0"}:
                return None
            return float(v)
        return float(value)
    except Exception:
        return None


def extract_fields(row: Dict[str, Any]) -> Tuple[Dict[str, Any], float | None, float | None, str | None, str | None]:
    # Capture all desired fields by prefix or substring
    kept: Dict[str, Any] = {}
    for k, v in row.items():
        if not k:
            continue
        if (
            k in REQUIRED_COLS
            or ("HTDD-BASE" in k)
            or ("CLDD-BASE" in k)
            or any(k.startswith(pref) for pref in KEEP_PREFIXES)
            or any(k.startswith(pref) for pref in FLAG_PREFIXES)
        ):
            kept[k] = v

    # Prefer direct base 65
    hdd65 = coerce_float(row.get("HTDD-BASE65"))
    cdd65 = coerce_float(row.get("CLDD-BASE65"))
    hdd_method = "direct" if hdd65 is not None else None
    cdd_method = "direct" if cdd65 is not None else None

    # Attempt nearest base fallback when 65 not available
    if hdd65 is None:
        for base in (60, 70, 55, 75):
            # some columns include qualifiers like -NORMAL; try exact first then scan
            val = row.get(f"HTDD-BASE{base}")
            if val is None:
                # search any column containing this token
                for ck, cv in row.items():
                    if f"HTDD-BASE{base}" in (ck or ""):
                        val = cv
                        break
            alt = coerce_float(val)
            if alt is not None:
                hdd65 = alt
                hdd_method = f"alt_base_{base}"
                break
    if cdd65 is None:
        for base in (60, 70, 55, 75):
            val = row.get(f"CLDD-BASE{base}")
            if val is None:
                for ck, cv in row.items():
                    if f"CLDD-BASE{base}" in (ck or ""):
                        val = cv
                        break
            alt = coerce_float(val)
            if alt is not None:
                cdd65 = alt
                cdd_method = f"alt_base_{base}"
                break

    return kept, hdd65, cdd65, hdd_method, cdd_method


def make_record(row: Dict[str, Any]) -> Record | None:
    st = row.get("STATION") or row.get("station")
    name = row.get("NAME") or row.get("name")
    lat = coerce_float(row.get("LATITUDE") or row.get("LAT"))
    lon = coerce_float(row.get("LONGITUDE") or row.get("LON"))
    elev = coerce_float(row.get("ELEVATION") or row.get("elev"))
    if not st or lat is None or lon is None:
        return None
    fields, hdd65, cdd65, hdd_m, cdd_m = extract_fields(row)
    return Record(
        station=st,
        name=name or "",
        lat=lat,
        lon=lon,
        elev=elev or 0.0,
        fields=fields,
        hdd65=hdd65,
        cdd65=cdd65,
        hdd65_method=hdd_m,
        cdd65_method=cdd_m,
    )


def write_jsonl(records: Iterable[Record]) -> int:
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    count = 0
    with OUTPUT_PATH.open("a", encoding="utf-8") as out:
        for rec in records:
            obj = {
                "station": rec.station,
                "name": rec.name,
                "lat": rec.lat,
                "lon": rec.lon,
                "elev": rec.elev,
                "hdd65": rec.hdd65,
                "cdd65": rec.cdd65,
                "hdd65_method": rec.hdd65_method,
                "cdd65_method": rec.cdd65_method,
                "fields": rec.fields,
            }
            out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            count += 1
    return count


def write_checkpoint(start: int, end: int, processed_files: List[str], record_count: int) -> None:
    CHECKPOINT_PATH.parent.mkdir(exist_ok=True)
    ck = {
        "started": datetime.utcnow().isoformat() + "Z",
        "start_index": start,
        "end_index": end,
        "files": processed_files,
        "records_written": record_count,
    }
    with CHECKPOINT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(ck, fh, indent=2)


def build(start: int | None, end: int | None) -> Dict[str, Any]:
    files = list_csv_files()
    total = len(files)
    s = start or 0
    e = end if end is not None else total
    s = max(0, s)
    e = min(total, e)

    batch_files = files[s:e]

    began = datetime.utcnow().isoformat() + "Z"
    recs: List[Record] = []
    processed_files: List[str] = []

    for fp in batch_files:
        header, rows = parse_csv(fp)
        # Skip precipitation-only files by checking absence of HDD/CDD tokens anywhere in headers
        has_hdd_cdd = any((("HTDD-BASE" in (k or "")) or ("CLDD-BASE" in (k or ""))) for k in header)
        if not has_hdd_cdd:
            continue
        for row in rows:
            rec = make_record(row)
            if rec:
                recs.append(rec)
        processed_files.append(fp.name)

    written = write_jsonl(recs)
    write_checkpoint(s, e, processed_files, written)

    ended = datetime.utcnow().isoformat() + "Z"
    return {
        "started": began,
        "ended": ended,
        "files_in_batch": len(batch_files),
        "files_written": len(processed_files),
        "records_written": written,
        "total_files_available": total,
        "batch_range": [s, e],
    }


def summarize() -> Dict[str, Any]:
    stations = 0
    missing_coords = 0
    have_hdd = 0
    have_cdd = 0
    bases_present: Dict[str, int] = {}

    if not OUTPUT_PATH.exists():
        return {}

    with OUTPUT_PATH.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            stations += 1
            if obj.get("lat") in (None, 0) or obj.get("lon") in (None, 0):
                missing_coords += 1
            if obj.get("hdd65") is not None:
                have_hdd += 1
            if obj.get("cdd65") is not None:
                have_cdd += 1
            for k in obj.get("fields", {}).keys():
                if ("HTDD-BASE" in k) or ("CLDD-BASE" in k):
                    base_token = k.split("BASE")[-1]  # e.g., '65', '60'
                    base_key = f"BASE{base_token}"
                    bases_present[base_key] = bases_present.get(base_key, 0) + 1

    return {
        "stations": stations,
        "missing_coords": missing_coords,
        "have_hdd65": have_hdd,
        "have_cdd65": have_cdd,
        "bases_present": dict(sorted(bases_present.items())),
    }


def write_report(summary: Dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as md:
        md.write(f"# Master Climate Index Summary – {datetime.utcnow().date()}\n\n")
        md.write("```json\n" + json.dumps(summary, indent=2) + "\n```\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=None)
    ap.add_argument("--end", type=int, default=None)
    args = ap.parse_args()

    print(f"[start] {datetime.utcnow().isoformat()}Z")
    result = build(args.start, args.end)
    print(json.dumps(result, indent=2))
    summary = summarize()
    write_report(summary)
    print(f"[end] {datetime.utcnow().isoformat()}Z")
