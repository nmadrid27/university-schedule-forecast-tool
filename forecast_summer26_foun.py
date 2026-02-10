#!/usr/bin/env python3
"""
Summer 2026 FOUN Forecast
Uses Spring 2026 projections and historical Summer/Spring ratios
"""

import sys
import pandas as pd
import numpy as np

# Configuration
SPRING_FORECAST = 'Data/Spring_2026_FOUN_Forecast_SAV_SCADnow_From_Sequence_Guides.csv'
HISTORICAL_DATA = 'Data/FOUN_Historical.csv'
OUTPUT_FILE = 'Data/Summer_2026_FOUN_Forecast.csv'
SECTION_CAPACITY = 20
DEFAULT_SUMMER_RATIO = 0.12  # Default 12% of Spring enrollment

print("=" * 60)
print("Summer 2026 FOUN Section Forecast")
print("=" * 60)

# Load Spring 2026 forecast
print(f"\n1. Loading Spring 2026 forecast from: {SPRING_FORECAST}")
try:
    spring_forecast = pd.read_csv(SPRING_FORECAST)
    print(f"   Found {len(spring_forecast)} course/campus combinations")
except FileNotFoundError:
    print(f"   Error: File not found: {SPRING_FORECAST}")
    sys.exit(1)
except Exception as e:
    print(f"   Error loading forecast: {e}")
    sys.exit(1)

# Load historical data to calculate Summer/Spring ratios
print(f"\n2. Loading historical data from: {HISTORICAL_DATA}")
try:
    hist = pd.read_csv(HISTORICAL_DATA)
    hist['course'] = hist['SUBJ'] + ' ' + hist['CRS NUMBER'].astype(str)

    # Calculate historical Summer/Spring ratios per course
    print("   Calculating historical Summer/Spring enrollment ratios...")

    ratios = {}
    for course in hist['course'].unique():
        course_data = hist[hist['course'] == course]

        # Get Spring terms (ending in 30) and Summer terms (ending in 40)
        spring_terms = course_data[course_data['TERM'].astype(str).str.endswith('30')]
        summer_terms = course_data[course_data['TERM'].astype(str).str.endswith('40')]

        if len(spring_terms) > 0 and len(summer_terms) > 0:
            # Match years
            course_ratios = []
            for year in range(2020, 2026):
                spring_term = int(f"{year}30")
                summer_term = int(f"{year}40")

                spring_enr = spring_terms[spring_terms['TERM'] == spring_term]['ACT ENR'].sum()
                summer_enr = summer_terms[summer_terms['TERM'] == summer_term]['ACT ENR'].sum()

                if spring_enr > 0 and summer_enr > 0:
                    ratio = summer_enr / spring_enr
                    course_ratios.append(ratio)

            if course_ratios:
                avg_ratio = np.mean(course_ratios)
                ratios[course] = {
                    'ratio': avg_ratio,
                    'sample_size': len(course_ratios)
                }

    print(f"   Calculated ratios for {len(ratios)} FOUN courses")

except Exception as e:
    print(f"   Warning: Could not load historical data: {e}")
    print(f"   Will use default ratio of {DEFAULT_SUMMER_RATIO}")
    ratios = {}

# Generate Summer 2026 forecast
print("\n3. Generating Summer 2026 forecast...")
print(f"   Section capacity: {SECTION_CAPACITY} students")

summer_forecast = []

for _, row in spring_forecast.iterrows():
    course = row['course']
    campus = row['campus']
    spring_seats = row['spring_projected_seats']

    # Get historical ratio or use default
    if course in ratios:
        summer_ratio = ratios[course]['ratio']
        sample_size = ratios[course]['sample_size']
        ratio_source = f"historical ({sample_size} years)"
    else:
        summer_ratio = DEFAULT_SUMMER_RATIO
        ratio_source = "default"

    # Calculate summer demand
    summer_seats = spring_seats * summer_ratio

    # Calculate sections needed (round up)
    sections_needed = int(np.ceil(summer_seats / SECTION_CAPACITY))

    # Only include courses with meaningful demand (at least 1 section)
    if sections_needed > 0:
        summer_forecast.append({
            'course': course,
            'campus': campus,
            'spring_projected_seats': round(spring_seats, 2),
            'summer_ratio': round(summer_ratio, 3),
            'summer_projected_seats': round(summer_seats, 2),
            'sections_needed': sections_needed,
            'ratio_source': ratio_source
        })

# Create DataFrame
df_forecast = pd.DataFrame(summer_forecast)

# Aggregate by course (combine campuses for summary)
print("\n4. Summer 2026 FOUN Forecast Summary:")
print("=" * 80)

course_summary = df_forecast.groupby('course').agg({
    'summer_projected_seats': 'sum',
    'sections_needed': 'sum'
}).reset_index()

course_summary = course_summary.sort_values('summer_projected_seats', ascending=False)

print(f"{'Course':<15} {'Summer Seats':<15} {'Sections':<10}")
print("-" * 80)
for _, row in course_summary.iterrows():
    print(f"{row['course']:<15} {row['summer_projected_seats']:>13.1f} {row['sections_needed']:>10}")

print("-" * 80)
print(f"{'TOTAL':<15} {course_summary['summer_projected_seats'].sum():>13.1f} {course_summary['sections_needed'].sum():>10}")

# Show by campus
print("\n5. Breakdown by Campus:")
print("=" * 80)

campus_summary = df_forecast.groupby('campus').agg({
    'summer_projected_seats': 'sum',
    'sections_needed': 'sum'
}).reset_index()

for _, row in campus_summary.iterrows():
    print(f"{row['campus']:<15} {row['summer_projected_seats']:>13.1f} seats → {row['sections_needed']:>3} sections")

# Save to CSV
print(f"\n6. Saving forecast to: {OUTPUT_FILE}")
try:
    df_forecast.to_csv(OUTPUT_FILE, index=False)
    print(f"   ✓ Saved {len(df_forecast)} course/campus forecasts")
except Exception as e:
    print(f"   Error saving forecast: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("Summer 2026 FOUN Forecast Complete!")
print("=" * 60)

# Show detailed forecast
print("\nDetailed Forecast (all courses/campuses):")
print("=" * 100)
print(df_forecast.to_string(index=False))
