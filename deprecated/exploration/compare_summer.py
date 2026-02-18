import pandas as pd

# 1. Sum from FOUN_Historical.csv for 202540 (Summer 2025)
try:
    df_hist = pd.read_csv('Data/FOUN_Historical.csv')
    df_hist_draw100 = df_hist[(df_hist['SUBJ'] == 'DRAW') & (df_hist['CRS NUMBER'] == 100) & (df_hist['TERM'] == 202540)]
    hist_total = df_hist_draw100['ACT ENR'].sum()
    print(f"Historical Summer 2025 Total for DRAW 100: {hist_total}")
except Exception as e:
    print(f"Error reading historical: {e}")

# 2. Sum from Data/Summer25.csv
try:
    df_new = pd.read_csv('Data/Summer25.csv')
    # Assuming 'Course' column has 'DRAW 100'
    # The grep showed "DRAW 100" in the Course column
    df_new_draw100 = df_new[df_new['Course'].str.contains('DRAW 100', na=False)]
    new_total = df_new_draw100['Enrollment'].sum()
    print(f"Uploaded Summer 2025 Total for DRAW 100: {new_total}")
except Exception as e:
    print(f"Error reading new file: {e}")
