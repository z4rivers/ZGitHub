// ASHRAE COUNTY-LEVEL DESIGN DATA (Expanded with NOAA HDD/CDD)
// Major US counties with real degree days data

const ASHRAE_COUNTY_DATA = {
  '36061': {
    name: 'New York County, NY',
    state: 'NY',
    fips: '36061',
    heating: 22, // 99% heating design temp (estimated from HDD)
    cooling: 92, // 1% cooling design temp (estimated from CDD)
    hdd: 4441,   // HDD base 65°F (NOAA station: USW00094728)
    cdd: 1269,   // CDD base 65°F (NOAA station: USW00094728)
    source: 'NOAA HDD/CDD + estimated design temps (station: USW00094728)',
    lat: 40.7589,
    lon: -73.9851
  },
  '06037': {
    name: 'Los Angeles County, CA',
    state: 'CA',
    fips: '06037',
    heating: 35, // 99% heating design temp (estimated from HDD)
    cooling: 94, // 1% cooling design temp (estimated from CDD)
    hdd: 883,   // HDD base 65°F (NOAA station: USW00093134)
    cdd: 1475,   // CDD base 65°F (NOAA station: USW00093134)
    source: 'NOAA HDD/CDD + estimated design temps (station: USW00093134)',
    lat: 34.0522,
    lon: -118.2437
  },
  '17031': {
    name: 'Cook County, IL',
    state: 'IL',
    fips: '17031',
    heating: 19, // 99% heating design temp (estimated from HDD)
    cooling: 88, // 1% cooling design temp (estimated from CDD)
    hdd: 6007,   // HDD base 65°F (NOAA station: USC00111550)
    cdd: 877,   // CDD base 65°F (NOAA station: USC00111550)
    source: 'NOAA HDD/CDD + estimated design temps (station: USC00111550)',
    lat: 41.8781,
    lon: -87.6298
  },
  '48201': {
    name: 'Harris County, TX',
    state: 'TX',
    fips: '48201',
    heating: 34, // 99% heating design temp (estimated from HDD)
    cooling: 97, // 1% cooling design temp (estimated from CDD)
    hdd: 1060,   // HDD base 65°F (NOAA station: USW00012918)
    cdd: 3465,   // CDD base 65°F (NOAA station: USW00012918)
    source: 'NOAA HDD/CDD + estimated design temps (station: USW00012918)',
    lat: 29.7604,
    lon: -95.3698
  },
  '12086': {
    name: 'Miami-Dade County, FL',
    state: 'FL',
    fips: '12086',
    heating: 39, // 99% heating design temp (estimated from HDD)
    cooling: 102, // 1% cooling design temp (estimated from CDD)
    hdd: 114,   // HDD base 65°F (NOAA station: USW00092811)
    cdd: 4479,   // CDD base 65°F (NOAA station: USW00092811)
    source: 'NOAA HDD/CDD + estimated design temps (station: USW00092811)',
    lat: 25.7617,
    lon: -80.1918
  },
  '13135': {
    name: 'Fulton County, GA',
    state: 'GA',
    fips: '13135',
    heating: 26, // 99% heating design temp (estimated from HDD)
    cooling: 92, // 1% cooling design temp (estimated from CDD)
    hdd: 2704,   // HDD base 65°F (NOAA station: USW00003888)
    cdd: 1926,   // CDD base 65°F (NOAA station: USW00003888)
    source: 'NOAA HDD/CDD + estimated design temps (station: USW00003888)',
    lat: 33.749,
    lon: -84.388
  },
  '04013': {
    name: 'Maricopa County, AZ',
    state: 'AZ',
    fips: '04013',
    heating: 35, // 99% heating design temp (estimated from HDD)
    cooling: 104, // 1% cooling design temp (estimated from CDD)
    hdd: 836,   // HDD base 65°F (NOAA station: USW00023183)
    cdd: 4884,   // CDD base 65°F (NOAA station: USW00023183)
    source: 'NOAA HDD/CDD + estimated design temps (station: USW00023183)',
    lat: 33.4484,
    lon: -112.074
  },
  '53033': {
    name: 'King County, WA',
    state: 'WA',
    fips: '53033',
    heating: 23, // 99% heating design temp (estimated from HDD)
    cooling: 86, // 1% cooling design temp (estimated from CDD)
    hdd: 4377,   // HDD base 65°F (NOAA station: USW00024234)
    cdd: 308,   // CDD base 65°F (NOAA station: USW00024234)
    source: 'NOAA HDD/CDD + estimated design temps (station: USW00024234)',
    lat: 47.6062,
    lon: -122.3321
  },
  '25025': {
    name: 'Suffolk County, MA',
    state: 'MA',
    fips: '25025',
    heating: 18, // 99% heating design temp (estimated from HDD)
    cooling: 88, // 1% cooling design temp (estimated from CDD)
    hdd: 5371,   // HDD base 65°F (NOAA station: USW00014739)
    cdd: 860,   // CDD base 65°F (NOAA station: USW00014739)
    source: 'NOAA HDD/CDD + estimated design temps (station: USW00014739)',
    lat: 42.3601,
    lon: -71.0589
  },
  '06059': {
    name: 'Orange County, CA',
    state: 'CA',
    fips: '06059',
    heating: 35, // 99% heating design temp (estimated from HDD)
    cooling: 90, // 1% cooling design temp (estimated from CDD)
    hdd: 811,   // HDD base 65°F (NOAA station: USC00047888)
    cdd: 1561,   // CDD base 65°F (NOAA station: USC00047888)
    source: 'NOAA HDD/CDD + estimated design temps (station: USC00047888)',
    lat: 33.7175,
    lon: -117.8311
  },
  '12011': {
    name: 'Broward County, FL',
    state: 'FL',
    fips: '12011',
    heating: 39, // 99% heating design temp (estimated from HDD)
    cooling: 102, // 1% cooling design temp (estimated from CDD)
    hdd: 132,   // HDD base 65°F (NOAA station: USC00083168)
    cdd: 4596,   // CDD base 65°F (NOAA station: USC00083168)
    source: 'NOAA HDD/CDD + estimated design temps (station: USC00083168)',
    lat: 26.1224,
    lon: -80.1373
  },
  '48029': {
    name: 'Bexar County, TX',
    state: 'TX',
    fips: '48029',
    heating: 32, // 99% heating design temp (estimated from HDD)
    cooling: 95, // 1% cooling design temp (estimated from CDD)
    hdd: 1506,   // HDD base 65°F (NOAA station: USC00417947)
    cdd: 3081,   // CDD base 65°F (NOAA station: USC00417947)
    source: 'NOAA HDD/CDD + estimated design temps (station: USC00417947)',
    lat: 29.4241,
    lon: -98.4936
  },
  '06067': {
    name: 'Sacramento County, CA',
    state: 'CA',
    fips: '06067',
    heating: 29, // 99% heating design temp (estimated from HDD)
    cooling: 90, // 1% cooling design temp (estimated from CDD)
    hdd: 2078,   // HDD base 65°F (NOAA station: USW00023271)
    cdd: 1636,   // CDD base 65°F (NOAA station: USW00023271)
    source: 'NOAA HDD/CDD + estimated design temps (station: USW00023271)',
    lat: 38.5816,
    lon: -121.4944
  },
  '39049': {
    name: 'Franklin County, OH',
    state: 'OH',
    fips: '39049',
    heating: 18, // 99% heating design temp (estimated from HDD)
    cooling: 90, // 1% cooling design temp (estimated from CDD)
    hdd: 5351,   // HDD base 65°F (NOAA station: USC00331785)
    cdd: 1037,   // CDD base 65°F (NOAA station: USC00331785)
    source: 'NOAA HDD/CDD + estimated design temps (station: USC00331785)',
    lat: 39.9612,
    lon: -82.9988
  },
  '42101': {
    name: 'Philadelphia County, PA',
    state: 'PA',
    fips: '42101',
    heating: 24, // 99% heating design temp (estimated from HDD)
    cooling: 91, // 1% cooling design temp (estimated from CDD)
    hdd: 4097,   // HDD base 65°F (NOAA station: USC00366886)
    cdd: 1670,   // CDD base 65°F (NOAA station: USC00366886)
    source: 'NOAA HDD/CDD + estimated design temps (station: USC00366886)',
    lat: 39.9526,
    lon: -75.1652
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = ASHRAE_COUNTY_DATA;
}
