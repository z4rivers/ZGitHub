#!/usr/bin/env python3
"""
Test if the annual/seasonal normals URL exists and contains HDD/CDD data
"""

from urllib.request import urlopen
from html.parser import HTMLParser

BASE_URL = "https://www.ncei.noaa.gov/data/normals-annualseasonal/1991-2020/access/"

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr, value in attrs:
                if attr == 'href' and value.endswith('.csv'):
                    self.links.append(value)

try:
    print(f"Testing URL: {BASE_URL}")
    with urlopen(BASE_URL) as response:
        if response.status == 200:
            html_content = response.read().decode('utf-8')
            parser = LinkParser()
            parser.feed(html_content)
            print(f"SUCCESS: Found {len(parser.links)} CSV files")
            print(f"First 5 files: {parser.links[:5]}")
            
            # Test download one file to check content
            if parser.links:
                test_file = parser.links[0]
                print(f"\nTesting download of: {test_file}")
                with urlopen(BASE_URL + test_file) as test_response:
                    content = test_response.read().decode('utf-8')
                    lines = content.splitlines()
                    print(f"File has {len(lines)} lines")
                    print(f"Header: {lines[0]}")
                    if len(lines) > 1:
                        print(f"First data line: {lines[1]}")
        else:
            print(f"FAILED: HTTP {response.status}")
            
except Exception as e:
    print(f"ERROR: {e}")
    print("Annual/seasonal normals URL does not exist or is inaccessible")
