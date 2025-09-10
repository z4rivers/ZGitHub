#!/usr/bin/env python3
"""
Fetch and consolidate NOAA 1991–2020 Climate Normals (HDD/CDD) into a single CSV.

This script now fetches the directory listing of individual station files,
downloads each one, extracts the annual degree day data, and consolidates
it into the single CSV file required by the application.

Output CSV schema:
  station_id, station_name, latitude, longitude, hdd65_ann, cdd65_ann

Usage:
  python fetch_noaa_normals.py --out noaa_normals_hdd_cdd_1991_2020.csv
"""

import argparse
import csv
import sys
import re
from pathlib import Path
from urllib.request import urlopen
from html.parser import HTMLParser

# The base URL for the directory containing individual station CSVs
BASE_URL = "https://www.ncei.noaa.gov/data/normals-daily/1991-2020/access/"

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr, value in attrs:
                if attr == 'href' and value.endswith('.csv'):
                    self.links.append(value)

def get_station_file_list(url: str) -> list[str]:
    """Fetch the list of CSV files from the NOAA directory page."""
    try:
        print(f"Fetching directory listing from {url} ...")
        with urlopen(url) as response:
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status} for {url}")
            html_content = response.read().decode('utf-8')
            parser = LinkParser()
            parser.feed(html_content)
            print(f"Found {len(parser.links)} station files.")
            return parser.links
    except Exception as e:
        print(f"Could not fetch directory listing: {e}", file=sys.stderr)
        return []

def get_processed_stations(path: Path) -> set[str]:
    """Reads an existing output file and returns a set of processed station IDs."""
    if not path.is_file():
        return set()
    
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # Skip header
        return {row[0] for row in reader if row}

def process_station_file(file_content: str) -> dict | None:
    """Extracts the single row of annual degree day data from a station's CSV."""
    try:
        reader = csv.reader(file_content.splitlines())
        header = next(reader)
        # Find the columns we need, case-insensitive
        h = {col.strip().lower(): i for i, col in enumerate(header)}
        
        # Required columns for our output
        lat_idx = h.get('latitude')
        lon_idx = h.get('longitude')
        station_idx = h.get('station')
        name_idx = h.get('name')
        
        # Find the annual degree day columns
        hdd_idx = h.get('ann-hdd-normal')
        cdd_idx = h.get('ann-cdd-normal')

        if any(idx is None for idx in [lat_idx, lon_idx, station_idx, name_idx, hdd_idx, cdd_idx]):
            return None # Skip files missing critical columns

        # The data we want is usually on the first data row.
        for row in reader:
            # We only care about the annual summary, which has an empty 'DATE' field
            if 'date' in h and row[h['date']] == '':
                return {
                    "station_id": row[station_idx],
                    "station_name": row[name_idx],
                    "latitude": row[lat_idx],
                    "longitude": row[lon_idx],
                    "hdd65_ann": row[hdd_idx],
                    "cdd65_ann": row[cdd_idx]
                }
        return None
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch and consolidate NOAA normals HDD/CDD from individual station files.")
    ap.add_argument("--out", default="noaa_normals_hdd_cdd_1991_2020.csv", help="Output CSV path")
    ap.add_argument("--limit", type=int, default=0, help="Limit the number of stations to process (for testing)")
    args = ap.parse_args()

    out_path = Path(args.out)
    
    # Get the list of station files to process
    station_files = get_station_file_list(BASE_URL)
    if not station_files:
        print("Could not retrieve station file list. Aborting.", file=sys.stderr)
        sys.exit(1)

    # Get the set of already processed stations to make the script resumable
    processed_stations = get_processed_stations(out_path)
    if processed_stations:
        print(f"Found {len(processed_stations)} stations in existing output file. Will skip them.")

    # Filter out already processed files
    files_to_process = [f for f in station_files if f.replace(".csv", "") not in processed_stations]
    
    # Apply the limit if one was provided
    if args.limit > 0:
        files_to_process = files_to_process[:args.limit]
        print(f"Processing a limited set of {len(files_to_process)} stations.")

    if not files_to_process:
        print("All stations are already processed. Nothing to do.")
        sys.exit(0)

    # Open in append mode and write header only if the file is new
    file_exists = out_path.is_file()
    with out_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["station_id", "station_name", "latitude", "longitude", "hdd65_ann", "cdd65_ann"])
        
        processed_count = 0
        total_to_process = len(files_to_process)
        for i, filename in enumerate(files_to_process):
            file_url = BASE_URL + filename
            try:
                with urlopen(file_url) as response:
                    if response.status == 200:
                        content = response.read().decode('utf-8')
                        data = process_station_file(content)
                        if data:
                            writer.writerow([
                                data['station_id'],
                                data['station_name'],
                                data['latitude'],
                                data['longitude'],
                                data['hdd65_ann'],
                                data['cdd65_ann']
                            ])
                            processed_count += 1
                # Progress update
                if (i + 1) % 100 == 0:
                    print(f"Processed {i + 1}/{total_to_process} files...")
                    f.flush()  # Force write to disk

            except Exception as e:
                print(f"  - Skipping {filename} due to error: {e}", file=sys.stderr)
    
    print(f"\nDone. Wrote data for {processed_count} new stations to {out_path}")

if __name__ == "__main__":
    main()


