#!/usr/bin/env python3
"""Off-sequence forecast using Fall/Winter cohort scaling."""

import pandas as pd
import math

# 1. Calculate Fall 24 Cohort Size (Baseline)
try:
    df_hist = pd.read_csv('Data/FOUN_Historical.csv')
    # Fall 24 is 202410? No, 202510 (Fall 2024)
    # Let's verify term codes. 202510 = Fall 2024.
    # 202210 = Fall 2021
    # 202310 = Fall 2022
    # 202410 = Fall 2023
    # 202510 = Fall 2024

    # Let's check 202510 for DRAW 100 / DSGN 100
    fall24_draw100 = df_hist[(df_hist['SUBJ'] == 'DRAW') & (df_hist['CRS NUMBER'] == 100) & (df_hist['TERM'] == 202510)]['ACT ENR'].sum()
    fall24_dsgn100 = df_hist[(df_hist['SUBJ'] == 'DSGN') & (df_hist['CRS NUMBER'] == 100) & (df_hist['TERM'] == 202510)]['ACT ENR'].sum()

    fall24_cohort = max(fall24_draw100, fall24_dsgn100)
    print(f"Fall 24 Cohort Size (Historical): {fall24_cohort}")

except FileNotFoundError:
    print("Error: FOUN_Historical.csv not found")
    fall24_cohort = 2000 # Fallback
except Exception as e:
    print(f"Error reading history: {e}")
    fall24_cohort = 2000 # Fallback

# 2. Calculate Fall 25 Cohort Size (Current)
fall25_cohort = 2092 # From previous step
print(f"Fall 25 Cohort Size (Actual): {fall25_cohort}")

# 3. Scaling Factor
scaling_factor = fall25_cohort / fall24_cohort if fall24_cohort > 0 else 1.0
print(f"Scaling Factor: {scaling_factor:.2f}")

# 4. Load Spring 25 Actuals (Baseline for Off-Sequence)
# We need to map them first
def load_crosswalk():
    try:
        df = pd.read_csv('Data/sequence_crosswalk_template.csv')
        return dict(zip(df['legacy_code'].str.strip(), df['foun_code'].str.strip()))
    except FileNotFoundError:
        print("Warning: sequence_crosswalk_template.csv not found")
        return {}
    except Exception as e:
        print(f"Warning: Error loading crosswalk: {e}")
        return {}

mapping = load_crosswalk()

try:
    df_spring25 = pd.read_csv('Data/Spring25.csv')
except FileNotFoundError:
    print("Error: Spring25.csv not found")
    exit(1)
except Exception as e:
    print(f"Error loading Spring25.csv: {e}")
    exit(1)
df_spring25.columns = df_spring25.columns.str.lower().str.strip()
if 'course' in df_spring25.columns:
    df_spring25 = df_spring25.rename(columns={'course': 'course_code'})
df_spring25['foun_code'] = df_spring25['course_code'].map(mapping).fillna(df_spring25['course_code'])

spring25_counts = df_spring25.groupby('foun_code')['enrollment'].sum()

# 5. Forecast
target_courses = ['FOUN 110', 'FOUN 111', 'FOUN 112', 'FOUN 113', 'FOUN 220']

print("\n--- Spring 26 Forecast (Off-Sequence) ---")
print(f"{'Course':<10} | {'Spring 25':<10} | {'Forecast':<10} | {'Sections':<10}")
print("-" * 45)

for course in target_courses:
    base = spring25_counts.get(course, 0)
    forecast = math.ceil(base * scaling_factor)
    sections = math.ceil(forecast / 20)
    print(f"{course:<10} | {base:<10} | {forecast:<10} | {sections:<10}")
