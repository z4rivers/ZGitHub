#!/usr/bin/env python3
"""
Test the monthly normals dataset for HDD/CDD data
"""

from urllib.request import urlopen

BASE_URL = "https://www.ncei.noaa.gov/data/normals-monthly/1991-2020/access/"

try:
    print(f"Testing URL: {BASE_URL}")
    with urlopen(BASE_URL) as response:
        if response.status == 200:
            html_content = response.read().decode('utf-8')[:2000]  # First 2000 chars
            print("SUCCESS: Monthly normals URL exists")
            print(f"Sample content: {html_content}")
            
            # Try to download first file
            if '.csv' in html_content:
                print("CSV files found in directory")
                
                # Extract first CSV filename
                start = html_content.find('href="') + 6
                end = html_content.find('.csv"', start) + 4
                first_file = html_content[start:end]
                
                if first_file.endswith('.csv'):
                    print(f"Testing download: {first_file}")
                    with urlopen(BASE_URL + first_file) as test_response:
                        content = test_response.read().decode('utf-8')
                        lines = content.splitlines()
                        
                        header = lines[0]
                        columns = header.split(',')
                        
                        # Look for HDD/CDD
                        hdd_cols = [col for col in columns if 'HDD' in col]
                        cdd_cols = [col for col in columns if 'CDD' in col]
                        
                        print(f"HDD columns: {hdd_cols}")
                        print(f"CDD columns: {cdd_cols}")
                        
                        if hdd_cols and cdd_cols:
                            print("✅ SUCCESS: Monthly normals contains HDD/CDD data!")
                        else:
                            print("❌ No HDD/CDD data found")
        else:
            print(f"FAILED: HTTP {response.status}")
            
except Exception as e:
    print(f"ERROR: {e}")
