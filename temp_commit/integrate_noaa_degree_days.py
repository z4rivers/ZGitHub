#!/usr/bin/env python3
"""
Integrate NOAA 1991–2020 Climate Normals (HDD65/CDD65 annual) into an
ASHRAE/RESNET county dataset JSON.

Usage:
  python integrate_noaa_degree_days.py \
    --in  HVAC_Design_Temps_FULL.json \
    --out HVAC_Design_Temps_FULL_WITH_NOAA.json \
    --qc  QC_report.csv \
    --normals-csv noaa_normals_hdd_cdd_1991_2020.csv \
    --county-centroids county_centroids.csv

Notes:
- No external dependencies required (stdlib only)
- Expects station CSV columns (case-insensitive, flexible):
  station_id/id/station, station_name/name, latitude/lat, longitude/lon/lng,
  hdd65_ann/hdd65/hdd, cdd65_ann/cdd65/cdd
- Input JSON can be either an object keyed by FIPS or an array of county entries.
  County entry should include: fips (string/number) and lat/lon for nearest-station lookup.
  If lat/lon missing, and a county centroid CSV is provided, lat/lon will be filled from that CSV.
"""

import argparse
import csv
import json
import math
import sys
from typing import Any, Dict, List, Optional, Tuple, Union


def to_float(value: Any) -> Optional[float]:
    try:
        f = float(value)
        if math.isfinite(f):
            return f
    except Exception:
        pass
    return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def read_json(path: str) -> Any:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: str, data: Any) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def lower_map(headers: List[str]) -> Dict[str, int]:
    return {h.strip().lower(): i for i, h in enumerate(headers)}


def read_stations_csv(path: str) -> List[Dict[str, Any]]:
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    if len(rows) < 2:
        return []
    header_lut = lower_map(rows[0])
    def idx(*names: str) -> Optional[int]:
        for n in names:
            i = header_lut.get(n)
            if i is not None:
                return i
        return None

    i_id = idx('station_id', 'id', 'station')
    i_name = idx('station_name', 'name')
    i_lat = idx('latitude', 'lat')
    i_lon = idx('longitude', 'lon', 'lng')
    i_hdd = idx('hdd65_ann', 'hdd65', 'hdd')
    i_cdd = idx('cdd65_ann', 'cdd65', 'cdd')
    if i_lat is None or i_lon is None:
        return []

    stations: List[Dict[str, Any]] = []
    for row in rows[1:]:
        if not row or len(row) <= max(i for i in [i_id, i_lat, i_lon] if i is not None):
            continue
        sid = row[i_id] if i_id is not None and i_id < len(row) else ''
        sname = row[i_name] if i_name is not None and i_name < len(row) else ''
        lat = to_float(row[i_lat]) if i_lat is not None else None
        lon = to_float(row[i_lon]) if i_lon is not None else None
        hdd = to_float(row[i_hdd]) if i_hdd is not None and i_hdd < len(row) else None
        cdd = to_float(row[i_cdd]) if i_cdd is not None and i_cdd < len(row) else None
        if lat is None or lon is None:
            continue
        stations.append({
            'id': sid,
            'name': sname,
            'lat': lat,
            'lon': lon,
            'hdd': hdd,
            'cdd': cdd,
        })
    return stations


def read_county_centroids_csv(path: str) -> Dict[str, Tuple[float, float]]:
    lut: Dict[str, Tuple[float, float]] = {}
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            state = (r.get('state') or r.get('State') or '').strip()
            county = (r.get('county') or r.get('County') or '').strip()
            fips = (r.get('fips') or r.get('FIPS') or '').strip()
            lat = to_float(r.get('lat') or r.get('Lat') or r.get('latitude'))
            lon = to_float(r.get('lon') or r.get('Lon') or r.get('lng') or r.get('longitude'))
            if not (lat is not None and lon is not None):
                continue
            key = fips.zfill(5) if fips else f"{state}:{county}".lower()
            lut[key] = (lat, lon)
    return lut


