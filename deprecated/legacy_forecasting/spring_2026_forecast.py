"""
Spring 2026 FOUN Section Forecast

Uses historical data, sequencing guide, and crosswalk to forecast
the number of sections needed for each FOUN course in Spring 2026.
"""

import pandas as pd
import numpy as np
import math
import os
from datetime import datetime

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Data")
SECTION_CAPACITY = 20
BUFFER_PERCENT = 10  # 10% buffer for waitlist/late adds
PROGRESSION_RATE = 0.95  # 95% of students progress to next term

print("=" * 60)
print("SPRING 2026 FOUN SECTION FORECAST")
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 60)

# 1. Load Crosswalk (Legacy -> FOUN mapping)
def load_crosswalk():
    df = pd.read_csv(os.path.join(DATA_DIR, "sequence_crosswalk_template.csv"))
    return dict(zip(df['legacy_code'].str.strip(), df['foun_code'].str.strip()))

crosswalk = load_crosswalk()
print(f"\n✓ Loaded crosswalk: {len(crosswalk)} mappings")

# 2. Load Historical Data
df_hist = pd.read_csv(os.path.join(DATA_DIR, "FOUN_Historical.csv"))
df_hist['course_code'] = df_hist['SUBJ'] + " " + df_hist['CRS NUMBER'].astype(str)
df_hist['foun_code'] = df_hist['course_code'].map(crosswalk).fillna(df_hist['course_code'])

print(f"✓ Loaded historical data: {len(df_hist)} records")
print(f"  Terms available: {sorted(df_hist['TERM'].unique())}")

# 3. Parse Term Codes
def parse_term(term_code):
    """Convert YYYYXX to (year, quarter_name)"""
    term_str = str(term_code)
    year_part = int(term_str[:4])
    suffix = int(term_str[4:])
    
    quarters = {10: ('Fall', year_part - 1), 20: ('Winter', year_part), 
                30: ('Spring', year_part), 40: ('Summer', year_part)}
    return quarters.get(suffix, (None, None))

# 4. Load Sequencing Guide - Identify Spring courses
df_seq = pd.read_csv(os.path.join(DATA_DIR, "FOUN_sequencing_map_by_major.csv"))
print(f"✓ Loaded sequencing map: {len(df_seq)} program entries")

# Extract all courses offered in Spring from sequencing
import re
spring_courses_from_seq = set()
for _, row in df_seq.iterrows():
    spring_val = str(row.get('spring', ''))
    # Find all FOUN XXX patterns
    courses = re.findall(r'FOUN \d{3}', spring_val)
    spring_courses_from_seq.update(courses)

print(f"\n📚 Spring courses from sequencing guide: {sorted(spring_courses_from_seq)}")

# 5. Analyze Historical Spring Enrollments
spring_terms = [t for t in df_hist['TERM'].unique() if str(t).endswith('30')]
print(f"\nHistorical Spring Terms: {spring_terms}")

spring_data = df_hist[df_hist['TERM'].isin(spring_terms)]
spring_by_term = spring_data.groupby(['TERM', 'foun_code'])['ACT ENR'].sum().reset_index()

print("\n📊 Historical Spring Enrollment by Course and Term:")
pivot = spring_by_term.pivot_table(index='foun_code', columns='TERM', values='ACT ENR', fill_value=0)
print(pivot.to_string())

# 6. Calculate Average Spring Enrollment (for trend)
course_avg = spring_by_term.groupby('foun_code')['ACT ENR'].mean()
print("\n📈 Average Spring Enrollment by Course:")
for course, avg in course_avg.sort_values(ascending=False).items():
    print(f"  {course}: {avg:.0f}")

# 7. Build Forecast using Multiple Methods

# Method A: Progression from Winter 2026
# Winter 2026 = 202620 (not in data yet)
# Use Winter 2025 = 202520 as proxy, scaled by growth

winter_2025_term = 202520
winter_2025_data = df_hist[df_hist['TERM'] == winter_2025_term]
winter_2025_by_course = winter_2025_data.groupby('foun_code')['ACT ENR'].sum()

