#!/usr/bin/env python3
"""
Expand county coverage by adding major counties with NOAA HDD/CDD data
"""

import json
import math

def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km"""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def find_nearest_station(lat, lon, stations):
    """Find the nearest weather station to coordinates"""
    if not stations or lat is None or lon is None:
        return None
    
    best_station = None
    best_distance = float('inf')
    
    for station in stations:
        if station.get('hdd') is None or station.get('cdd') is None:
            continue
            
        distance = haversine_km(lat, lon, station['latitude'], station['longitude'])
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
    
    # Major US counties with approximate coordinates
    major_counties = {
        '36061': {'name': 'New York County, NY', 'state': 'NY', 'lat': 40.7589, 'lon': -73.9851},
        '06037': {'name': 'Los Angeles County, CA', 'state': 'CA', 'lat': 34.0522, 'lon': -118.2437},
        '17031': {'name': 'Cook County, IL', 'state': 'IL', 'lat': 41.8781, 'lon': -87.6298},
        '48201': {'name': 'Harris County, TX', 'state': 'TX', 'lat': 29.7604, 'lon': -95.3698},
        '12086': {'name': 'Miami-Dade County, FL', 'state': 'FL', 'lat': 25.7617, 'lon': -80.1918},
        '13135': {'name': 'Fulton County, GA', 'state': 'GA', 'lat': 33.7490, 'lon': -84.3880},
        '04013': {'name': 'Maricopa County, AZ', 'state': 'AZ', 'lat': 33.4484, 'lon': -112.0740},
        '53033': {'name': 'King County, WA', 'state': 'WA', 'lat': 47.6062, 'lon': -122.3321},
        '25025': {'name': 'Suffolk County, MA', 'state': 'MA', 'lat': 42.3601, 'lon': -71.0589},
        '06059': {'name': 'Orange County, CA', 'state': 'CA', 'lat': 33.7175, 'lon': -117.8311},
        '12011': {'name': 'Broward County, FL', 'state': 'FL', 'lat': 26.1224, 'lon': -80.1373},
        '48029': {'name': 'Bexar County, TX', 'state': 'TX', 'lat': 29.4241, 'lon': -98.4936},
        '06067': {'name': 'Sacramento County, CA', 'state': 'CA', 'lat': 38.5816, 'lon': -121.4944},
        '39049': {'name': 'Franklin County, OH', 'state': 'OH', 'lat': 39.9612, 'lon': -82.9988},
        '42101': {'name': 'Philadelphia County, PA', 'state': 'PA', 'lat': 39.9526, 'lon': -75.1652}
    }
    
    # Generate county data with NOAA HDD/CDD
    county_data = {}
    
    for fips, info in major_counties.items():
        nearest = find_nearest_station(info['lat'], info['lon'], noaa_data)
        if nearest:
            # Estimate heating/cooling design temps based on HDD/CDD
            hdd = int(nearest['hdd']) if nearest['hdd'] is not None else 0
            cdd = int(nearest['cdd']) if nearest['cdd'] is not None else 0
            
            # Rough estimates for design temps based on degree days
            if hdd > 6000:
                heating = max(0, 20 - (hdd - 6000) / 1000 * 5)  # Very cold
            elif hdd > 4000:
                heating = max(10, 25 - (hdd - 4000) / 2000 * 10)  # Cold
            elif hdd > 2000:
                heating = max(20, 30 - (hdd - 2000) / 2000 * 10)  # Moderate
            else:
                heating = max(30, 40 - hdd / 2000 * 10)  # Warm
            
            if cdd > 3000:
                cooling = min(110, 95 + (cdd - 3000) / 1000 * 5)  # Very hot
            elif cdd > 1500:
                cooling = min(100, 90 + (cdd - 1500) / 1500 * 10)  # Hot
            elif cdd > 500:
                cooling = min(95, 85 + (cdd - 500) / 1000 * 10)  # Moderate
            else:
                cooling = min(90, 80 + cdd / 500 * 10)  # Cool
            
            county_data[fips] = {
                'name': info['name'],
                'state': info['state'],
                'fips': fips,
                'heating': int(heating),
                'cooling': int(cooling),
                'hdd': hdd,
                'cdd': cdd,
                'source': f'NOAA HDD/CDD + estimated design temps (station: {nearest["station_id"]})',
                'lat': info['lat'],
                'lon': info['lon']
            }
            print(f"Added {info['name']}: HDD={hdd}, CDD={cdd}, Heating={int(heating)}°F, Cooling={int(cooling)}°F")
    
    # Write expanded county data
    print(f"\nWriting expanded county data with {len(county_data)} counties...")
    with open('ashrae_county_data_expanded.js', 'w') as f:
        f.write("// ASHRAE COUNTY-LEVEL DESIGN DATA (Expanded with NOAA HDD/CDD)\n")
        f.write("// Major US counties with real degree days data\n\n")
        f.write("const ASHRAE_COUNTY_DATA = {\n")
        
        for fips, data in county_data.items():
            f.write(f"  '{fips}': {{\n")
            f.write(f"    name: '{data['name']}',\n")
            f.write(f"    state: '{data['state']}',\n")
            f.write(f"    fips: '{fips}',\n")
            f.write(f"    heating: {data['heating']}, // 99% heating design temp (estimated from HDD)\n")
            f.write(f"    cooling: {data['cooling']}, // 1% cooling design temp (estimated from CDD)\n")
            f.write(f"    hdd: {data['hdd']},   // HDD base 65°F (NOAA station: {data['source'].split('station: ')[1].split(')')[0]})\n")
            f.write(f"    cdd: {data['cdd']},   // CDD base 65°F (NOAA station: {data['source'].split('station: ')[1].split(')')[0]})\n")
            f.write(f"    source: '{data['source']}',\n")
            f.write(f"    lat: {data['lat']},\n")
            f.write(f"    lon: {data['lon']}\n")
            f.write("  },\n")
        
        f.write("};\n\n")
        f.write("if (typeof module !== 'undefined' && module.exports) {\n")
        f.write("  module.exports = ASHRAE_COUNTY_DATA;\n")
        f.write("}\n")
    
    print("Expansion complete! File saved as ashrae_county_data_expanded.js")

if __name__ == '__main__':
    main()
