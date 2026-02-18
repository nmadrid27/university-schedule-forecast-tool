import pandas as pd
import os

path = "/Users/nathanmadrid/Desktop/Dev/Forecast Tool/Data/PZSAAPF-SL31 - Accepted Applicants with Latest Decision.xlsx"
xl = pd.ExcelFile(path)
df = xl.parse("202620 - SAV - FR", header=10)
print("Columns:")
for i, c in enumerate(df.columns):
    print(f"{i}: {c}")