fall_2025_term = 202610
fall_2025_data = df_hist[df_hist['TERM'] == fall_2025_term]
fall_2025_by_course = fall_2025_data.groupby('foun_code')['ACT ENR'].sum()

# Calculate YoY growth (Fall 25 vs Fall 24)
fall_2024_term = 202510
fall_2024_data = df_hist[df_hist['TERM'] == fall_2024_term]
fall_2024_by_course = fall_2024_data.groupby('foun_code')['ACT ENR'].sum()

# Get growth factor (Fall 25 / Fall 24)
fall_25_total = fall_2025_by_course.sum()
fall_24_total = fall_2024_by_course.sum()
growth_factor = fall_25_total / fall_24_total if fall_24_total > 0 else 1.0
print(f"\n📊 Year-over-Year Growth: {(growth_factor - 1) * 100:.1f}%")
print(f"   Fall 2024 Total: {fall_24_total:.0f}")
print(f"   Fall 2025 Total: {fall_25_total:.0f}")

# Method B: Historical Spring Average + Growth
spring_2025_term = 202530
spring_2025_data = df_hist[df_hist['TERM'] == spring_2025_term]
spring_2025_by_course = spring_2025_data.groupby('foun_code')['ACT ENR'].sum()

# 8. Generate Forecast using Growth Scaling
# The progression logic was creating unrealistic spikes
# Historical patterns show growth scaling is more reliable

print("\n" + "=" * 60)
print("SPRING 2026 SECTION FORECAST")
print("=" * 60)

forecasts = {}

# Scale from Spring 2025 using growth factor
for course in spring_courses_from_seq:
    base = spring_2025_by_course.get(course, course_avg.get(course, 0))
    # Apply growth factor
    projected = base * growth_factor
    forecasts[course] = {
        'spring_25_actual': base,
        'final': projected,
        'method': 'growth_scaled'
    }

# Calculate sections needed
def calculate_sections(enrollment, capacity=SECTION_CAPACITY, buffer_pct=BUFFER_PERCENT):
    effective_cap = capacity * (1 - buffer_pct / 100)
    return max(1, math.ceil(enrollment / effective_cap)) if enrollment > 0 else 0

# 10. Output Results
print(f"\n{'Course':<12} | {'Sp25 Act':>10} | {'Forecast':>10} | {'Sections':>10} | Method")
print("-" * 65)

results = []
total_sections = 0
total_enrollment = 0

for course in sorted(forecasts.keys()):
    f = forecasts[course]
    final_enr = f['final']
    sections = calculate_sections(final_enr)
    total_sections += sections
    total_enrollment += final_enr
    
    results.append({
        'Course': course,
        'Spring_25_Actual': int(f['spring_25_actual']),
        'Spring_26_Forecast': int(round(final_enr)),
        'Sections_Needed': sections,
        'Method': f['method']
    })
    
    print(f"{course:<12} | {int(f['spring_25_actual']):>10} | {int(round(final_enr)):>10} | {sections:>10} | {f['method']}")

print("-" * 65)
print(f"{'TOTAL':<12} | {'':<10} | {int(total_enrollment):>10} | {total_sections:>10}")

# 11. Save Results
df_results = pd.DataFrame(results)
output_path = os.path.join(DATA_DIR, "Spring_2026_FOUN_Forecast.csv")
df_results.to_csv(output_path, index=False)
print(f"\n✓ Results saved to: {output_path}")

# 12. Confidence Notes
print("\n" + "=" * 60)
print("METHODOLOGY NOTES")
print("=" * 60)
print(f"""
1. Base Data: Spring 2025 actual enrollments
2. Growth Factor: {growth_factor:.2%} (Fall 25 vs Fall 24)
3. Progression Rate: {PROGRESSION_RATE:.0%} (Winter -> Spring)
4. Section Capacity: {SECTION_CAPACITY} students
5. Buffer: {BUFFER_PERCENT}% for waitlist/late adds

Courses with 'max(prog,growth)' method use the higher of:
  - Historical growth scaling
  - Progression from Winter feeder course
""")