def normalize_counties(raw: Any) -> Dict[str, Dict[str, Any]]:
    """Return dict keyed by 5-digit FIPS with required fields."""
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(raw, dict):
        items = raw.items()
    elif isinstance(raw, list):
        items = [(None, r) for r in raw]
    else:
        raise ValueError('Unsupported JSON structure for counties')

    for key, entry in items:
        if not isinstance(entry, dict):
            continue
        fips_raw = entry.get('fips') or entry.get('FIPS') or entry.get('countyFIPS') or key
        if fips_raw is None:
            continue
        fips = str(fips_raw).zfill(5)
        name = entry.get('name') or entry.get('county_name') or ''
        state = entry.get('state') or entry.get('state_abbr') or ''
        lat = to_float(entry.get('lat'))
        lon = to_float(entry.get('lon'))
        out[fips] = {
            **entry,
            'fips': fips,
            'name': name,
            'state': state,
            'lat': lat,
            'lon': lon,
        }
    return out


def nearest_station(lat: float, lon: float, stations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    best = None
    best_d = float('inf')
    for s in stations:
        d = haversine_km(lat, lon, s['lat'], s['lon'])
        if d < best_d:
            best_d = d
            best = s
    return best


def integrate(args: argparse.Namespace) -> None:
    counties_raw = read_json(args.in_path)
    counties = normalize_counties(counties_raw)

    centroids: Dict[str, Tuple[float, float]] = {}
    if args.county_centroids:
        centroids = read_county_centroids_csv(args.county_centroids)

    stations = read_stations_csv(args.normals_csv)
    if not stations:
        print('ERROR: No stations parsed from normals CSV.', file=sys.stderr)
        sys.exit(2)

    filled = 0
    still_missing = 0
    weird: List[Tuple[str, str]] = []

    for fips, entry in counties.items():
        lat = entry.get('lat')
        lon = entry.get('lon')
        if (lat is None or lon is None) and centroids:
            key = fips
            if key in centroids:
                lat, lon = centroids[key]
                entry['lat'] = lat
                entry['lon'] = lon

        needs_hdd = not isinstance(entry.get('hdd'), (int, float))
        needs_cdd = not isinstance(entry.get('cdd'), (int, float))
        if not needs_hdd and not needs_cdd:
            continue

        if lat is None or lon is None:
            still_missing += 1
            continue

        s = nearest_station(lat, lon, stations)
        if not s:
            still_missing += 1
            continue

        # Apply rules: use available station HDD/CDD
        if needs_hdd and isinstance(s.get('hdd'), (int, float)):
            entry['hdd'] = s['hdd']
        if needs_cdd and isinstance(s.get('cdd'), (int, float)):
            entry['cdd'] = s['cdd']

        if (needs_hdd and isinstance(entry.get('hdd'), (int, float))) or \
           (needs_cdd and isinstance(entry.get('cdd'), (int, float))):
            filled += 1

        # Basic QC flags
        if isinstance(entry.get('hdd'), (int, float)) and entry['hdd'] > 15000:
            weird.append((fips, 'HDD>15000'))
        if isinstance(entry.get('cdd'), (int, float)) and entry['cdd'] > 8000:
            weird.append((fips, 'CDD>8000'))

    # Prepare output in original structure shape
    out_data: Union[Dict[str, Any], List[Any]]
    if isinstance(counties_raw, dict):
        out_data = {fips: counties[fips] for fips in counties}
    else:
        out_data = list(counties.values())

    write_json(args.out_path, out_data)
    print(f"Wrote {args.out_path} with NOAA normals merged. Filled counties: {filled}, missing after merge: {still_missing}")

    if args.qc_path:
        with open(args.qc_path, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['fips', 'issue'])
            for fips, issue in weird:
                w.writerow([fips, issue])
        print(f"QC report written to {args.qc_path} with {len(weird)} flagged entries")


def main() -> None:
    p = argparse.ArgumentParser(description='Merge NOAA HDD/CDD normals into county dataset JSON')
    p.add_argument('--in', dest='in_path', required=True, help='Input county dataset JSON')
    p.add_argument('--out', dest='out_path', required=True, help='Output JSON path')
    p.add_argument('--qc', dest='qc_path', default=None, help='Optional QC CSV output')
    p.add_argument('--normals-csv', dest='normals_csv', required=True, help='NOAA normals consolidated CSV path')
    p.add_argument('--county-centroids', dest='county_centroids', default=None, help='Optional county centroids CSV (lat/lon)')
    args = p.parse_args()
    integrate(args)


if __name__ == '__main__':
    main()


