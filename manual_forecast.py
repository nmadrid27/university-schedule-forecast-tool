import pandas as pd
import math

def load_crosswalk():
    try:
        df = pd.read_csv('Data/sequence_crosswalk_template.csv')
        return dict(zip(df['legacy_code'].str.strip(), df['foun_code'].str.strip()))
    except:
        return {}

def load_and_map(filename, mapping):
    try:
        df = pd.read_csv(filename)
        # Normalize columns
        df.columns = df.columns.str.lower().str.strip()
        # Rename course col
        if 'course' in df.columns:
            df = df.rename(columns={'course': 'course_code'})
        
        # Map codes
        df['foun_code'] = df['course_code'].map(mapping).fillna(df['course_code'])
        return df
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return pd.DataFrame()

mapping = load_crosswalk()
print("Loaded Crosswalk.")

# Load Data
df_spring25 = load_and_map('Data/Spring25.csv', mapping)
df_winter26 = load_and_map('Data/Winter26.csv', mapping)

# Analyze Spring 25 (What courses do we expect in Spring?)
print("\n--- Spring 25 Actuals (Reference) ---")
spring25_counts = df_spring25.groupby('foun_code')['enrollment'].sum().sort_values(ascending=False)
print(spring25_counts)

# Analyze Winter 26 (The feeder cohort)
print("\n--- Winter 26 Projected/Actuals (Feeder) ---")
winter26_counts = df_winter26.groupby('foun_code')['enrollment'].sum().sort_values(ascending=False)
print(winter26_counts)

# Forecast Logic
# Assumption: 
# FOUN 112 (Winter) -> FOUN 240 (Spring)
# FOUN 220 (Winter) -> FOUN 230 (Spring)
# FOUN 113 (Winter) -> ? (Maybe FOUN 245? Or terminal?)

print("\n--- Spring 26 Forecast ---")
print("Assumptions: 95% progression rate from Winter to Spring.")

forecast = {}

# 1. FOUN 240 (from FOUN 112)
feeder_112 = winter26_counts.get('FOUN 112', 0)
forecast['FOUN 240'] = math.ceil(feeder_112 * 0.95)

# 2. FOUN 230 (from FOUN 220)
feeder_220 = winter26_counts.get('FOUN 220', 0)
forecast['FOUN 230'] = math.ceil(feeder_220 * 0.95)

# 3. FOUN 245 (from FOUN 113? or just historical?)
# Let's check historical ratio of 245 vs 240 in Spring 25
s25_240 = spring25_counts.get('FOUN 240', 0)
s25_245 = spring25_counts.get('FOUN 245', 0)
ratio_245 = s25_245 / s25_240 if s25_240 > 0 else 0

forecast['FOUN 245'] = math.ceil(forecast['FOUN 240'] * ratio_245)

# 4. FOUN 250 (Summer prep? Or offered in Spring?)
# Check Spring 25
s25_250 = spring25_counts.get('FOUN 250', 0)
if s25_250 > 0:
    forecast['FOUN 250'] = s25_250 # Use historical if no clear feeder

# Display Results
print(f"{'Course':<10} | {'Forecast':<10} | {'Sections (20/sec)':<15}")
print("-" * 40)
for course, count in forecast.items():
    sections = math.ceil(count / 20)
    print(f"{course:<10} | {count:<10} | {sections:<15}")

