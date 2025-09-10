#!/usr/bin/env python3
"""
ASHRAE Design Temperature Calculator from NCEI Data
==================================================

This script calculates 99% heating and 1% cooling design temperatures
from raw NCEI Integrated Surface Database (ISD) data using the official
ASHRAE methodology.

Based on ASHRAE Handbook - Fundamentals and NCEI data processing standards.

Usage:
    python calculate_ashrae_design_temps.py

Requirements:
    pip install pandas numpy

Author: HVAC Calculator Project
License: MIT
"""

import pandas as pd
import numpy as np
import glob
import os
import sys
from pathlib import Path

# --- Configuration ---
DATA_DIR = 'ncei_data'  # Directory containing NCEI CSV files
TEMP_COLUMN = 'TMP'  # Temperature column name in NCEI data
TEMP_SCALING_FACTOR = 10  # NCEI stores temps in tenths of degrees Celsius
OUTPUT_UNIT = 'Fahrenheit'  # 'Fahrenheit' or 'Celsius'
HEATING_PERCENTILE = 0.01  # 1% for 99% heating design temp
COOLING_PERCENTILE = 0.99  # 99% for 1% cooling design temp

# Minimum years of data required for reliable results
MIN_YEARS = 10
MIN_OBSERVATIONS = 50000  # Minimum hourly observations


