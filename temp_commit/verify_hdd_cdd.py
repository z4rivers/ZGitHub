#!/usr/bin/env python3
"""
Verify that the annual normals dataset contains HDD/CDD data
"""

from urllib.request import urlopen

BASE_URL = "https://www.ncei.noaa.gov/data/normals-annualseasonal/1991-2020/access/"

try:
    # Download first file to check complete header
    with urlopen(BASE_URL + "AQC00914000.csv") as response:
        content = response.read().decode('utf-8')
        lines = content.splitlines()
        
        print(f"File has {len(lines)} lines")
        header = lines[0]
        print(f"Complete header length: {len(header)} characters")
        
        # Split header into columns
        columns = header.split(',')
        print(f"Number of columns: {len(columns)}")
        
        # Look for HDD/CDD columns
        hdd_columns = [col for col in columns if 'HDD' in col]
        cdd_columns = [col for col in columns if 'CDD' in col]
        
        print(f"\nHDD columns found: {hdd_columns}")
        print(f"CDD columns found: {cdd_columns}")
        
        # Show all column names that contain key terms
        key_terms = ['TEMP', 'HDD', 'CDD', 'HEAT', 'COOL']
        relevant_cols = []
        for col in columns:
            for term in key_terms:
                if term in col.upper():
                    relevant_cols.append(col)
                    break
        
        print(f"\nAll temperature/degree day related columns:")
        for col in relevant_cols:
            print(f"  {col}")
            
        # Check if we have the data we need
        has_hdd = any('HDD' in col for col in columns)
        has_cdd = any('CDD' in col for col in columns)
        
        print(f"\nDATA VERIFICATION:")
        print(f"Contains HDD data: {has_hdd}")
        print(f"Contains CDD data: {has_cdd}")
        
        if has_hdd and has_cdd:
            print("✅ SUCCESS: This dataset contains the HDD/CDD data we need!")
        else:
            print("❌ FAILURE: This dataset does NOT contain the HDD/CDD data we need.")
            
except Exception as e:
    print(f"ERROR: {e}")
