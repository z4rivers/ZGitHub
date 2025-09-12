NOAA Climate Index API (FastAPI)

Serve small JSON lookups from `data/master_climate_index.min.jsonl` so the web app can fetch HDD/CDD by ZIP without downloading the full dataset.

Endpoints
- GET `/ping` → health check ({ ok: true, stations })
- GET `/lookup/{zip}` → nearest station for ZIP (hdd65, cdd65, lat, lon, dist_km, station info)

Run locally
```bash
uvicorn scripts.noaa_api_service:app --reload
```

Install deps
```bash
pip install -r requirements.txt
```

Notes
- Loads the minimal JSONL once at startup and keeps it in memory
- ZIP→lat/lon resolved via Zippopotam; results cached with LRU
- Typical response latency: <100 ms after warm-up