def load_and_clean_data(directory):
    """
    Loads and cleans raw NCEI ISD data from CSV files.
    
    Args:
        directory (str): Path to directory containing NCEI CSV files
        
    Returns:
        pd.DataFrame: Cleaned temperature data with timestamps
        
    Raises:
        FileNotFoundError: If no CSV files found
        ValueError: If insufficient data quality
    """
    print(f"Loading data from: {directory}")
    
    # Find all CSV files
    csv_files = glob.glob(os.path.join(directory, "*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in directory: {directory}")
    
    print(f"Found {len(csv_files)} data files")
    
    # Load and combine all files
    df_list = []
    for file_path in csv_files:
        try:
            # NCEI ISD files are space-separated with fixed-width columns
            # Adjust separator based on your specific file format
            df = pd.read_csv(file_path, sep=r'\s+', low_memory=False)
            df_list.append(df)
            print(f"  Loaded: {os.path.basename(file_path)} ({len(df)} records)")
        except Exception as e:
            print(f"  Warning: Could not load {file_path}: {e}")
            continue
    
    if not df_list:
        raise ValueError("No valid data files could be loaded")
    
    # Combine all data
    all_data = pd.concat(df_list, ignore_index=True)
    print(f"Total records loaded: {len(all_data)}")
    
    # Clean temperature data
    print("Cleaning temperature data...")
    
    # Convert temperature column to numeric, handling missing values
    all_data[TEMP_COLUMN] = pd.to_numeric(
        all_data[TEMP_COLUMN].astype(str).str.strip(' +').str.replace('9999', 'nan'),
        errors='coerce'
    )
    
    # Convert from tenths of degrees Celsius to full degrees Celsius
    all_data[TEMP_COLUMN] = all_data[TEMP_COLUMN] / TEMP_SCALING_FACTOR
    
    # Remove rows with invalid temperature data
    initial_count = len(all_data)
    all_data.dropna(subset=[TEMP_COLUMN], inplace=True)
    final_count = len(all_data)
    
    print(f"Removed {initial_count - final_count} invalid temperature records")
    print(f"Valid temperature records: {final_count}")
    
    # Check data sufficiency
    if final_count < MIN_OBSERVATIONS:
        raise ValueError(f"Insufficient data: {final_count} records (minimum: {MIN_OBSERVATIONS})")
    
    # Convert to desired output unit
    if OUTPUT_UNIT.lower() == 'fahrenheit':
        all_data[TEMP_COLUMN] = (all_data[TEMP_COLUMN] * 9/5) + 32
        print("Converted temperatures to Fahrenheit")
    
    return all_data


def calculate_design_temperatures(df, temp_col, heating_q, cooling_q):
    """
    Calculates ASHRAE design temperatures using percentile method.
    
    Args:
        df (pd.DataFrame): Temperature data
        temp_col (str): Temperature column name
        heating_q (float): Heating percentile (0.01 for 99% design)
        cooling_q (float): Cooling percentile (0.99 for 1% design)
        
    Returns:
        tuple: (heating_design_temp, cooling_design_temp, stats)
    """
    print("Calculating design temperatures...")
    
    temp_series = df[temp_col].dropna()
    total_hours = len(temp_series)
    
    # Calculate percentiles
    heating_temp = temp_series.quantile(heating_q)
    cooling_temp = temp_series.quantile(cooling_q)
    
    # Calculate additional statistics
    min_temp = temp_series.min()
    max_temp = temp_series.max()
    mean_temp = temp_series.mean()
    
    # Calculate degree days (base 65°F)
    if OUTPUT_UNIT.lower() == 'fahrenheit':
        base_temp = 65
    else:
        base_temp = 18.3  # 65°F in Celsius
    
    heating_degree_days = temp_series[temp_series < base_temp].apply(
        lambda x: base_temp - x
    ).sum() / 24  # Convert hourly to daily
    
    cooling_degree_days = temp_series[temp_series > base_temp].apply(
        lambda x: x - base_temp
    ).sum() / 24  # Convert hourly to daily
    
    stats = {
        'total_hours': total_hours,
        'years_of_data': total_hours / (365.25 * 24),
        'min_temp': min_temp,
        'max_temp': max_temp,
        'mean_temp': mean_temp,
        'heating_degree_days': heating_degree_days,
        'cooling_degree_days': cooling_degree_days
    }
    
    return heating_temp, cooling_temp, stats


def print_results(heating_temp, cooling_temp, stats, output_unit):
    """Prints formatted results and statistics."""
    
    unit_symbol = '°F' if output_unit.lower() == 'fahrenheit' else '°C'
    
    print("\n" + "="*60)
    print("ASHRAE DESIGN TEMPERATURE CALCULATION RESULTS")
    print("="*60)
    print(f"Data Period: {stats['years_of_data']:.1f} years ({stats['total_hours']:,} hours)")
    print(f"Temperature Unit: {output_unit}")
    print()
    print("DESIGN TEMPERATURES:")
    print(f"  99% Heating Design Temperature: {heating_temp:.1f} {unit_symbol}")
    print(f"   1% Cooling Design Temperature: {cooling_temp:.1f} {unit_symbol}")
    print()
    print("CLIMATE STATISTICS:")
    print(f"  Minimum Temperature: {stats['min_temp']:.1f} {unit_symbol}")
    print(f"  Maximum Temperature: {stats['max_temp']:.1f} {unit_symbol}")
    print(f"  Average Temperature: {stats['mean_temp']:.1f} {unit_symbol}")
    print(f"  Heating Degree Days (base 65°F): {stats['heating_degree_days']:.0f}")
    print(f"  Cooling Degree Days (base 65°F): {stats['cooling_degree_days']:.0f}")
    print()
    print("NOTES:")
    print("  • 99% Heating Design: Temperature exceeded 99% of hours")
    print("  • 1% Cooling Design: Temperature exceeded 1% of hours")
    print("  • Based on ASHRAE Handbook - Fundamentals methodology")
    print("  • Data source: NOAA NCEI Integrated Surface Database")
    print("="*60)


def main():
    """Main execution function."""
    
    print("ASHRAE Design Temperature Calculator")
    print("====================================")
    print(f"Data directory: {DATA_DIR}")
    print(f"Output unit: {OUTPUT_UNIT}")
    print()
    
    try:
        # Check if data directory exists
        if not os.path.exists(DATA_DIR):
            print(f"Error: Data directory '{DATA_DIR}' not found.")
            print("Please create the directory and add your NCEI CSV files.")
            print("\nTo download NCEI data:")
            print("1. Visit: https://www.ncei.noaa.gov/data/global-hourly/")
            print("2. Select your weather station and time period")
            print("3. Download the CSV files to the 'ncei_data' directory")
            return 1
        
        # Load and clean data
        weather_data = load_and_clean_data(DATA_DIR)
        
        # Calculate design temperatures
        heating_design, cooling_design, stats = calculate_design_temperatures(
            weather_data, TEMP_COLUMN, HEATING_PERCENTILE, COOLING_PERCENTILE
        )
        
        # Print results
        print_results(heating_design, cooling_design, stats, OUTPUT_UNIT)
        
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

