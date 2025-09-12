#!/usr/bin/env python3
"""
FastAPI service to serve small JSON responses from data/master_climate_index.min.jsonl

Endpoints:
  - GET /ping -> { ok: true }
  - GET /lookup/{zip} -> nearest station for a ZIP (HDD65, CDD65, lat, lon, station info)

Run locally:
  uvicorn scripts.noaa_api_service:app --reload

Notes:
  - Loads the minimal JSONL once at startup into memory (list of dicts)
  - Uses a simple LRU cache for ZIP lookups
  - Resolves ZIP to lat/lon using Zippopotam; falls back to RESNET_ASHRAE_DATA if available
"""
from __future__ import annotations

import json
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

DATA_PATH = Path("data/master_climate_index.min.jsonl")


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, str):
            v = value.strip()
            if not v or v.upper() in {"NA", "N/A", "-9999", "-9999.0"}:
                return None
            return float(v)
        return float(value)
    except Exception:
        return None


def _load_min_index(path: Path) -> List[Dict[str, Any]]:
    t0 = time.time()
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset: {path}")
    recs: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            try:
                o = json.loads(s)
            except Exception:
                continue
            lat = _to_float(o.get("lat"))
            lon = _to_float(o.get("lon"))
            if lat is None or lon is None:
                continue
            recs.append({
                "station": o.get("station"),
                "name": o.get("name"),
                "lat": lat,
                "lon": lon,
                "hdd65": _to_float(o.get("hdd65")),
                "cdd65": _to_float(o.get("cdd65")),
            })
    t1 = time.time()
    print(f"[load] loaded {len(recs):,} stations from {path} in {t1 - t0:.2f}s")
    return recs


app = FastAPI(title="NOAA Climate Index API", version="0.1.0")
# CORS for local static site
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
_STATIONS: List[Dict[str, Any]] = _load_min_index(DATA_PATH)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import radians, sin, cos, atan2, sqrt
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    c = 2*atan2(sqrt(1 - a), sqrt(a)) if a > 1 else 2*atan2(sqrt(a), sqrt(1 - a))
    return 6371.0 * c


@lru_cache(maxsize=4096)
def _zip_to_latlon(zipcode: str) -> Optional[Dict[str, float]]:
    zipcode = zipcode.strip()
    if len(zipcode) != 5 or not zipcode.isdigit():
        return None
    url = f"https://api.zippopotam.us/us/{zipcode}"
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(url)
            if r.status_code != 200:
                return None
            js = r.json()
            places = js.get("places") or []
            if not places:
                return None
            lat = _to_float(places[0].get("latitude"))
            lon = _to_float(places[0].get("longitude"))
            if lat is None or lon is None:
                return None
            return {"lat": lat, "lon": lon}
    except Exception:
        return None


@lru_cache(maxsize=8192)
def _nearest_for_zip(zipcode: str) -> Optional[Dict[str, Any]]:
    ll = _zip_to_latlon(zipcode)
    if not ll:
        return None
    lat0, lon0 = ll["lat"], ll["lon"]
    best = None
    bestkm = float("inf")
    for r in _STATIONS:
        lat = r.get("lat"); lon = r.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue
        d = _haversine_km(lat0, lon0, float(lat), float(lon))
        if d < bestkm:
            bestkm = d
            best = r
    if best is None:
        return None
    return {
        "zip": zipcode,
        "lat": round(lat0, 5),
        "lon": round(lon0, 5),
        "station": best.get("station"),
        "name": best.get("name"),
        "dist_km": round(bestkm, 1),
        "hdd65": best.get("hdd65"),
        "cdd65": best.get("cdd65"),
    }


@app.get("/ping")
def ping() -> Dict[str, Any]:
    return {"ok": True, "stations": len(_STATIONS)}


@app.get("/lookup/{zipcode}")
def lookup_zip(zipcode: str) -> Dict[str, Any]:
    t0 = time.time()
    res = _nearest_for_zip(zipcode)
    if not res:
        raise HTTPException(status_code=404, detail="ZIP not found or no nearby station")
    res["elapsed_ms"] = int((time.time() - t0) * 1000)
    return res


