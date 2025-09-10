#!/usr/bin/env python3
"""
Find the closest NOAA stations to target zip codes and download their data.
"""

import csv
import math
import sys
from urllib.request import urlopen
from html.parser import HTMLParser

BASE_URL = "https://www.ncei.noaa.gov/data/normals-daily/1991-2020/access/"

# Target zip codes and their coordinates
TARGET_LOCATIONS = {
    "97219": {"lat": 45.44, "lon": -122.7, "name": "Portland, OR"},
    "97520": {"lat": 42.19, "lon": -122.71, "name": "Ashland, OR"},
    "96001": {"lat": 40.58, "lon": -122.37, "name": "Redding, CA"},
    "10001": {"lat": 40.75, "lon": -73.99, "name": "New York, NY"}
}

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr, value in attrs:
                if attr == 'href' and value.endswith('.csv'):
                    self.links.append(value)

def haversine(lon1, lat1, lon2, lat2):
    """Calculate distance in km between two points on earth."""
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    return c * 6371  # Earth radius in km

def get_station_file_list():
    """Get list of all station files from NOAA."""
    print("Getting station file list...")
    with urlopen(BASE_URL) as response:
        html_content = response.read().decode('utf-8')
        parser = LinkParser()
        parser.feed(html_content)
        print(f"Found {len(parser.links)} station files")
        return parser.links

def get_station_coordinates(station_filename):
    """Download a station file and extract its coordinates."""
    try:
        with urlopen(BASE_URL + station_filename) as response:
            content = response.read().decode('utf-8')
            lines = content.splitlines()
            if len(lines) < 2:
                return None
            
            # Parse first data line to get coordinates
            reader = csv.reader([lines[1]])
            row = next(reader)
            
            station_id = row[0]
            lat = float(row[2])
            lon = float(row[3])
            name = row[5]
            
            return {
                "id": station_id,
                "filename": station_filename,
                "lat": lat,
                "lon": lon,
                "name": name
            }
    except Exception as e:
        print(f"Error processing {station_filename}: {e}")
        return None

def find_closest_stations():
    """Find the closest station to each target location."""
    station_files = get_station_file_list()
    
    results = {}
    
    for zip_code, location in TARGET_LOCATIONS.items():
        print(f"\nFinding closest station to {zip_code} ({location['name']})...")
        
        closest_station = None
        min_distance = float('inf')
        checked = 0
        
        # Check stations in batches to show progress
        for i, filename in enumerate(station_files):
            station_data = get_station_coordinates(filename)
            if station_data:
                distance = haversine(
                    location['lon'], location['lat'],
                    station_data['lon'], station_data['lat']
                )
                
                if distance < min_distance:
                    min_distance = distance
                    closest_station = station_data
                    closest_station['distance'] = distance
                
                checked += 1
                
                # Progress update every 1000 stations
                if checked % 1000 == 0:
                    print(f"  Checked {checked} stations, closest so far: {closest_station['name']} ({min_distance:.1f} km)")
        
        results[zip_code] = closest_station
        print(f"  FINAL: {closest_station['name']} - {min_distance:.1f} km")
    
    return results

def download_station_data(stations):
    """Download the full data for the selected stations."""
    print(f"\nDownloading data for {len(stations)} stations...")
    
    with open("target_stations_data.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["zip_code", "station_id", "station_name", "latitude", "longitude", "distance_km", "filename"])
        
        for zip_code, station in stations.items():
            writer.writerow([
                zip_code,
                station['id'],
                station['name'],
                station['lat'],
                station['lon'],
                station['distance'],
                station['filename']
            ])
            print(f"  {zip_code}: {station['name']} ({station['distance']:.1f} km)")
    
    print(f"\nStation data saved to target_stations_data.csv")

if __name__ == "__main__":
    try:
        closest_stations = find_closest_stations()
        download_station_data(closest_stations)
        print("\nSUCCESS: Found and saved data for all target stations")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
