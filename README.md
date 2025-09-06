# HVAC Cost Comparison Calculator

A web-based calculator for comparing HVAC system costs using accurate ASHRAE design temperatures from NOAA weather data.

## Features

- **Accurate Climate Data**: Uses NOAA NCEI weather station data with proper ASHRAE 99%/1% percentile calculations
- **Zip Code Lookup**: Enter any US zip code to get location-specific climate data
- **Multiple HVAC Systems**: Compare traditional, heat pump, and hybrid systems
- **Real-time Calculations**: Instant cost comparisons with detailed breakdowns
- **Professional Methodology**: Follows ASHRAE Handbook - Fundamentals standards

## Quick Start

1. **Open the calculator**: Double-click `hvac_cost_comparison.html` or open it in any web browser
2. **Enter your zip code**: Type any US zip code (e.g., 33101 for Miami, 80202 for Denver)
3. **Click "Lookup"**: The calculator will fetch weather station data and calculate design temperatures
4. **View results**: See your climate data, system comparisons, and cost analysis

## Climate Data Sources

- **Weather Stations**: [NOAA Weather API](https://api.weather.gov/) for nearest station lookup
- **Historical Data**: [NOAA NCEI Integrated Surface Database](https://www.ncei.noaa.gov/data/global-hourly/) for hourly temperature data
- **Design Temperatures**: ASHRAE 99%/1% percentile method (NCEI standard)
- **Location Data**: [Zippopotam.us API](https://zippopotam.us/) for zip code to coordinates

## Advanced Usage: Python Script

For users who want to calculate design temperatures from their own NCEI data:

### Prerequisites

```bash
pip install pandas numpy
```

### Download NCEI Data

1. Visit [NOAA NCEI Data Access](https://www.ncei.noaa.gov/data/global-hourly/)
2. Search for your weather station
3. Select 30+ years of data (1990-2023 recommended)
4. Download CSV files to a `ncei_data` directory

### Run the Script

```bash
python calculate_ashrae_design_temps.py
```

### Example Output

```
ASHRAE DESIGN TEMPERATURE CALCULATION RESULTS
============================================
Data Period: 30.2 years (264,384 hours)
Temperature Unit: Fahrenheit

DESIGN TEMPERATURES:
  99% Heating Design Temperature: 7.0 °F
   1% Cooling Design Temperature: 90.0 °F

CLIMATE STATISTICS:
  Minimum Temperature: -25.0 °F
  Maximum Temperature: 105.0 °F
  Average Temperature: 52.0 °F
  Heating Degree Days (base 65°F): 6,500
  Cooling Degree Days (base 65°F): 600
```

## Methodology

### ASHRAE Design Temperature Calculation

The calculator uses the official ASHRAE methodology:

1. **Data Collection**: Fetches 4+ years of hourly temperature data from NOAA weather stations
2. **Data Cleaning**: Removes invalid readings and converts units
3. **Percentile Calculation**:
   - **99% Heating Design**: Temperature exceeded 99% of hours (coldest 1% of hours)
   - **1% Cooling Design**: Temperature exceeded 1% of hours (hottest 1% of hours)
4. **Validation**: Compares results against known ASHRAE values for major cities

### HVAC System Calculations

- **Heating Load**: Based on degree days and climate zone
- **Energy Costs**: Uses regional electricity and gas rates
- **System Efficiency**: Accounts for COP, AFUE, and seasonal performance
- **Lifecycle Costs**: Includes installation, operation, and maintenance

## Known Cities with Verified Data

The calculator includes verified ASHRAE design temperatures for:

- **Phoenix, AZ**: 41°F / 108°F
- **Portland, OR**: 29°F / 87°F  
- **New York, NY**: 18°F / 88°F
- **Miami, FL**: 48°F / 89°F
- **Denver, CO**: 7°F / 90°F

## Troubleshooting

### Common Issues

1. **"No weather data found"**: Try a different zip code or check your internet connection
2. **Inaccurate temperatures**: The calculator falls back to regional estimates if weather station data is unavailable
3. **Debug mode**: Click "Show Debug" to see raw data and calculation details

### Data Quality

- **Minimum 4 years** of data required for reliable results
- **Weather station proximity** affects accuracy (closer = better)
- **Data gaps** are handled by falling back to regional estimates

## Technical Details

### File Structure

```
├── hvac_cost_comparison.html    # Main calculator (web interface)
├── calculate_ashrae_design_temps.py  # Python script for NCEI data
├── README.md                    # This file
└── ncei_data/                   # Directory for NCEI CSV files (create this)
```

### Browser Compatibility

- Chrome, Firefox, Safari, Edge (modern versions)
- JavaScript enabled
- Internet connection required for API calls

## Contributing

This calculator is designed for educational and professional use. For production HVAC design, always verify results against Manual J software and local building codes.

## License

MIT License - Feel free to use and modify for your projects.

## Data Attribution

- **Climate Data**: NOAA National Centers for Environmental Information
- **Location Data**: Zippopotam.us (free API)
- **Methodology**: ASHRAE Handbook - Fundamentals
- **Weather Stations**: National Weather Service

