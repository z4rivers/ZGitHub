#!/usr/bin/env python3
import json, sys
from pathlib import Path

INDEX = Path('data/master_climate_index.jsonl')
EARTH_KM = 6371.0

ZIP_COORDS = {
    '97219': (45.45, -122.68),
    '85001': (33.45, -112.07),
    '33101': (25.77, -80.20),
    '99729': (63.392, -148.95),
}

def hav(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, atan2, sqrt
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    c = 2*atan2(sqrt(a), sqrt(1-a))
    return EARTH_KM*c


def load_index():
    recs = []
    with INDEX.open('r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                recs.append(json.loads(s))
            except Exception:
                continue
    return recs


def nearest_for_zip(zipcode: str, recs):
    ll = ZIP_COORDS.get(zipcode)
    if not ll:
        return { 'zip': zipcode, 'error': 'no_coords' }
    lat0, lon0 = ll
    best, bestkm = None, float('inf')
    for r in recs:
        lat = r.get('lat'); lon = r.get('lon')
        if not isinstance(lat, (int,float)) or not isinstance(lon, (int,float)):
            continue
        d = hav(lat0, lon0, lat, lon)
        if d < bestkm:
            bestkm = d; best = r
    if best is None:
        return { 'zip': zipcode, 'error': 'no_station' }
    return {
        'zip': zipcode,
        'lat': round(lat0,5), 'lon': round(lon0,5),
        'station': best.get('station'),
        'name': best.get('name'),
        'dist_km': round(bestkm,1),
        'hdd65': best.get('hdd65'),
        'cdd65': best.get('cdd65'),
    }


def main(argv):
    zips = argv[1:] or ['97219','85001','33101','99729']
    recs = load_index()
    out = [nearest_for_zip(z, recs) for z in zips]
    print(json.dumps({ 'records': len(recs), 'results': out }, indent=2))


if __name__ == '__main__':
    main(sys.argv)

