#!/usr/bin/env python3
"""
Fetch and consolidate NOAA 1991–2020 Climate Normals (HDD/CDD) into a single CSV.

Output CSV schema (what our merger expects):
  station_id, station_name, latitude, longitude, hdd65_ann, cdd65_ann

Usage (auto-try common URLs):
  python fetch_noaa_normals.py --out noaa_normals_hdd_cdd_1991_2020.csv

Usage (explicit URL if you have it):
  python fetch_noaa_normals.py --url https://.../your_noaa_normals.csv --out noaa_normals_hdd_cdd_1991_2020.csv

Notes:
- This script tries several likely NOAA NCEI WAF CSV endpoints. If none work,
  provide the exact URL via --url (from NCEI normals 1991–2020 pages) and rerun.
"""

import argparse
import csv
import sys
from pathlib import Path
from urllib.request import urlopen


DEFAULT_CANDIDATES = [
    # Common NCEI 1991–2020 normals annual products folders (degree days CSV names vary)
    # Provide multiple candidates; the first that works will be used
    "https://www.ncei.noaa.gov/pub/data/normals/1991-2020/products/annual/ann-degree-days-1991-2020.csv",
    "https://www.ncei.noaa.gov/pub/data/normals/1991-2020/products/annual/ann-deg-days-1991-2020.csv",
    "https://www.ncei.noaa.gov/pub/data/normals/1991-2020/products/annual/ann_hdd_cdd_1991_2020.csv",
]


def download_text(url: str) -> str:
    with urlopen(url) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} for {url}")
        return resp.read().decode("utf-8", errors="replace")


def detect_columns(header: list[str]) -> dict[str, int]:
    lut = {h.strip().lower(): i for i, h in enumerate(header)}
    def idx(*names: str):
        for n in names:
            i = lut.get(n)
            if i is not None:
                return i
        return None
    return {
        "station": idx("station", "station_id", "id"),
        "name": idx("name", "station_name"),
        "lat": idx("latitude", "lat"),
        "lon": idx("longitude", "lon", "lng"),
        # NOAA naming varies; try multiple possibilities
        "hdd": idx("hdd65_ann", "hdd65", "hdd"),
        "cdd": idx("cdd65_ann", "cdd65", "cdd"),
    }


def normalize(csv_text: str, out_path: Path) -> int:
    lines = [r for r in csv.reader(csv_text.splitlines()) if r]
    if len(lines) < 2:
        raise RuntimeError("CSV appears empty")
    cols = detect_columns(lines[0])
    if cols["lat"] is None or cols["lon"] is None:
        raise RuntimeError("CSV missing latitude/longitude columns")

    written = 0
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["station_id", "station_name", "latitude", "longitude", "hdd65_ann", "cdd65_ann"])
        for row in lines[1:]:
            try:
                lat = float(row[cols["lat"]]) if cols["lat"] is not None else None
                lon = float(row[cols["lon"]]) if cols["lon"] is not None else None
            except Exception:
                continue
            if lat is None or lon is None:
                continue
            sid = row[cols["station"]] if cols["station"] is not None else ""
            name = row[cols["name"]] if cols["name"] is not None else ""
            hdd = row[cols["hdd"]] if cols["hdd"] is not None else ""
            cdd = row[cols["cdd"]] if cols["cdd"] is not None else ""
            w.writerow([sid, name, lat, lon, hdd, cdd])
            written += 1
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch NOAA normals HDD/CDD and consolidate to a single CSV")
    ap.add_argument("--url", default=None, help="Explicit NOAA CSV URL to fetch")
    ap.add_argument("--out", default="noaa_normals_hdd_cdd_1991_2020.csv", help="Output CSV path")
    args = ap.parse_args()

    out_path = Path(args.out)

    tried: list[str] = []
    last_err = None
    urls = [args.url] if args.url else DEFAULT_CANDIDATES
    for url in [u for u in urls if u]:
        try:
            print(f"Fetching {url} ...")
            text = download_text(url)
            n = normalize(text, out_path)
            print(f"Wrote {n} stations to {out_path}")
            return
        except Exception as e:
            last_err = e
            tried.append(url)
            continue

    print("Could not fetch NOAA normals automatically.", file=sys.stderr)
    if last_err:
        print(f"Last error: {last_err}", file=sys.stderr)
    print("Please open the NOAA 1991–2020 normals WAF and copy the Degree Day CSV URL, then run:", file=sys.stderr)
    print("  python fetch_noaa_normals.py --url https://.../your_noaa_normals.csv --out noaa_normals_hdd_cdd_1991_2020.csv", file=sys.stderr)
    print("Suggested folder to browse:")
    print("  https://www.ncei.noaa.gov/pub/data/normals/1991-2020/products/annual/")


if __name__ == "__main__":
    main()


