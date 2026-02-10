#!/usr/bin/env python3

import pandas as pd
import re
import os
import sys

from utils import get_data_dir

# --- Configuration ---
DATA_DIR = get_data_dir()
ADMISSIONS_FILE = os.path.join(DATA_DIR, "PZSAAPF-SL31 - Accepted Applicants with Latest Decision.xlsx")
MASTERLIST_FILE = os.path.join(DATA_DIR, "Masterlist.md")
OUTPUT_FILE = os.path.join(DATA_DIR, "FOUN_Demand_Forecast.csv")

GEN_ED_CODES = {'FOUN', 'ENGL', 'COMM', 'MATH', 'CTXT', 'BUSI', 'DIGI', 'LECT', 'SFLM', 'VFX', 'GAME', 'CMPA', 'ARLH', 'ARTH', 'PHYS', 'ANTH', 'PHIL', 'POLS', 'PSYC'} 

# Manual overrides for codes that heuristics miss or specific mapping needs
MANUAL_CODE_MAP = {
    'ARCH': 'ARCHITECTURE',
    'GAME': 'INTERACTIVE DESIGN AND GAME DEVELOPMENT', # Assuming full name varies
    'ANIM': 'ANIMATION 2D ANIMATION', # Default proxy
    'ILLU': 'ILLUSTRATION',
    'UXDG': 'USER EXPERIENCE UX DESIGN',
    'GRDS': 'GRAPHIC DESIGN',
    'INDS': 'INTERIOR DESIGN',
    'FASM': 'FASHION MARKETING AND MANAGEMENT',
    'SEQA': 'SEQUENTIAL ART',
    'BEAU': 'BUSINESS OF BEAUTY AND FRAGRANCE',
    'SOCL': 'SOCIAL STRATEGY AND MANAGEMENT',
    'PNTG': 'PAINTING',
    'SCUL': 'SCULPTURE',
    'DWRI': 'DRAMATIC WRITING',
    'ADBR': 'ADVERTISING AND BRANDING',
    'IDUS': 'INDUSTRIAL DESIGN',
    'FASH': 'FASHION',
    'MOME': 'MOTION MEDIA DESIGN'
}

def clean_major_name(name):
    if not isinstance(name, str):
        return ""
    name = name.upper()
    name = name.replace('-', ' ')
    name = re.sub(r'^\d+\s+', '', name)
    name = re.sub(r'[()]', '', name) # Remove parens e.g. (UX)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def parse_masterlist_requirements(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    major_courses = {}
    major_codes = {} # Extracted from file
    
    current_major = None
    in_year = 0 # 0=None, 1=First, 2=Second
    
    for line in lines:
        line = line.strip()
        
        if line.startswith("## ") and not line.startswith("###"):
            raw_major = line[3:].strip()
            clean_name = re.sub(r'(Fall Only|Winter Only|Spring Only|Group [A-Z])', '', raw_major).strip()
            # Also handle manual fixes for masterlist keys if they are messy
            current_major = clean_major_name(clean_name)
            major_courses[current_major] = set()
            in_year = 0
        
        if line.startswith("#### First Year"):
            in_year = 1
        elif line.startswith("#### Second Year"):
            in_year = 2
        elif line.startswith("#### Third Year"):
            in_year = 3
            
        if current_major and line.startswith("- "):
            # 1. Collect FOUN courses (First Year Only)
            if in_year == 1:
                foun_match = re.match(r'- (FOUN \d{3})', line)
                if foun_match:
                    major_courses[current_major].add(foun_match.group(1))
            
            # 2. Extract Major Code (Look in Year 1 & 2)
            # Find first valid 4-letter code in course list
            if current_major not in major_codes and in_year <= 2:
                code_match = re.match(r'- ([A-Z]{4}) \d{3}', line)
                if code_match:
                    code = code_match.group(1)
                    if code not in GEN_ED_CODES:
                        major_codes[current_major] = code

    return major_courses, major_codes

