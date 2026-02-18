import pandas as pd

try:
    df = pd.read_csv('Data/FAll25.csv')
    # Check for FOUN 110
    total = df[df['Course'].str.contains('FOUN 110', na=False)]['Enrollment'].sum()
    print(f"Fall 25 FOUN 110 Total: {total}")
except Exception as e:
    print(e)
