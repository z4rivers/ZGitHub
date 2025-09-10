#!/usr/bin/env python3
"""
Process local NOAA climate normal CSV files to extract HDD/CDD data
for HVAC calculator integration.
"""

import csv
import os
import json
import math
from pathlib import Path

# Target zip codes and their approximate coordinates
TARGET_LOCATIONS = {
    "97219": {"name": "Portland, OR", "lat": 45.44, "lon": -122.7},
    "97520": {"name": "Ashland, OR", "lat": 42.19, "lon": -122.71},
    "96001": {"name": "Redding, CA", "lat": 40.58, "lon": -122.37},
    "10001": {"name": "New York, NY", "lat": 40.75, "lon": -73.99}
}

def haversine(lon1, lat1, lon2, lat2):
    """Calculate the great circle distance between two points on Earth."""
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

def inventory_csv_files(data_dir):
    """
    Scan all CSV files and extract basic station information.
    Returns list of station dictionaries with coordinates and file paths.
    """
    stations = []
    csv_files = list(Path(data_dir).glob("*.csv"))
    
    print(f"Found {len(csv_files)} CSV files to process...")
    
    for i, csv_file in enumerate(csv_files):
        if i % 1000 == 0:
            print(f"Processing file {i+1}/{len(csv_files)}: {csv_file.name}")
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                # Get first row to extract station info
                first_row = next(reader)
                
                station_info = {
                    'station_id': first_row.get('STATION', ''),
                    'name': first_row.get('NAME', ''),
                    'latitude': float(first_row.get('LATITUDE', 0)),
                    'longitude': float(first_row.get('LONGITUDE', 0)),
                    'elevation': first_row.get('ELEVATION', ''),
                    'file_path': str(csv_file)
                }
                stations.append(station_info)
                
        except Exception as e:
            print(f"Error processing {csv_file.name}: {e}")
            continue
    
    print(f"Successfully processed {len(stations)} stations")
    return stations

def find_nearest_stations_with_data(stations, target_locations):
    """Find the closest station to each target location that has HDD/CDD data."""
    results = {}
    
    for zip_code, location in target_locations.items():
        print(f"  Finding station with HDD/CDD data for {zip_code} ({location['name']})...")
        min_distance = float('inf')
        best_station = None
        stations_checked = 0
        
        # Sort stations by distance first
        valid_stations = [s for s in stations if s['latitude'] != 0 and s['longitude'] != 0]
        valid_stations.sort(key=lambda s: haversine(s['longitude'], s['latitude'], location['lon'], location['lat']))
        
        for station in valid_stations:
            stations_checked += 1
            if stations_checked % 500 == 0:
                print(f"    Checked {stations_checked}/{len(valid_stations)} stations...")
            
            distance = haversine(
                station['longitude'], station['latitude'],
                location['lon'], location['lat']
            )
            
            # Check if this station has HDD/CDD data
            climate_data = extract_climate_data(station['file_path'])
            if climate_data:
                print(f"    Found data at {station['name']} ({distance:.1f} km)")
                results[zip_code] = {
                    'location_name': location['name'],
                    'station': station,
                    'distance_km': round(distance, 2),
                    'climate_data': climate_data
                }
                break
        
        if zip_code not in results:
            print(f"    WARNING: No station with HDD/CDD data found for {zip_code}")
    
    return results

def extract_climate_data(station_file_path):
    """Extract HDD and CDD data from a station's CSV file."""
    try:
        with open(station_file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Look for annual heating and cooling degree day data
                if row.get('ANN-HTDD-NORMAL') and row.get('ANN-CLDD-NORMAL'):
                    return {
                        'hdd': float(row['ANN-HTDD-NORMAL']),
                        'cdd': float(row['ANN-CLDD-NORMAL']),
                        'station_name': row.get('NAME', ''),
                        'station_id': row.get('STATION', '')
                    }
        return None
    except Exception as e:
        print(f"Error extracting data from {station_file_path}: {e}")
        return None

if __name__ == "__main__":
    # Path to the extracted CSV files
    data_directory = "us-climate-normals_2006-2020_v1.0.1_annualseasonal_multivariate_by-station_c20230404"
    
    print("Step 1: Inventorying CSV files...")
    stations = inventory_csv_files(data_directory)
    
    print(f"\nStep 2: Finding nearest stations with complete HDD/CDD data...")
    nearest_stations = find_nearest_stations_with_data(stations, TARGET_LOCATIONS)
    
    print(f"\nStep 3: Results summary:")
    climate_data = {}
    for zip_code, result in nearest_stations.items():
        print(f"\nZip {zip_code} ({result['location_name']}):")
        print(f"  Station: {result['station']['name']}")
        print(f"  Station ID: {result['station']['station_id']}")
        print(f"  Distance: {result['distance_km']} km")
        print(f"  Coordinates: {result['station']['latitude']}, {result['station']['longitude']}")
        print(f"  HDD: {result['climate_data']['hdd']}")
        print(f"  CDD: {result['climate_data']['cdd']}")
        climate_data[zip_code] = result['climate_data']
    
    # Save results
    output_file = "extracted_climate_data.json"
    with open(output_file, 'w') as f:
        json.dump({
            'nearest_stations': nearest_stations,
            'climate_data': climate_data
        }, f, indent=2)
    
    print(f"\nResults saved to {output_file}")
