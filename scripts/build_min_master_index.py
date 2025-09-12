#!/usr/bin/env python3
"""
Create a minimal JSONL from data/master_climate_index.jsonl containing only
the fields used by the UI for fast client-side loading.

Input:  data/master_climate_index.jsonl (large, full records)
Output: data/master_climate_index.min.jsonl (small, station/name/lat/lon/hdd65/cdd65)

Usage:
  python scripts/build_min_master_index.py

Notes:
  - Streams line-by-line; memory usage stays low
  - Skips malformed lines and records missing coordinates
  - Prints progress every N lines and a final size summary
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Any

IN_PATH = Path("data/master_climate_index.jsonl")
OUT_PATH = Path("data/master_climate_index.min.jsonl")


def to_float(value: Any):
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


def main() -> None:
    if not IN_PATH.exists():
        raise SystemExit(f"Input not found: {IN_PATH}")

    OUT_PATH.parent.mkdir(exist_ok=True)

    total_in = 0
    total_out = 0
    start = time.time()
    last_report = start
    report_every = 100000  # lines

    with IN_PATH.open("r", encoding="utf-8", errors="replace") as fin, \
         OUT_PATH.open("w", encoding="utf-8") as fout:
        for line in fin:
            total_in += 1
            s = line.strip()
            if not s:
                continue
            try:
                obj: Dict[str, Any] = json.loads(s)
            except Exception:
                continue

            lat = to_float(obj.get("lat"))
            lon = to_float(obj.get("lon"))
            if lat is None or lon is None:
                continue

            rec = {
                "station": obj.get("station"),
                "name": obj.get("name"),
                "lat": lat,
                "lon": lon,
                "hdd65": to_float(obj.get("hdd65")),
                "cdd65": to_float(obj.get("cdd65")),
            }
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            total_out += 1

            if total_in % report_every == 0:
                now = time.time()
                if now - last_report >= 1.0:
                    print(f"[progress] lines_in={total_in:,} lines_out={total_out:,} elapsed={now-start:.1f}s")
                    last_report = now

    elapsed = time.time() - start
    out_size = OUT_PATH.stat().st_size if OUT_PATH.exists() else 0
    print(json.dumps({
        "lines_in": total_in,
        "lines_out": total_out,
        "elapsed_sec": round(elapsed, 2),
        "output_bytes": out_size,
        "output_path": str(OUT_PATH)
    }, indent=2))


if __name__ == "__main__":
    main()


