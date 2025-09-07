#!/usr/bin/env python3
"""
Compute HDD/CDD (base 65°F) from NOAA/NCEI ISD hourly data and export a county JSON.

Usage:
  1) Place NCEI CSV files under ncei_data/<FIPS>/ (one folder per county FIPS)
  2) Optionally edit stations_map.json to map county FIPS -> list of relative CSV paths
  3) Run:
        py compute_hdd_cdd_from_ncei.py --out ashrae_county_hdd_cdd.json

Notes:
  - This reads all CSVs for each FIPS folder or those listed in stations_map.json
  - It computes HDD/CDD at base 65°F and exports JSON with fields: fips, hdd, cdd
  - We do NOT estimate missing data. If a county has insufficient data, it's skipped.
"""

import argparse
import json
import os
import glob
from pathlib import Path

import pandas as pd
import numpy as np

DATA_ROOT = Path('ncei_data')
STATIONS_MAP_FILE = Path('stations_map.json')

BASE_F = 65.0
MIN_OBS = 50_000  # minimum hourly observations for reliability (~5.7 years)


def load_station_paths_for_fips(fips: str) -> list:
    # Use stations_map.json if provided; else default to all CSVs in folder
    if STATIONS_MAP_FILE.exists():
        try:
            mapping = json.loads(STATIONS_MAP_FILE.read_text(encoding='utf-8'))
            if fips in mapping:
                return [str(Path(p)) for p in mapping[fips]]
        except Exception:
            pass
    # Fallback: any CSV directly under ncei_data/<fips>/
    folder = DATA_ROOT / fips
    return [str(p) for p in folder.glob('*.csv')]


def load_and_clean(paths: list) -> pd.Series:
    frames = []
    for p in paths:
        try:
            df = pd.read_csv(p, sep=r"\s+|,", engine='python', low_memory=False)
            # Try common temperature columns
            temp = None
            for col in ['TMP', 'temp', 'temperature', 'air_temp']:
                if col in df.columns:
                    temp = df[col]
                    break
            if temp is None:
                continue
            # NCEI ISD TMP often in tenth °C; try to detect
            s = pd.to_numeric(temp, errors='coerce')
            if s.abs().median() > 120:  # probably tenths of °C
                s = s / 10.0
            # Convert C→F if values look like Celsius
            # Heuristic: if median < 45, assume °C
            if s.dropna().median() < 45:
                s = (s * 9/5) + 32
            frames.append(s)
        except Exception:
            continue
    if not frames:
        return pd.Series(dtype=float)
    all_t = pd.concat(frames, ignore_index=True)
    all_t = pd.to_numeric(all_t, errors='coerce')
    all_t = all_t.dropna()
    return all_t


def compute_hdd_cdd(temp_f: pd.Series) -> tuple:
    total_hours = len(temp_f)
    if total_hours < MIN_OBS:
        return None, None
    below = (BASE_F - temp_f[temp_f < BASE_F]).clip(lower=0)
    above = (temp_f[temp_f > BASE_F] - BASE_F).clip(lower=0)
    hdd = float(below.sum() / 24.0)
    cdd = float(above.sum() / 24.0)
    return hdd, cdd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='ashrae_county_hdd_cdd.json', help='Output JSON file')
    args = ap.parse_args()

    results = {}

    # Iterate fips folders under ncei_data
    if not DATA_ROOT.exists():
        print("ncei_data/ not found. Create folders ncei_data/<FIPS>/ with CSVs.")
        return 1

    candidate_folders = [p for p in DATA_ROOT.iterdir() if p.is_dir()]
    if not candidate_folders:
        print("No county folders under ncei_data/. Nothing to compute.")
        return 1

    for folder in candidate_folders:
        fips = folder.name
        paths = load_station_paths_for_fips(fips)
        if not paths:
            print(f"Skipping {fips}: no CSV files")
            continue
        temps = load_and_clean(paths)
        if temps.empty:
            print(f"Skipping {fips}: could not read temperatures")
            continue
        hdd, cdd = compute_hdd_cdd(temps)
        if hdd is None:
            print(f"Skipping {fips}: insufficient observations ({len(temps)})")
            continue
        results[fips] = {
            'fips': fips,
            'hdd': round(hdd),
            'cdd': round(cdd),
            'source': 'NOAA NCEI ISD (computed)',
        }
        print(f"Computed {fips}: HDD={round(hdd)}, CDD={round(cdd)}")

    if not results:
        print("No results produced.")
        return 1

    Path(args.out).write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(f"Wrote {args.out} with {len(results)} counties")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())




