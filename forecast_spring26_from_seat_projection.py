#!/usr/bin/env python3

import csv
import math
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


DATA_DIR = Path(__file__).resolve().parent / "Data"
SEQUENCE_PATH = DATA_DIR / "clon_sav_atl_seat_projection_202630_20260107.xlsx"
FALL_ENROLL_PATH = DATA_DIR / "FAll25.csv"
WINTER_ENROLL_PATH = DATA_DIR / "Winter26.csv"
OUTPUT_PATH = DATA_DIR / "Spring_2026_FOUN_Forecast_SAV_SCADnow.csv"

SECTION_CAPACITY = 20

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def col_letter_to_index(col: str) -> int:
    idx = 0
    for ch in col:
        if not ch.isalpha():
            break
        idx = idx * 26 + (ord(ch.upper()) - ord("A") + 1)
    return idx


def parse_float(value: str) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def load_shared_strings(zf: zipfile.ZipFile) -> List[str]:
    try:
        with zf.open("xl/sharedStrings.xml") as f:
            root = ET.parse(f).getroot()
    except KeyError:
        return []

    strings = []
    for si in root.findall("main:si", NS):
        texts = []
        for t in si.findall(".//main:t", NS):
            texts.append(t.text or "")
        strings.append("".join(texts))
    return strings


def load_sheet_targets(zf: zipfile.ZipFile) -> Dict[str, str]:
    with zf.open("xl/workbook.xml") as f:
        root = ET.parse(f).getroot()
        sheets = []
        for sheet in root.findall("main:sheets/main:sheet", NS):
            name = sheet.attrib.get("name")
            rid = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            sheets.append((name, rid))

    with zf.open("xl/_rels/workbook.xml.rels") as f:
        root = ET.parse(f).getroot()
        rid_to_target = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in root.findall("rel:Relationship", NS)
        }

    return {name: rid_to_target[rid] for name, rid in sheets if rid in rid_to_target}


def read_sheet_rows(path: Path, sheet_name: str) -> List[List[str]]:
    with zipfile.ZipFile(path) as zf:
        shared_strings = load_shared_strings(zf)
        targets = load_sheet_targets(zf)
        target = targets.get(sheet_name)
        if not target:
            raise KeyError(f"Sheet not found: {sheet_name}")

        with zf.open(f"xl/{target}") as f:
            root = ET.parse(f).getroot()

        rows: List[List[str]] = []
        for row in root.findall(".//main:sheetData/main:row", NS):
            cells: Dict[int, str] = {}
            for c in row.findall("main:c", NS):
                ref = c.attrib.get("r")
                if not ref:
                    continue
                col_letters = "".join(ch for ch in ref if ch.isalpha())
                col_idx = col_letter_to_index(col_letters)
                cell_type = c.attrib.get("t")
                v = c.find("main:v", NS)
                if v is None:
                    value = ""
                else:
                    raw = v.text or ""
                    if cell_type == "s":
                        try:
                            value = shared_strings[int(raw)]
                        except (ValueError, IndexError):
                            value = raw
                    else:
                        value = raw
                cells[col_idx] = value
            if cells:
                max_col = max(cells)
                rows.append([cells.get(i, "") for i in range(1, max_col + 1)])
        return rows


def extract_foun_totals(path: Path, sheet_name: str) -> Dict[str, float]:
    rows = read_sheet_rows(path, sheet_name)
    if not rows:
        return {}

    header = rows[0]
    foun_cols = [
        idx for idx, col in enumerate(header)
        if str(col).strip().upper().startswith("FOUN ")
    ]
    total_row = None
    for row in rows[1:]:
        if row and str(row[0]).strip() == "Total Counts":
            total_row = row
            break
    if not total_row:
        return {}

    totals = {}
    for idx in foun_cols:
        if idx >= len(total_row):
            continue
        course = str(header[idx]).strip()
        totals[course] = parse_float(total_row[idx])
    return totals


def load_term_enrollments(path: Path) -> Dict[Tuple[str, str], float]:
    totals: Dict[Tuple[str, str], float] = defaultdict(float)
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            course = (row.get("Course") or "").strip()
            if not course.startswith("FOUN "):
                continue
            enrollment = parse_float(row.get("Enrollment"))
            room = (row.get("Room") or "").strip().upper()
            section = (row.get("Section #") or "").strip().upper()
            campus = "SCADnow" if (room == "OLNOW" or section.startswith("N")) else "SAV"
            totals[(campus, course)] += enrollment
    return totals


def compute_sections(seats: float, capacity: int) -> int:
    if seats <= 0:
        return 0
    return int(math.ceil(seats / capacity))


def main() -> int:
    sav_spring = extract_foun_totals(SEQUENCE_PATH, "Spring 2026 SAV")
    if not sav_spring:
        raise SystemExit("No SAV totals found in sequencing guide.")

    fall_totals = load_term_enrollments(FALL_ENROLL_PATH)
    winter_totals = load_term_enrollments(WINTER_ENROLL_PATH)

    combined: Dict[Tuple[str, str], float] = defaultdict(float)
    for source in (fall_totals, winter_totals):
        for key, value in source.items():
            combined[key] += value

    courses = sorted(sav_spring.keys())

    sav_fall_winter_total = sum(combined.get(("SAV", course), 0.0) for course in courses)
    sav_spring_total = sum(sav_spring.values())
    overall_ratio = sav_spring_total / sav_fall_winter_total if sav_fall_winter_total > 0 else 0.0

    course_ratios: Dict[str, float] = {}
    for course in courses:
        sav_fall_winter = combined.get(("SAV", course), 0.0)
        if sav_fall_winter > 0:
            course_ratios[course] = sav_spring[course] / sav_fall_winter

    output_rows = []

    for course in courses:
        sav_seats = sav_spring[course]
        output_rows.append(
            {
                "course": course,
                "campus": "Savannah",
                "spring_projected_seats": sav_seats,
                "sections": compute_sections(sav_seats, SECTION_CAPACITY),
                "method": "sequencing_total_counts",
            }
        )

    for course in courses:
        scad_fall_winter = combined.get(("SCADnow", course), 0.0)
        ratio = course_ratios.get(course, overall_ratio)
        scad_seats = scad_fall_winter * ratio
        output_rows.append(
            {
                "course": course,
                "campus": "SCADnow",
                "spring_projected_seats": scad_seats,
                "sections": compute_sections(scad_seats, SECTION_CAPACITY),
                "method": "scaled_from_fall_winter_vs_sav",
            }
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["course", "campus", "spring_projected_seats", "sections", "method"],
        )
        writer.writeheader()
        for row in output_rows:
            row["spring_projected_seats"] = f"{row['spring_projected_seats']:.2f}"
            writer.writerow(row)

    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
