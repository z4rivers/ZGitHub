#!/usr/bin/env python3
"""
Test script to get the list of station files from NOAA and extract station IDs.
This tests the connection and file listing without downloading data.
"""

import sys
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

def extract_station_ids(filenames: list[str]) -> list[str]:
    """Extract station IDs from CSV filenames."""
    station_ids = []
    for filename in filenames:
        # Remove .csv extension to get station ID
        if filename.endswith('.csv'):
            station_id = filename[:-4]  # Remove last 4 characters (.csv)
            station_ids.append(station_id)
    return station_ids

if __name__ == "__main__":
    # Test 1: Get the list of files
    print("=== TEST 1: Getting station file list ===")
    station_files = get_station_file_list(BASE_URL)
    
    if not station_files:
        print("FAILED: Could not get station file list")
        sys.exit(1)
    
    print(f"SUCCESS: Retrieved {len(station_files)} station files")
    print(f"First 5 files: {station_files[:5]}")
    
    # Test 2: Extract station IDs
    print("\n=== TEST 2: Extracting station IDs ===")
    station_ids = extract_station_ids(station_files)
    print(f"SUCCESS: Extracted {len(station_ids)} station IDs")
    print(f"First 5 station IDs: {station_ids[:5]}")
    
    # Test 3: Try to download just ONE file to verify the format
    print("\n=== TEST 3: Testing download of one file ===")
    test_filename = station_files[0]
    test_url = BASE_URL + test_filename
    
    try:
        with urlopen(test_url) as response:
            if response.status == 200:
                content = response.read().decode('utf-8')
                lines = content.splitlines()
                print(f"SUCCESS: Downloaded {test_filename}")
                print(f"File has {len(lines)} lines")
                print(f"Header: {lines[0] if lines else 'NO HEADER'}")
                print(f"First data line: {lines[1] if len(lines) > 1 else 'NO DATA'}")
            else:
                print(f"FAILED: HTTP {response.status} for {test_url}")
    except Exception as e:
        print(f"FAILED: Could not download test file: {e}")
    
    print("\n=== TEST COMPLETE ===")
