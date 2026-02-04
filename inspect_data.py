import pandas as pd
import os

data_dir = "/Users/nathanmadrid/Desktop/Dev/Forecast Tool/Data"
applicants_file = os.path.join(data_dir, "PZSAAPF-SL31 - Accepted Applicants with Latest Decision.xlsx")
masterlist_file = os.path.join(data_dir, "Masterlist_FOUN_courses_by_major.xlsx")

def inspect_excel(filepath):
    print(f"--- Inspecting {os.path.basename(filepath)} ---")
    try:
        xl = pd.ExcelFile(filepath)
        print("Sheet names:", xl.sheet_names)
        for sheet in xl.sheet_names:
            df = xl.parse(sheet, nrows=5)
            print(f"\nSheet: {sheet}")
            print("Columns:", list(df.columns))
            # specific checks based on user request
            if "FR" in sheet or "TR" in sheet or "202620" in sheet:
                print("Sample data (first 2 rows):")
                print(df.head(2))
    except Exception as e:
        print(f"Error reading {filepath}: {e}")

inspect_excel(applicants_file)
print("\n" + "="*30 + "\n")
inspect_excel(masterlist_file)
