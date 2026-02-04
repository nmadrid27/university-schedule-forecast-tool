#!/usr/bin/env python3

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


DATA_DIR = Path(__file__).resolve().parent / "Data"
SEQUENCE_MAP_PATH = DATA_DIR / "FOUN_sequencing_map_by_major.csv"
SPRING_ENROLL_PATH = DATA_DIR / "Spring26.csv"
SUMMER_ENROLL_PATH = DATA_DIR / "Summer26.csv"
OUTPUT_PATH = DATA_DIR / "Fall_2026_FOUN_Forecast_SAV_SCADnow_From_Sequence_Guides.csv"

SECTION_CAPACITY = 20

DEFAULTS = {
    "sequence_map": str(SEQUENCE_MAP_PATH),
    "spring_enroll": str(SPRING_ENROLL_PATH),
    "summer_enroll": str(SUMMER_ENROLL_PATH),
    "output": str(OUTPUT_PATH),
    "capacity": SECTION_CAPACITY,
    "progression_rate": 0.95,
}
FOUN_CODE_RE = re.compile(r"\bFOUN\s*(\d{3})\b", re.IGNORECASE)


def normalize_text(value: str) -> str:
    value = value or ""
    value = str(value).upper()
    value = value.replace("&", " AND ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_campuses(campus_raw: str) -> Tuple[str, ...]:
    campus_norm = normalize_text(campus_raw)
    if not campus_norm:
        return tuple()
    campus_norm = campus_norm.replace("MAJOR COURSE SEQUENCING GUIDE", "").strip()
    if campus_norm == "GENERAL":
        return ("GENERAL",)
    parts = [p.strip() for p in campus_norm.split("|")]
    parts = [p for p in parts if p]
    return tuple(parts)


def campus_matches(campuses: Iterable[str], campus: str) -> bool:
    if "GENERAL" in campuses:
        return True
    return campus in campuses


def extract_foun_codes(cell_value: str) -> List[str]:
    if not cell_value:
        return []
    codes = []
    for match in FOUN_CODE_RE.findall(str(cell_value)):
        codes.append(f"FOUN {match}")
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for code in codes:
        if code in seen:
            continue
        seen.add(code)
        deduped.append(code)
    return deduped


def parse_quarter_courses(cell_value: str) -> List[Tuple[str, float]]:
    text = str(cell_value or "").strip()
    if not text:
        return []
    courses = extract_foun_codes(text)
    if not courses:
        return []
    is_choice = "CHOICE" in text.upper()
    weight = 1.0 / len(courses) if is_choice else 1.0
    return [(course, weight) for course in courses]


def load_sequence_mappings(path: Path) -> Dict[str, Dict[str, Dict[str, float]]]:
    mappings = {
        "SAVANNAH": {
            "spring_to_fall": defaultdict(float),
            "summer_to_fall": defaultdict(float),
            "fall_counts": defaultdict(float),
        },
        "SCADNOW": {
            "spring_to_fall": defaultdict(float),
            "summer_to_fall": defaultdict(float),
            "fall_counts": defaultdict(float),
        },
    }

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            campuses = parse_campuses(row.get("campus", ""))
            if not campuses:
                continue

            spring_courses = parse_quarter_courses(row.get("spring"))
            summer_courses = parse_quarter_courses(row.get("summer"))
            fall_courses = parse_quarter_courses(row.get("fall"))
            if not fall_courses:
                continue

            for campus in ("SAVANNAH", "SCADNOW"):
                if not campus_matches(campuses, campus):
                    continue

                for fall_course, fall_weight in fall_courses:
                    mappings[campus]["fall_counts"][fall_course] += fall_weight

                for spring_course, spring_weight in spring_courses:
                    for fall_course, fall_weight in fall_courses:
                        key = (spring_course, fall_course)
                        mappings[campus]["spring_to_fall"][key] += spring_weight * fall_weight

                for summer_course, summer_weight in summer_courses:
                    for fall_course, fall_weight in fall_courses:
                        key = (summer_course, fall_course)
                        mappings[campus]["summer_to_fall"][key] += summer_weight * fall_weight

    return mappings


def parse_number(value: str) -> float:
    if value is None:
        return 0.0
    text = str(value).replace(",", "").strip()
    if text == "":
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def load_term_enrollments(path: Path, term_code: Optional[str] = None) -> Dict[Tuple[str, str], float]:
    totals: Dict[Tuple[str, str], float] = defaultdict(float)
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        fieldnames = [name or "" for name in (reader.fieldnames or [])]
        has_course = "Course" in fieldnames and "Enrollment" in fieldnames
        has_master = "SUBJ" in fieldnames and "CRS NUMBER" in fieldnames and "ACT ENR" in fieldnames
        for row in reader:
            if has_course:
                course = (row.get("Course") or "").strip()
                if not course.startswith("FOUN "):
                    continue
                enrollment = parse_number(row.get("Enrollment"))
                room = (row.get("Room") or "").strip().upper()
                section = (row.get("Section #") or "").strip().upper()
                campus = "SCADNOW" if (room == "OLNOW" or section.startswith("N")) else "SAVANNAH"
                totals[(campus, course)] += enrollment
                continue

            if has_master:
                term_value = str(row.get("TERM") or "").strip()
                if term_code and term_value != str(term_code):
                    continue
                subj = (row.get("SUBJ") or "").strip().upper()
                if subj != "FOUN":
                    continue
                crs = (row.get("CRS NUMBER") or "").strip()
                if not crs:
                    continue
                course = f"{subj} {crs}"
                enrollment = parse_number(row.get("ACT ENR"))
                campus_code = (row.get("CAMPUS") or "").strip().upper()
                if campus_code == "NOW":
                    campus = "SCADNOW"
                elif campus_code == "SAV":
                    campus = "SAVANNAH"
                else:
                    continue
                totals[(campus, course)] += enrollment
    return totals


def compute_sections(seats: float, capacity: int) -> int:
    if seats <= 0:
        return 0
    return int(math.ceil(seats / capacity))


def load_config(path: Path) -> Dict[str, object]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def apply_config(args: argparse.Namespace, config: Dict[str, object]) -> None:
    for key, value in config.items():
        if not hasattr(args, key):
            continue
        if getattr(args, key) is None:
            setattr(args, key, value)


def distribute_enrollments(
    enrollments: Dict[str, float],
    mapping: Dict[Tuple[str, str], float],
    multiplier: float,
) -> Dict[str, float]:
    fall_demand: Dict[str, float] = defaultdict(float)
    # Normalize mapping weights per source course
    by_source: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for (source, target), weight in mapping.items():
        by_source[source][target] += weight

    for source_course, seats in enrollments.items():
        if seats <= 0:
            continue
        targets = by_source.get(source_course)
        if not targets:
            continue
        total_weight = sum(targets.values())
        if total_weight <= 0:
            continue
        for target_course, weight in targets.items():
            fall_demand[target_course] += seats * multiplier * (weight / total_weight)
    return fall_demand


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Forecast Fall 2026 FOUN sections using sequencing guides and Spring/Summer enrollments."
    )
    parser.add_argument("--config", help="Path to JSON config file.")
    parser.add_argument("--sequence-map")
    parser.add_argument("--spring-enroll")
    parser.add_argument("--summer-enroll")
    parser.add_argument("--spring-term-code")
    parser.add_argument("--summer-term-code")
    parser.add_argument("--output")
    parser.add_argument("--capacity", type=int)
    parser.add_argument(
        "--progression-rate",
        type=float,
        help="Per-term progression rate (Spring->Fall uses two transitions).",
    )
    args = parser.parse_args()

    if args.config:
        apply_config(args, load_config(Path(args.config)))

    for key, default in DEFAULTS.items():
        if getattr(args, key) is None:
            setattr(args, key, default)

    mappings = load_sequence_mappings(Path(args.sequence_map))

    spring_enrollments = load_term_enrollments(Path(args.spring_enroll), args.spring_term_code)
    summer_enrollments = load_term_enrollments(Path(args.summer_enroll), args.summer_term_code)

    output_rows = []
    for campus in ("SAVANNAH", "SCADNOW"):
        spring_by_course = {
            course: seats
            for (campus_key, course), seats in spring_enrollments.items()
            if campus_key == campus
        }
        summer_by_course = {
            course: seats
            for (campus_key, course), seats in summer_enrollments.items()
            if campus_key == campus
        }

        spring_multiplier = args.progression_rate ** 2
        summer_multiplier = args.progression_rate ** 1

        fall_from_spring = distribute_enrollments(
            spring_by_course, mappings[campus]["spring_to_fall"], spring_multiplier
        )
        fall_from_summer = distribute_enrollments(
            summer_by_course, mappings[campus]["summer_to_fall"], summer_multiplier
        )

        combined = defaultdict(float)
        for course, seats in fall_from_spring.items():
            combined[course] += seats
        for course, seats in fall_from_summer.items():
            combined[course] += seats

        # Ensure fall-only courses appear (even if no spring/summer mapping hits them).
        for course in mappings[campus]["fall_counts"].keys():
            combined.setdefault(course, 0.0)

        for course in sorted(combined.keys()):
            seats = combined[course]
            output_rows.append(
                {
                    "course": course,
                    "campus": "Savannah" if campus == "SAVANNAH" else "SCADnow",
                    "fall_projected_seats": seats,
                    "sections": compute_sections(seats, args.capacity),
                    "method": "sequence_map_spring_summer_mapping",
                }
            )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["course", "campus", "fall_projected_seats", "sections", "method"],
        )
        writer.writeheader()
        for row in output_rows:
            row["fall_projected_seats"] = f"{row['fall_projected_seats']:.2f}"
            writer.writerow(row)

    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
