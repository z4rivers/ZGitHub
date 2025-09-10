#!/usr/bin/env python3
"""
Build a comprehensive climate database from all NOAA stations with HDD/CDD data.
This creates a lookup table for any zip code in the calculator.
"""

import csv
import json
import math
from pathlib import Path

def haversine(lon1, lat1, lon2, lat2):
    """Calculate distance between two points on Earth in kilometers."""
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return c * 6371  # Earth radius in km

def extract_station_climate_data(csv_file):
    """Extract station info and climate data if available."""
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            first_row = next(reader)
            
            # Check if this station has HDD/CDD data
            hdd_value = first_row.get('ANN-HTDD-NORMAL', '').strip()
            cdd_value = first_row.get('ANN-CLDD-NORMAL', '').strip()
            
            if not hdd_value or not cdd_value:
                return None  # Skip stations without HDD/CDD data
            
            try:
                hdd = float(hdd_value)
                cdd = float(cdd_value)
            except ValueError:
                return None  # Skip if values aren't numeric
            
            # Extract station information
            station_data = {
                'station_id': first_row.get('STATION', '').strip(),
                'name': first_row.get('NAME', '').strip(),
                'latitude': float(first_row.get('LATITUDE', 0)),
                'longitude': float(first_row.get('LONGITUDE', 0)),
                'elevation': first_row.get('ELEVATION', '').strip(),
                'hdd': hdd,
                'cdd': cdd
            }
            
            # Skip stations with invalid coordinates
            if station_data['latitude'] == 0 and station_data['longitude'] == 0:
                return None
                
            return station_data
            
    except Exception as e:
        print(f"Error processing {csv_file.name}: {e}")
        return None

def build_climate_database(data_dir, batch_size=1000):
    """Process all CSV files and build comprehensive climate database with resumability."""
    csv_files = list(Path(data_dir).glob("*.csv"))
    stations_with_data = []
    
    # Check for existing progress file
    progress_file = "climate_db_progress.json"
    processed_files = set()
    
    if Path(progress_file).exists():
        with open(progress_file, 'r') as f:
            progress_data = json.load(f)
            stations_with_data = progress_data.get('stations', [])
            processed_files = set(progress_data.get('processed_files', []))
        print(f"Resuming: {len(stations_with_data)} stations already found, {len(processed_files)} files processed")
    
    remaining_files = [f for f in csv_files if str(f) not in processed_files]
    print(f"Processing {len(remaining_files)} remaining files out of {len(csv_files)} total...")
    
    for i, csv_file in enumerate(remaining_files):
        if i % 100 == 0:  # More frequent updates
            print(f"  Batch progress: {i}/{len(remaining_files)} files, found {len(stations_with_data)} total stations")
        
        station_data = extract_station_climate_data(csv_file)
        if station_data:
            stations_with_data.append(station_data)
        
        processed_files.add(str(csv_file))
        
        # Save progress every batch_size files
        if (i + 1) % batch_size == 0:
            with open(progress_file, 'w') as f:
                json.dump({
                    'stations': stations_with_data,
                    'processed_files': list(processed_files),
                    'total_files': len(csv_files),
                    'completed_files': len(processed_files)
                }, f)
            print(f"  Progress saved: {len(processed_files)}/{len(csv_files)} files processed")
    
    # Final save
    with open(progress_file, 'w') as f:
        json.dump({
            'stations': stations_with_data,
            'processed_files': list(processed_files),
            'total_files': len(csv_files),
            'completed_files': len(processed_files)
        }, f)
    
    print(f"\nCompleted! Found {len(stations_with_data)} stations with complete HDD/CDD data")
    return stations_with_data

def find_nearest_station(target_lat, target_lon, stations_db):
    """Find the nearest station to given coordinates."""
    min_distance = float('inf')
    nearest_station = None
    
    for station in stations_db:
        distance = haversine(station['longitude'], station['latitude'], target_lon, target_lat)
        if distance < min_distance:
            min_distance = distance
            nearest_station = station
    
    if nearest_station:
        return {
            'station': nearest_station,
            'distance_km': round(min_distance, 2)
        }
    return None

if __name__ == "__main__":
    data_directory = "us-climate-normals_2006-2020_v1.0.1_annualseasonal_multivariate_by-station_c20230404"
    
    print("Building comprehensive climate database...")
    climate_stations = build_climate_database(data_directory)
    
    # Save the complete database
    database_file = "noaa_climate_database.json"
    with open(database_file, 'w') as f:
        json.dump(climate_stations, f, indent=2)
    
    print(f"Database saved to {database_file}")
    print(f"Database contains {len(climate_stations)} stations with HDD/CDD data")
    
    # Test with our original 4 zip codes
    test_locations = {
        "97219": {"name": "Portland, OR", "lat": 45.44, "lon": -122.7},
        "97520": {"name": "Ashland, OR", "lat": 42.19, "lon": -122.71},
        "96001": {"name": "Redding, CA", "lat": 40.58, "lon": -122.37},
        "10001": {"name": "New York, NY", "lat": 40.75, "lon": -73.99}
    }
    
    print(f"\nTesting with sample zip codes:")
    test_results = {}
    for zip_code, location in test_locations.items():
        result = find_nearest_station(location['lat'], location['lon'], climate_stations)
        if result:
            station = result['station']
            test_results[zip_code] = result
            print(f"\n{zip_code} ({location['name']}):")
            print(f"  Station: {station['name']}")
            print(f"  Distance: {result['distance_km']} km")
            print(f"  HDD: {station['hdd']}, CDD: {station['cdd']}")
    
    # Save test results
    with open("test_climate_results.json", 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\nTest results saved to test_climate_results.json")
