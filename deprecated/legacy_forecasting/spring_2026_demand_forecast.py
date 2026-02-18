"""
Spring 2026 FOUN Section Forecast - Demand-Based

Uses:
1. Fall 2025 admitted students (First Year in Spring 2026)
2. Fall 2024 cohort estimate (Second Year in Spring 2026) 
3. Winter 2026 late transfers
4. Sequencing guide (which courses each major takes by year)
5. 2% retake margin

This calculates demand for BOTH First Year AND Second Year students.
"""

import pandas as pd
import numpy as np
import math
import os
import re
from datetime import datetime

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Data")
SECTION_CAPACITY = 20
BUFFER_PERCENT = 10
RETAKE_MARGIN = 0.02  # 2% for students retaking courses

print("=" * 70)
print("SPRING 2026 FOUN SECTION FORECAST - DEMAND-BASED")
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 70)

# 1. Load Admissions Data
print("\n📥 Loading Admissions Data...")
xl = pd.ExcelFile(os.path.join(DATA_DIR, "PZSAAPF-SL31 - Accepted Applicants with Latest Decision.xlsx"))

# 1a. Fall 2025 Freshmen (First Year in Spring 2026)
fall_2025_cohort = []
for sheet in xl.sheet_names:
    if '202610' in sheet and 'FR' in sheet:
        try:
            df = xl.parse(sheet, header=10)
            if '1st Interest' in df.columns:
                campus = sheet.split(' - ')[1] if len(sheet.split(' - ')) > 1 else 'Unknown'
                for major in df['1st Interest'].dropna():
                    fall_2025_cohort.append({'Major': str(major).strip(), 'Campus': campus})
        except Exception as e:
            print(f"  Warning: {e}")

print(f"✓ Fall 2025 freshmen (First Year): {len(fall_2025_cohort)}")

# 1b. Winter 2026 Transfers
winter_2026_transfers = []
for sheet in xl.sheet_names:
    if '202620' in sheet:
        try:
            df = xl.parse(sheet, header=10)
            major_col = '1st Interest' if '1st Interest' in df.columns else 'Major' if 'Major' in df.columns else None
            if major_col:
                for major in df[major_col].dropna():
                    winter_2026_transfers.append({'Major': str(major).strip()})
        except Exception as e:
            pass

print(f"✓ Winter 2026 transfers: {len(winter_2026_transfers)}")

# 1c. Estimate Fall 2024 cohort size (Second Year in Spring 2026)
# Use historical data to get Fall 2024 incoming class size
df_hist = pd.read_csv(os.path.join(DATA_DIR, "FOUN_Historical.csv"))
fall_2024_dsgn_draw_100 = df_hist[(df_hist['TERM'] == 202510) & 
                                   (df_hist['CRS NUMBER'] == 100)]['ACT ENR'].sum()
# DRAW 100 + DSGN 100 approximates incoming freshman class
second_year_cohort_size = int(fall_2024_dsgn_draw_100 / 2)  # Each student takes one of these
print(f"✓ Fall 2024 cohort estimate (Second Year): ~{second_year_cohort_size}")

# 2. Load Sequencing Guide
print("\n📥 Loading Sequencing Guide...")
df_seq = pd.read_csv(os.path.join(DATA_DIR, "FOUN_sequencing_map_by_major.csv"))
print(f"✓ Loaded {len(df_seq)} program sequences")

# 3. Build mappings for BOTH First Year and Second Year
first_year_spring_courses = {}
second_year_spring_courses = {}

for _, row in df_seq.iterrows():
    program = str(row['program']).strip()
    year = str(row['year']).strip()
    spring_courses = str(row.get('spring', ''))
    
    # Extract courses (excluding CHOICE options for simplicity)
    courses = re.findall(r'FOUN \d{3}', spring_courses)
    
    if 'First Year' in year and courses:
        first_year_spring_courses[program] = courses
    elif 'Second Year' in year and courses:
        second_year_spring_courses[program] = courses

print(f"✓ First Year Spring programs: {len(first_year_spring_courses)}")
print(f"✓ Second Year Spring programs: {len(second_year_spring_courses)}")

# 4. Fuzzy matching function
def clean_major_name(name):
    name = str(name).upper()
    name = re.sub(r'^1\s+', '', name)
    name = name.replace('-', ' ').replace('_', ' ')
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def find_matching_program(major, program_list):
    clean_major = clean_major_name(major)
    
    for prog in program_list:
        if clean_major == clean_major_name(prog):
            return prog
            
    for prog in program_list:
        clean_prog = clean_major_name(prog)
        if clean_major in clean_prog or clean_prog in clean_major:
            return prog
    
    major_words = set(clean_major.split())
    best_match, best_score = None, 0
    for prog in program_list:
        prog_words = set(clean_major_name(prog).split())
        overlap = len(major_words & prog_words)
        if overlap > best_score:
            best_score = overlap
            best_match = prog
    
    return best_match if best_score >= 2 else None

