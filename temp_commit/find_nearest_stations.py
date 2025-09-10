import csv
import math

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers.
    return c * r

def find_nearest_stations(targets, stations_file):
    """
    Finds the nearest station for each target coordinate.
    """
    stations = []
    with open(stations_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                stations.append({
                    "id": row['USAF'],
                    "name": row['STATION NAME'],
                    "lat": float(row['LAT']),
                    "lon": float(row['LON'])
                })
            except (ValueError, KeyError):
                continue # Skip rows with missing or invalid coordinates

    results = {}
    for name, coords in targets.items():
        min_dist = float('inf')
        closest_station = None
        for station in stations:
            dist = haversine(coords['lon'], coords['lat'], station['lon'], station['lat'])
            if dist < min_dist:
                min_dist = dist
                closest_station = station
        results[name] = {
            "zip": name.split(' ')[0],
            "closest_station_id": closest_station['id'],
            "closest_station_name": closest_station['name'],
            "distance_km": round(min_dist, 2)
        }
    return results

if __name__ == "__main__":
    target_locations = {
        "97219 (Portland, OR)": {"lat": 45.44, "lon": -122.7},
        "97520 (Ashland, OR)": {"lat": 42.19, "lon": -122.71},
        "96001 (Redding, CA)": {"lat": 40.58, "lon": -122.37},
        "10001 (New York, NY)": {"lat": 40.75, "lon": -73.99}
    }
    
    station_file_path = 'isd-history.csv'
    
    nearest = find_nearest_stations(target_locations, station_file_path)
    
    print("Found the following nearest stations:")
    for loc, data in nearest.items():
        print(f"- For {loc}:")
        print(f"  - Station ID: {data['closest_station_id']}")
        print(f"  - Station Name: {data['closest_station_name']}")
        print(f"  - Distance: {data['distance_km']} km")