def load_admissions_data(filepath):
    xl = pd.ExcelFile(filepath)
    all_data = []
    HEADER_ROW = 10

    for sheet in xl.sheet_names:
        sheet_upper = sheet.upper()
        if "202620" not in sheet_upper: continue
        
        is_fr = "FR" in sheet_upper
        is_tr = "TR" in sheet_upper
        if not (is_fr or is_tr): continue
        
        df = xl.parse(sheet, header=HEADER_ROW)
        
        loc_col = 'Campus'
        if is_fr:
            target_col = '1st Interest'
            st_type = 'FR'
        elif is_tr:
            target_col = 'Major'
            st_type = 'TR'
            
        if target_col not in df.columns: continue
        if loc_col not in df.columns: df[loc_col] = 'Unknown'

        grouped = df.groupby([target_col, loc_col]).size().reset_index(name='Count')
        grouped.columns = ['MajorRaw', 'Location', 'Count']
        grouped['StudentType'] = st_type
        all_data.append(grouped)

    if not all_data: return pd.DataFrame()
    return pd.concat(all_data, ignore_index=True)

def calculate_demand(admissions_df, major_courses, extracted_codes):
    demand_list = []
    print("\nCalculating Demand...")
    
    # Merge Extracted Codes with Manual Map (Manual takes precedence or fallback?)
    # Let's say Manual Map helps map *Input Codes* to *Masterlist Keys*.
    # Extracted Codes maps *Masterlist Keys* to *Codes*.
    # We want Code -> Masterlist Key.
    
    code_to_key = {v: k for k, v in extracted_codes.items()}
    # Update with manual map
    for code, key in MANUAL_CODE_MAP.items():
        # Check if key matches a masterlist key
        # We need to ensure the manual 'value' matches a valid key in major_courses
        # Try exact match or find closest
        found = False
        if key in major_courses:
            code_to_key[code] = key
            found = True
        else:
            # Fuzzy find
            for mk in major_courses.keys():
                if key in mk: # e.g. ILLUSTRATION in ILLUSTRATION
                    code_to_key[code] = mk
                    found = True
                    break
    
    unmapped_majors = set()
    
    for _, row in admissions_df.iterrows():
        raw_major = str(row['MajorRaw'])
        clean_adm = clean_major_name(raw_major)
        count = row['Count']
        location = row['Location']
        st_type = row['StudentType']
        
        matched_key = None
        
        # 1. Exact Match
        if clean_adm in major_courses:
            matched_key = clean_adm
        
        # 2. Code Match
        if not matched_key:
            # If input is code-like (<=4 chars or known code)
            if clean_adm in code_to_key:
                matched_key = code_to_key[clean_adm]
        
        # 3. Fuzzy Logic
        if not matched_key:
            # 'ANIMATION' -> 'ANIMATION 2D...'
            for mk in major_courses.keys():
                # Starts with logic: "ANIMATION" matches "ANIMATION 2D..."
                if mk.startswith(clean_adm):
                    matched_key = mk
                    break
        
        if matched_key:
            for course in major_courses[matched_key]:
                demand_list.append({
                    'Course': course,
                    'Location': location,
                    'Source': f"{st_type} Admits",
                    'Demand': count
                })
        else:
            unmapped_majors.add(raw_major)

    if unmapped_majors:
        print(f"Warning: {len(unmapped_majors)} unique majors unmapped.")
        print("Sample:", list(unmapped_majors)[:5])

    if not demand_list: return pd.DataFrame()
    return pd.DataFrame(demand_list).groupby(['Course', 'Location']).agg({'Demand': 'sum'}).reset_index()

def main():
    if not os.path.exists(ADMISSIONS_FILE):
        print(f"Warning: Admissions file not found: {ADMISSIONS_FILE}")
        return
    if not os.path.exists(MASTERLIST_FILE):
        print(f"Warning: Masterlist file not found: {MASTERLIST_FILE}")
        return
    reqs, codes = parse_masterlist_requirements(MASTERLIST_FILE)
    print(f"Loaded requirements for {len(reqs)} majors.")
    try:
        adm_df = load_admissions_data(ADMISSIONS_FILE)
    except Exception as e:
        print(f"Error loading admissions data: {e}")
        return

    if adm_df.empty: return

    result_df = calculate_demand(adm_df, reqs, codes)

    if not result_df.empty:
        print("\n--- FOUN COURSE DEMAND FORECAST (WI26) ---")
        print(result_df)
        result_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\nSaved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
