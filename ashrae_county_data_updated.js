// ASHRAE COUNTY-LEVEL DESIGN DATA (Authoritative)
// Updated with NOAA HDD/CDD data

const ASHRAE_COUNTY_DATA = {
  '41051': {
    
    name: 'Multnomah County, OR',
    state: 'OR',
    fips: '41051',
    heating: 24, // 99% heating design temp (Appendix A)
    cooling: 88, // 1% cooling design temp (Appendix A)
    hdd: 4000,   // HDD base 65°F (RESNET dataset for PDX)
    cdd: 400,    // CDD base 65°F (RESNET dataset for PDX)
    source: 'Appendix A (Normative) 2013 + RESNET HDD/CDD (Portland Intl Airport)',
    lat: 45.52,
    lon: -122.68
  
  },
  '41029': {
    
    name: 'Jackson County, OR',
    state: 'OR',
    fips: '41029',
    heating: 15,
    cooling: 98,
    hdd: 4500,
    cdd: 600,
    source: 'Appendix A (Normative) + RESNET HDD/CDD (Rogue Valley Intl–Medford)',
    lat: 42.33,
    lon: -122.87
  
  },
  '41005': {
    
    name: 'Clackamas County, OR',
    state: 'OR',
    fips: '41005',
    heating: 24, // 99% heating design temp (Appendix A proxy to PDX region)
    cooling: 88, // 1% cooling design temp (Appendix A proxy to PDX region)
    hdd: 4000,   // HDD base 65°F (proxied from PDX for testing)
    cdd: 400,    // CDD base 65°F (proxied from PDX for testing)
    source: 'Appendix A (design temps, PDX proxy) + HDD/CDD provisional for dev test',
    lat: 45.41,
    lon: -122.57
  
  },
  '06089': {
    
    name: 'Shasta County, CA',
    state: 'CA',
    fips: '06089',
    heating: 25, // 99% heating design temp (RESNET/ASHRAE table - Redding)
    cooling: 108, // 1% cooling design temp (RESNET/ASHRAE table - Redding)
    hdd: 3000,   // HDD base 65°F (RESNET table - Redding Municipal Airport)
    cdd: 2500,   // CDD base 65°F (RESNET table - Redding Municipal Airport)
    source: 'RESNET/ASHRAE (Redding 96001) – Redding Municipal Airport normals',
    lat: 40.509,
    lon: -122.293
  
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = ASHRAE_COUNTY_DATA;
}
