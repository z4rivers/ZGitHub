#!/usr/bin/env python3
"""
Check progress of climate database building.
"""
import json
from pathlib import Path

def check_progress():
    progress_file = "climate_db_progress.json"
    
    if not Path(progress_file).exists():
        print("No progress file found. Database building not started.")
        return
    
    with open(progress_file, 'r') as f:
        progress_data = json.load(f)
    
    total_files = progress_data.get('total_files', 0)
    completed_files = progress_data.get('completed_files', 0)
    stations_found = len(progress_data.get('stations', []))
    
    if completed_files > 0:
        percentage = (completed_files / total_files) * 100
        print(f"Progress: {completed_files}/{total_files} files ({percentage:.1f}%)")
        print(f"Stations with HDD/CDD data found: {stations_found}")
        
        if completed_files == total_files:
            print("✅ Database building COMPLETE!")
        else:
            print("🔄 Database building in progress...")
    else:
        print("Database building started but no progress yet.")

if __name__ == "__main__":
    check_progress()
