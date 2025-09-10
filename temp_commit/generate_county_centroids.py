#!/usr/bin/env python3
"""
Generate a county_centroids.csv file from the full ASHRAE/RESNET JSON.

Usage:
  python generate_county_centroids.py \
    --in  HVAC_Design_Temps_FULL.json \
    --out county_centroids.csv

The script extracts (fips, state, county name, lat, lon) for each county.
If a county is missing lat/lon but has a nested station with lat/lon, it uses that.
"""

import argparse
import csv
import json
from typing import Any, Dict, List, Tuple


def read_json(path: str) -> Any:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def normalize_entries(raw: Any) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    if isinstance(raw, dict):
        it = raw.values()
    elif isinstance(raw, list):
        it = raw
    else:
        it = []
    for e in it:
        if isinstance(e, dict):
            entries.append(e)
    return entries


def main() -> None:
    p = argparse.ArgumentParser(description='Generate county centroids CSV from JSON')
    p.add_argument('--in', dest='in_path', required=True)
    p.add_argument('--out', dest='out_path', required=True)
    args = p.parse_args()

    data = read_json(args.in_path)
    entries = normalize_entries(data)

    rows: List[Tuple[str, str, str, str, str]] = []
    for e in entries:
        fips = str(e.get('fips') or e.get('FIPS') or e.get('countyFIPS') or '').zfill(5)
        name = (e.get('name') or e.get('county_name') or '').strip()
        state = (e.get('state') or e.get('state_abbr') or '').strip()
        lat = e.get('lat')
        lon = e.get('lon')

        # Fallback: if nested station object present with lat/lon
        if (lat is None or lon is None) and isinstance(e.get('station'), dict):
            lat = e['station'].get('lat', lat)
            lon = e['station'].get('lon', lon)

        # Skip if still missing coordinates
        if lat is None or lon is None:
            continue

        rows.append((state, name, fips, str(lat), str(lon)))

    with open(args.out_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['state', 'county', 'fips', 'lat', 'lon'])
        w.writerows(rows)

    print(f'Wrote {len(rows)} county centroids to {args.out_path}')


if __name__ == '__main__':
    main()


