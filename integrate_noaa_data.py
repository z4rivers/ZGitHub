#!/usr/bin/env python3
"""
Integrate NOAA HDD/CDD data into ashrae_county_data.js
"""

import json
import re
import math

def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km"""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def find_nearest_station(county_lat, county_lon, stations):
    """Find the nearest weather station to a county"""
    if not stations or county_lat is None or county_lon is None:
        return None
    
    best_station = None
    best_distance = float('inf')
    
    for station in stations:
        if station.get('hdd') is None or station.get('cdd') is None:
            continue
            
        distance = haversine_km(county_lat, county_lon, station['latitude'], station['longitude'])
        if distance < best_distance:
            best_distance = distance
            best_station = station
    
    return best_station

def main():
    # Load NOAA data
    print("Loading NOAA climate database...")
    with open('temp_commit/noaa_climate_database.json', 'r') as f:
        noaa_data = json.load(f)
    print(f"Loaded {len(noaa_data)} NOAA stations")
    
    # Load current county data
    print("Loading county data...")
    with open('ashrae_county_data.js', 'r') as f:
        county_js = f.read()
    
    # Extract county data using regex
    county_pattern = r"'(\d{5})':\s*\{([^}]+)\}"
    counties = {}
    
    for match in re.finditer(county_pattern, county_js):
        fips = match.group(1)
        content = match.group(2)
        
        # Extract lat/lon from the content
        lat_match = re.search(r'lat:\s*([0-9.-]+)', content)
        lon_match = re.search(r'lon:\s*([0-9.-]+)', content)
        
        if lat_match and lon_match:
            lat = float(lat_match.group(1))
            lon = float(lon_match.group(1))
            counties[fips] = {'lat': lat, 'lon': lon, 'content': content}
    
    print(f"Found {len(counties)} counties with coordinates")
    
    # Find nearest stations for each county
    updated_counties = 0
    for fips, county in counties.items():
        nearest = find_nearest_station(county['lat'], county['lon'], noaa_data)
        if nearest:
            # Check if county already has HDD/CDD
            has_hdd = 'hdd:' in county['content']
            has_cdd = 'cdd:' in county['content']
            
            if not has_hdd or not has_cdd:
                # Add HDD/CDD data
                hdd_value = int(nearest['hdd']) if nearest['hdd'] is not None else 0
                cdd_value = int(nearest['cdd']) if nearest['cdd'] is not None else 0
                
                # Update the content
                new_content = county['content']
                if not has_hdd:
                    new_content += f",\n    hdd: {hdd_value},   // HDD base 65°F (NOAA station: {nearest['station_id']})"
                if not has_cdd:
                    new_content += f",\n    cdd: {cdd_value},   // CDD base 65°F (NOAA station: {nearest['station_id']})"
                
                # Update source
                if 'source:' in new_content:
                    new_content = re.sub(r'source:\s*[^,]+', f"source: 'NOAA HDD/CDD + {nearest['station_id']}'", new_content)
                
                counties[fips]['content'] = new_content
                updated_counties += 1
                print(f"Updated {fips}: HDD={hdd_value}, CDD={cdd_value} (station: {nearest['station_id']})")
    
    print(f"Updated {updated_counties} counties with NOAA HDD/CDD data")
    
    # Write updated county data
    print("Writing updated county data...")
    with open('ashrae_county_data_updated.js', 'w') as f:
        f.write("// ASHRAE COUNTY-LEVEL DESIGN DATA (Authoritative)\n")
        f.write("// Updated with NOAA HDD/CDD data\n\n")
        f.write("const ASHRAE_COUNTY_DATA = {\n")
        
        for fips, county in counties.items():
            f.write(f"  '{fips}': {{\n")
            f.write(f"    {county['content']}\n")
            f.write("  },\n")
        
        f.write("};\n\n")
        f.write("if (typeof module !== 'undefined' && module.exports) {\n")
        f.write("  module.exports = ASHRAE_COUNTY_DATA;\n")
        f.write("}\n")
    
    print("Integration complete! Updated file saved as ashrae_county_data_updated.js")

if __name__ == '__main__':
    main()
