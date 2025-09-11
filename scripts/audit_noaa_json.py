#!/usr/bin/env python3
"""Stream-audit NOAA extracted climate JSON.

Usage:
  python scripts/audit_noaa_json.py <path_to_json>
If no path is given, defaults to 'extracted_climate_data_comprehensive.json' in CWD.

Outputs a JSON summary to stdout and also writes a timestamped Markdown report
under reports/noaa_audit_summary.md when run as a standalone script.

The script is designed to keep memory usage low by reading the file with the
`ijson` streaming parser. Progress metrics print every 100 000 records.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
from pathlib import Path
from typing import Dict, Any

try:
    import ijson  # type: ignore
except ImportError as exc:
    sys.stderr.write("ijson not installed – install with `pip install ijson`\n")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two (lat, lon) points in kilometres."""
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return EARTH_RADIUS_KM * c


# Coordinates of Cantwell, AK (ZIP 99729) – fallback if API fails
ZIP_99729_LAT_LON = (63.392, -148.95)


# ---------------------------------------------------------------------------
# Main streaming audit
# ---------------------------------------------------------------------------

def audit(path: Path) -> Dict[str, Any]:
    start_ts = time.time()

    summary: Dict[str, Any] = {
        "file": str(path),
        "started": datetime.utcnow().isoformat() + "Z",
        "total_records": 0,
        "records_with_HDD_CDD": 0,
        "missing_lat_lon": 0,
        "state_counts": {},
        "sample_records": [],
        "nearest_to_99729": [],
        "elapsed_sec": None,
        "file_size_mb": round(path.stat().st_size / (1024 * 1024), 2),
    }

    state_counter: Counter[str] = Counter()

    # Pre-fetch precise lat/lon for 99729 via Zippopotam (non-fatal if offline)
    lat_99729, lon_99729 = ZIP_99729_LAT_LON
    try:
        import urllib.request

        zp = json.loads(
            urllib.request.urlopen("https://api.zippopotam.us/us/99729", timeout=5).read()
        )
        lat_99729 = float(zp["places"][0]["latitude"])
        lon_99729 = float(zp["places"][0]["longitude"])
    except Exception:
        pass

    nearest_candidates = []  # type: list[tuple[float, Dict[str, Any]]]

    with path.open("rb") as fh:
        # climate_data is an object keyed by ZIP OR station id depending on file.
        for key, obj in ijson.kvitems(fh, "climate_data"):
            summary["total_records"] += 1

            hdd = obj.get("hdd")
            cdd = obj.get("cdd")
            if isinstance(hdd, (int, float)) and isinstance(cdd, (int, float)):
                summary["records_with_HDD_CDD"] += 1

            lat, lon = obj.get("lat"), obj.get("lon")
            if lat in (None, 0, "") or lon in (None, 0, ""):
                summary["missing_lat_lon"] += 1
            else:
                # per-state counts – infer from station_name suffix or explicit field
                state = obj.get("state")
                if not state:
                    sn = obj.get("station_name", "")
                    if ", " in sn and sn.strip().endswith("US"):
                        parts = sn.split(",")
                        if len(parts) >= 2:
                            state = parts[-2].strip().split()[-1]
                if state:
                    state_counter[state] += 1

                # distance to 99729
                dist = haversine_km(lat_99729, lon_99729, lat, lon)
                if dist <= 50:  # km
                    nearest_candidates.append((dist, {**obj, "distance_km": round(dist, 1)}))

            # gather up to 5 sample records for inspection
            if len(summary["sample_records"]) < 5:
                summary["sample_records"].append(
                    {
                        "key": key,
                        "station_id": obj.get("station_id"),
                        "state": obj.get("state"),
                        "lat": lat,
                        "lon": lon,
                        "hdd": hdd,
                        "cdd": cdd,
                    }
                )

            # progress feedback every 100k (useful for huge files)
            if summary["total_records"] % 100_000 == 0:
                print(f"Processed {summary['total_records']:,} records…", file=sys.stderr)

    # post-processing
    summary["state_counts"] = state_counter.most_common()
    summary["nearest_to_99729"] = [x[1] for x in sorted(nearest_candidates)[:10]]
    summary["elapsed_sec"] = round(time.time() - start_ts, 2)

    return summary


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def main() -> None:
    path_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("extracted_climate_data_comprehensive.json")
    if not path_arg.exists():
        sys.stderr.write(f"ERROR: {path_arg} not found\n")
        sys.exit(1)

    summary = audit(path_arg)

    # dump JSON to stdout
    print(json.dumps(summary, indent=2, default=float))

    # also write/update markdown report
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    md_path = reports_dir / "noaa_audit_summary.md"

    with md_path.open("w", encoding="utf-8") as md:
        md.write(f"# NOAA Climate JSON Audit – {datetime.utcnow().date()}\n\n")
        md.write(f"*File size*: {summary['file_size_mb']} MB\n\n")
        md.write(f"*Total records*: {summary['total_records']:,}\n\n")
        md.write(f"*With HDD & CDD*: {summary['records_with_HDD_CDD']:,}\n\n")
        md.write(f"*Missing lat/lon*: {summary['missing_lat_lon']:,}\n\n")
        md.write("## Per-state counts (top 20)\n\n")
        md.write("State | Stations\n--- | ---\n")
        for st, cnt in summary["state_counts"][:20]:
            md.write(f"{st} | {cnt}\n")
        md.write("\n## Sample records\n\n")
        md.write("```json\n" + json.dumps(summary["sample_records"], indent=2, default=float) + "\n```\n\n")
        if summary["nearest_to_99729"]:
            md.write("## Stations within 50 km of ZIP 99729\n\n")
            md.write("```json\n" + json.dumps(summary["nearest_to_99729"], indent=2, default=float) + "\n```\n")
        md.write(f"\n_Processed in {summary['elapsed_sec']} s on {summary['started']}_\n")


if __name__ == "__main__":
    main()
