#!/usr/bin/env python3
import json
from pathlib import Path

INDEX = Path('data/master_climate_index.jsonl')

EARTH_KM = 6371.0

def hav(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, atan2, sqrt
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    c = 2*atan2(sqrt(a), sqrt(1-a))
    return EARTH_KM*c

ZIP_COORDS = {
    '97219': (45.45, -122.68),  # Portland, OR (approx SW)
    '85001': (33.45, -112.07),  # Phoenix, AZ (approx)
    '33101': (25.77, -80.20),   # Miami, FL (approx)
    '99729': (63.392, -148.95), # Cantwell, AK
}


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


def nearest(zipcode: str, recs):
    ll = ZIP_COORDS.get(zipcode)
    if not ll:
        return None
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
        return None
    return {
        'zip': zipcode,
        'lat': round(lat0,5), 'lon': round(lon0,5),
        'station': best.get('station'),
        'name': best.get('name'),
        'dist_km': round(bestkm,1),
        'hdd65': best.get('hdd65'),
        'cdd65': best.get('cdd65'),
    }


if __name__ == '__main__':
    zips = ['97219','85001','33101','99729']
    recs = load_index()
    print(json.dumps({'records': len(recs)}))
    out = [nearest(z, recs) for z in zips]
    print(json.dumps(out, indent=2))