# 5. Calculate FIRST YEAR demand
print("\n📊 Calculating First Year Spring Demand...")

course_demand = {}
first_year_students = fall_2025_cohort + winter_2026_transfers
first_year_counts = pd.DataFrame(first_year_students)['Major'].value_counts()
first_year_matched = 0

for major, count in first_year_counts.items():
    program = find_matching_program(major, first_year_spring_courses.keys())
    if program:
        first_year_matched += count
        for course in first_year_spring_courses[program]:
            if course not in course_demand:
                course_demand[course] = {'first_year': 0, 'second_year': 0, 'sources': []}
            course_demand[course]['first_year'] += count
            course_demand[course]['sources'].append(f"1Y-{major}: {count}")

print(f"✓ First Year matched: {first_year_matched}/{len(first_year_students)}")

# 6. Calculate SECOND YEAR demand
print("\n📊 Calculating Second Year Spring Demand...")

# Distribute second year cohort across majors proportionally to Fall 2025 distribution
# (assumes similar major distribution year-to-year)
second_year_matched = 0

for major, count in first_year_counts.items():
    # Scale count to second year cohort size
    scaled_count = int(count * (second_year_cohort_size / len(first_year_students)))
    
    program = find_matching_program(major, second_year_spring_courses.keys())
    if program:
        second_year_matched += scaled_count
        for course in second_year_spring_courses[program]:
            if course not in course_demand:
                course_demand[course] = {'first_year': 0, 'second_year': 0, 'sources': []}
            course_demand[course]['second_year'] += scaled_count
            course_demand[course]['sources'].append(f"2Y-{major}: {scaled_count}")

print(f"✓ Second Year estimated: {second_year_matched}")

# 7. Calculate sections
def calculate_sections(enrollment, capacity=SECTION_CAPACITY, buffer_pct=BUFFER_PERCENT):
    effective_cap = capacity * (1 - buffer_pct / 100)
    return max(1, math.ceil(enrollment / effective_cap)) if enrollment > 0 else 0

# 8. Output Results
print("\n" + "=" * 70)
print("SPRING 2026 FOUN SECTION FORECAST (DEMAND-BASED)")
print(f"Includes: First Year + Second Year + 2% retakes + Winter transfers")
print("=" * 70)
print(f"\n{'Course':<12} | {'1st Yr':>8} | {'2nd Yr':>8} | {'Retake':>8} | {'TOTAL':>8} | {'Sections':>10}")
print("-" * 70)

results = []
total_demand = 0
total_sections = 0

for course in sorted(course_demand.keys()):
    first_yr = course_demand[course]['first_year']
    second_yr = course_demand[course]['second_year']
    base = first_yr + second_yr
    retakes = math.ceil(base * RETAKE_MARGIN)
    final = base + retakes
    sections = calculate_sections(final)
    
    total_demand += final
    total_sections += sections
    
    results.append({
        'Course': course,
        'First_Year': first_yr,
        'Second_Year': second_yr,
        'Retakes': retakes,
        'Total_Demand': final,
        'Sections_Needed': sections
    })
    
    print(f"{course:<12} | {first_yr:>8} | {second_yr:>8} | {retakes:>8} | {final:>8} | {sections:>10}")

print("-" * 70)
print(f"{'TOTAL':<12} | {'':<8} | {'':<8} | {'':<8} | {total_demand:>8} | {total_sections:>10}")

# 9. Save Results
df_results = pd.DataFrame(results)
output_path = os.path.join(DATA_DIR, "Spring_2026_FOUN_Demand_Forecast.csv")
df_results.to_csv(output_path, index=False)
print(f"\n✓ Results saved to: {output_path}")

# 10. Methodology
print("\n" + "=" * 70)
print("METHODOLOGY")
print("=" * 70)
print(f"""
FIRST YEAR (entering Fall 2025 → Spring 2026 First Year):
  - Fall 2025 freshmen: {len(fall_2025_cohort)}
  - Winter 2026 transfers: {len(winter_2026_transfers)}
  - Matched: {first_year_matched}

SECOND YEAR (entering Fall 2024 → Spring 2026 Second Year):
  - Estimated cohort: {second_year_cohort_size}
  - Matched to programs: {second_year_matched}

ADJUSTMENTS:
  - Retake margin: {RETAKE_MARGIN*100:.0f}%
  - Section capacity: {SECTION_CAPACITY} students
  - Capacity buffer: {BUFFER_PERCENT}%
""")
