#!/usr/bin/env python3
"""Merge Winter26.csv into Master Schedule of Classes.csv"""

import csv
import re
from pathlib import Path

# Find project root and set paths
script_dir = Path(__file__).parent
project_root = script_dir.parent
master_path = project_root / "Data/Master Schedule of Classes.csv"
winter_path = project_root / "Data/Winter26.csv"
output_path = project_root / "Data/Master Schedule of Classes.csv"

# Read Master Schedule headers and data
with master_path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
    reader = csv.DictReader(f)
    master_headers = reader.fieldnames
    master_rows = list(reader)

print(f"Master Schedule has {len(master_rows)} rows")

# Read Winter26.csv
with winter_path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
    reader = csv.DictReader(f)
    winter_headers = reader.fieldnames
    winter_rows = list(reader)

print(f"Winter26.csv has {len(winter_rows)} rows")

# SCAD term code mapping
TERM_CODES = {"Fall": 10, "Winter": 20, "Spring": 30, "Summer": 40}

def parse_term_code(term_str):
    """Convert 'Winter 2026' to '202620'"""
    match = re.match(r'(Fall|Winter|Spring|Summer)\s*(\d{4})', term_str)
    if match:
        season, year = match.groups()
        # Academic year: Fall uses next calendar year
        if season == "Fall":
            acad_year = int(year) + 1
        else:
            acad_year = int(year)
        return f"{acad_year}{TERM_CODES[season]:02d}"
    return None

def parse_course(course_str):
    """Split 'FOUN 110' into SUBJ='FOUN' and CRS_NUMBER='110'"""
    match = re.match(r'(\w+)\s*(\d+)', course_str)
    if match:
        return match.group(1), match.group(2)
    return None, None

def determine_campus(room, section):
    """Determine campus from room/section"""
    room = str(room).upper().strip()
    section = str(section).upper().strip()
    if room == "OLNOW" or room.startswith("OL") or section.startswith("N"):
        return "NOW"
    return "SAV"

# Convert Winter26 rows to Master Schedule format
new_rows = []
for row in winter_rows:
    term_code = parse_term_code(row.get("Term", ""))
    if not term_code:
        print(f"Warning: couldn't parse term: {row.get('Term')}")
        continue

    subj, crs_num = parse_course(row.get("Course", ""))
    if not subj or not crs_num:
        print(f"Warning: couldn't parse course: {row.get('Course')}")
        continue

    campus = determine_campus(row.get("Room", ""), row.get("Section #", ""))
    enrollment = row.get("Enrollment", "0").strip() or "0"

    # Build Master Schedule row with required columns
    master_row = {
        "SCHOOL": "",
        "DEPT": "",
        "CRN": row.get("CRN", ""),
        "XLST ID": "",
        "STATUS": "",
        "SUBJ": subj,
        "CRS NUMBER": crs_num,
        "SECTION": row.get("Section #", ""),
        "SESSION DESC": "",
        "COURSE TITLE": row.get("Course Title", ""),
        "TERM": term_code,
        "CAMPUS": campus,
        "MEET DAYS": "",
        "MEET TIMES": row.get("Meeting Pattern", ""),
        "BLDG": "",
        "ROOM": row.get("Room", ""),
        "ROOM DESC": "",
        "MAX ROOM CAP": row.get("Maximum Enrollment", ""),
        "INSTR NAME": row.get("Instructor", ""),
        "INSTR ID": "",
        "INSTR CAMPUS": "",
        "MAX ENR": row.get("Maximum Enrollment", ""),
        "ACT ENR": enrollment,
        "SEATS AVAIL": "",
        "WL MAX ENR": row.get("Waitlist", ""),
        "WL ACT ENR": row.get("Wait Total", ""),
        "WL SEATS AVAIL": "",
        "PART OF TERM": "",
        "MAX ENR SUBJ/CRS/TERM": "",
        "ACT ENR SUBJ/CRS/TERM": "",
        "SEATS AVAIL SUBJ/CRS/TERM": "",
        "RESERVED MAX ENR": "",
        "RESERVED ACT ENR": "",
        "CREDIT HR SESS": "",
        "CREDIT HRS EARNED": "",
        "SECTION COUNT": "",
    }
    new_rows.append(master_row)

print(f"Converted {len(new_rows)} rows to Master Schedule format")

# Check for duplicates
existing_terms = {row.get("TERM") for row in master_rows if row.get("TERM")}
new_terms = {row.get("TERM") for row in new_rows if row.get("TERM")}
print(f"Existing terms in Master Schedule: {sorted(existing_terms)}")
print(f"New terms being added: {sorted(new_terms)}")

# Append new rows
all_rows = master_rows + new_rows

# Write merged output
with output_path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=master_headers)
    writer.writeheader()
    writer.writerows(all_rows)

print(f"Wrote {len(all_rows)} total rows to {output_path}")
print(f"Original: {len(master_rows)} rows, Added: {len(new_rows)} rows")
