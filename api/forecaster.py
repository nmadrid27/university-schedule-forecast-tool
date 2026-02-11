"""
Sequence-based FOUN enrollment forecasting.

Pure functions extracted from forecast_spring26_from_sequence_guides.py
so the FastAPI backend can call them without argparse/sys.exit coupling.

Generalized to forecast any target quarter (Spring, Summer, Fall, Winter).
"""

import csv
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, DefaultDict

FOUN_CODE_RE = re.compile(r"\bFOUN\s*(\d{3})\b", re.IGNORECASE)

# Quarter cycle: each quarter's two feeders in order (closer, farther)
QUARTER_CYCLE = {
    "spring": ("winter", "fall"),
    "summer": ("spring", "winter"),
    "fall":   ("summer", "spring"),
    "winter": ("fall", "summer"),
}

# SCAD term code quarter digits
QUARTER_CODES = {"fall": 10, "winter": 20, "spring": 30, "summer": 40}


def resolve_term_info(target_term: str) -> Dict:
    """Parse a human-readable term like 'Summer 2026' into quarter info
    with feeder term codes.

    Returns dict with:
        target_quarter, target_term_code,
        closer_feeder: {quarter, term_code, multiplier_exp},
        farther_feeder: {quarter, term_code, multiplier_exp}
    """
    parts = target_term.strip().split()
    if len(parts) != 2:
        raise ValueError(f"Invalid target_term format: '{target_term}'. Expected 'Quarter YYYY'.")
    quarter_name = parts[0].lower()
    calendar_year = int(parts[1])

    if quarter_name not in QUARTER_CYCLE:
        raise ValueError(f"Unknown quarter: '{quarter_name}'. Must be spring/summer/fall/winter.")

    # Academic year: Fall uses next calendar year's academic code
    if quarter_name == "fall":
        academic_year = calendar_year + 1
    else:
        academic_year = calendar_year

    target_term_code = str(academic_year) + str(QUARTER_CODES[quarter_name])

    closer_q, farther_q = QUARTER_CYCLE[quarter_name]

    def _feeder_term_code(feeder_quarter: str) -> str:
        """Compute the term code for a feeder quarter preceding the target."""
        # Walk backwards: the closer feeder is 1 quarter before target,
        # the farther feeder is 2 quarters before target.
        # We need to figure out the calendar year for each feeder.
        quarter_order = ["fall", "winter", "spring", "summer"]
        target_idx = quarter_order.index(quarter_name)
        feeder_idx = quarter_order.index(feeder_quarter)

        # Determine the calendar year of the feeder
        # The feeder is in the same academic year cycle or the previous one
        if feeder_quarter == "fall":
            # Fall always uses calendar_year of the fall itself
            # Fall before winter/spring/summer of calendar_year is Fall (calendar_year - 1)
            feeder_cal_year = calendar_year - 1
            feeder_acad_year = feeder_cal_year + 1  # Fall academic year
        elif feeder_quarter == "winter":
            if quarter_name == "fall":
                # Winter before Fall: same calendar year
                feeder_cal_year = calendar_year
            else:
                # Winter before Spring/Summer of same year
                feeder_cal_year = calendar_year
            feeder_acad_year = feeder_cal_year
        elif feeder_quarter == "spring":
            feeder_cal_year = calendar_year
            feeder_acad_year = feeder_cal_year
        else:  # summer
            if quarter_name == "fall":
                feeder_cal_year = calendar_year
            elif quarter_name == "winter":
                # Winter 2027 ← Summer 2026
                feeder_cal_year = calendar_year - 1
            else:
                feeder_cal_year = calendar_year
            feeder_acad_year = feeder_cal_year

        # Apply SCAD academic year convention: Fall uses next year
        if feeder_quarter == "fall":
            feeder_acad_year = feeder_cal_year + 1

        return str(feeder_acad_year) + str(QUARTER_CODES[feeder_quarter])

    return {
        "target_quarter": quarter_name,
        "target_term_code": target_term_code,
        "closer_feeder": {
            "quarter": closer_q,
            "term_code": _feeder_term_code(closer_q),
            "multiplier_exp": 1,
        },
        "farther_feeder": {
            "quarter": farther_q,
            "term_code": _feeder_term_code(farther_q),
            "multiplier_exp": 2,
        },
    }


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
    seen = set()
    codes = []
    for match in FOUN_CODE_RE.findall(str(cell_value)):
        code = f"FOUN {match}"
        if code not in seen:
            seen.add(code)
            codes.append(code)
    return codes


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


def load_sequence_mappings(
    path: Path,
    target_quarter: str,
    closer_quarter: str,
    farther_quarter: str,
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Load the sequencing map CSV and build mappings for the given quarters.

    Returns per-campus dicts with keys:
        farther_to_target, closer_to_target, target_counts
    """
    mappings = {
        "SAVANNAH": {
            "farther_to_target": defaultdict(float),
            "closer_to_target": defaultdict(float),
            "target_counts": defaultdict(float),
        },
        "SCADNOW": {
            "farther_to_target": defaultdict(float),
            "closer_to_target": defaultdict(float),
            "target_counts": defaultdict(float),
        },
    }

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            campuses = parse_campuses(row.get("campus", ""))
            if not campuses:
                continue

            farther_courses = parse_quarter_courses(row.get(farther_quarter))
            closer_courses = parse_quarter_courses(row.get(closer_quarter))
            target_courses = parse_quarter_courses(row.get(target_quarter))
            if not target_courses:
                continue

            for campus in ("SAVANNAH", "SCADNOW"):
                if not campus_matches(campuses, campus):
                    continue

                for target_course, target_weight in target_courses:
                    mappings[campus]["target_counts"][target_course] += target_weight

                for farther_course, farther_weight in farther_courses:
                    for target_course, target_weight in target_courses:
                        key = (farther_course, target_course)
                        mappings[campus]["farther_to_target"][key] += farther_weight * target_weight

                for closer_course, closer_weight in closer_courses:
                    for target_course, target_weight in target_courses:
                        key = (closer_course, target_course)
                        mappings[campus]["closer_to_target"][key] += closer_weight * target_weight

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


def distribute_enrollments(
    enrollments: Dict[str, float],
    mapping: Dict[Tuple[str, str], float],
    multiplier: float,
) -> Dict[str, float]:
    demand: Dict[str, float] = defaultdict(float)
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
            demand[target_course] += seats * multiplier * (weight / total_weight)
    return demand


def get_available_terms(master_schedule_path: Path) -> List[str]:
    """Scan the Master Schedule CSV for distinct TERM values."""
    terms = set()
    with master_schedule_path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            term_val = str(row.get("TERM") or "").strip()
            if term_val:
                terms.add(term_val)
    return sorted(terms)


def term_code_to_label(term_code: str) -> str:
    """Convert SCAD term code like '202630' to 'Spring 2026'."""
    if len(term_code) != 6:
        return term_code
    acad_year = int(term_code[:4])
    quarter_digit = term_code[4:]
    labels = {"10": "Fall", "20": "Winter", "30": "Spring", "40": "Summer"}
    quarter_name = labels.get(quarter_digit)
    if not quarter_name:
        return term_code
    # Fall uses academic year - 1 for calendar year
    if quarter_name == "Fall":
        cal_year = acad_year - 1
    else:
        cal_year = acad_year
    return f"{quarter_name} {cal_year}"


# --------------- Orchestrator ---------------

def run_sequence_forecast(
    sequence_map_path: Path,
    enrollment_source_path: Path,
    target_term: str,
    capacity: int = 20,
    progression_rate: float = 0.95,
    buffer_percent: float = 0.0,
) -> List[Dict]:
    """Run the full sequence-based forecast pipeline for any target quarter.

    Args:
        sequence_map_path: Path to the sequencing map CSV.
        enrollment_source_path: Path to enrollment data (Master Schedule or term CSV).
        target_term: Human-readable term, e.g. "Summer 2026".
        capacity: Section capacity.
        progression_rate: Per-gap progression rate.
        buffer_percent: Buffer percentage to add.

    Returns a list of dicts with keys:
        course, campus, projected_seats, sections, method
    """
    info = resolve_term_info(target_term)
    target_quarter = info["target_quarter"]
    closer = info["closer_feeder"]
    farther = info["farther_feeder"]

    mappings = load_sequence_mappings(
        sequence_map_path,
        target_quarter=target_quarter,
        closer_quarter=closer["quarter"],
        farther_quarter=farther["quarter"],
    )

    farther_enrollments = load_term_enrollments(enrollment_source_path, farther["term_code"])
    closer_enrollments = load_term_enrollments(enrollment_source_path, closer["term_code"])

    farther_multiplier = progression_rate ** farther["multiplier_exp"]
    closer_multiplier = progression_rate ** closer["multiplier_exp"]

    output_rows: List[Dict] = []
    for campus in ("SAVANNAH", "SCADNOW"):
        farther_by_course = {
            course: seats
            for (campus_key, course), seats in farther_enrollments.items()
            if campus_key == campus
        }
        closer_by_course = {
            course: seats
            for (campus_key, course), seats in closer_enrollments.items()
            if campus_key == campus
        }

        from_farther = distribute_enrollments(
            farther_by_course, mappings[campus]["farther_to_target"], farther_multiplier
        )
        from_closer = distribute_enrollments(
            closer_by_course, mappings[campus]["closer_to_target"], closer_multiplier
        )

        combined = defaultdict(float)
        for course, seats in from_farther.items():
            combined[course] += seats
        for course, seats in from_closer.items():
            combined[course] += seats

        for course in mappings[campus]["target_counts"].keys():
            combined.setdefault(course, 0.0)

        # Apply buffer
        buffer_multiplier = 1.0 + (buffer_percent / 100.0)

        for course in sorted(combined.keys()):
            seats = combined[course] * buffer_multiplier
            output_rows.append(
                {
                    "course": course,
                    "campus": "Savannah" if campus == "SAVANNAH" else "SCADnow",
                    "projected_seats": seats,
                    "sections": compute_sections(seats, capacity),
                    "method": "sequence_map_feeder_mapping",
                }
            )

    return output_rows


def _compute_historical_ratios(
    historical_path: Path,
    target_quarter_code: str,
    feeder_quarter_code: str,
) -> Dict[str, float]:
    """Compute average target/feeder enrollment ratios per course from historical data.

    Quarter codes: "10"=Fall, "20"=Winter, "30"=Spring, "40"=Summer.
    Returns {course: ratio}.
    """
    # Collect per-course, per-academic-year enrollment totals for each quarter
    # Structure: {course: {acad_year: {quarter_code: total_enrollment}}}
    data: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

    if not historical_path.is_file():
        return {}

    with historical_path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            subj = (row.get("SUBJ") or "").strip().upper()
            crs = (row.get("CRS NUMBER") or "").strip()
            if not subj.startswith("FOUN") or not crs:
                continue
            course = f"{subj} {crs}"
            term_str = str(row.get("TERM") or "").strip()
            if len(term_str) != 6:
                continue
            acad_year = term_str[:4]
            qq = term_str[4:]
            enrollment = parse_number(row.get("ACT ENR"))
            data[course][acad_year][qq] += enrollment

    ratios: Dict[str, float] = {}
    for course, by_year in data.items():
        year_ratios = []
        for acad_year, by_qq in by_year.items():
            feeder_enr = by_qq.get(feeder_quarter_code, 0.0)
            target_enr = by_qq.get(target_quarter_code, 0.0)
            if feeder_enr > 0 and target_enr > 0:
                year_ratios.append(target_enr / feeder_enr)
        if year_ratios:
            ratios[course] = sum(year_ratios) / len(year_ratios)

    return ratios


def run_ratio_forecast(
    feeder_forecast_path: Path,
    historical_data_path: Path,
    target_term: str,
    capacity: int = 20,
    buffer_percent: float = 0.0,
    default_ratio: float = 0.12,
) -> List[Dict]:
    """Ratio-based forecast: apply historical target/feeder ratios to a prior forecast.

    Used when the sequence map lacks data for the target quarter (e.g. Summer).
    Reads an existing forecast CSV (e.g. Spring 2026) and scales seats by
    the historical ratio of target-quarter to feeder-quarter enrollment.

    Args:
        feeder_forecast_path: Path to the feeder term's forecast CSV
            (must have columns: course, campus, and a *_projected_seats column).
        historical_data_path: Path to FOUN_Historical.csv for ratio computation.
        target_term: Human-readable term, e.g. "Summer 2026".
        capacity: Section capacity.
        buffer_percent: Buffer percentage to add.
        default_ratio: Fallback ratio when historical data is insufficient.

    Returns list of dicts matching run_sequence_forecast output format.
    """
    info = resolve_term_info(target_term)
    target_qq = str(QUARTER_CODES[info["target_quarter"]])
    feeder_qq = str(QUARTER_CODES[info["closer_feeder"]["quarter"]])

    # Compute per-course historical ratios
    historical_ratios = _compute_historical_ratios(
        historical_data_path, target_qq, feeder_qq
    )

    # Load the feeder forecast CSV
    feeder_data: List[Tuple[str, str, float]] = []
    if not feeder_forecast_path.is_file():
        return []

    with feeder_forecast_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        # Find the projected_seats column (varies by CSV naming)
        seats_col = None
        for col in fieldnames:
            if col == "projected_seats" or col.endswith("_projected_seats"):
                seats_col = col
                break
        if seats_col is None:
            return []

        for row in reader:
            course = (row.get("course") or "").strip()
            campus = (row.get("campus") or "").strip()
            seats = parse_number(row.get(seats_col))
            if course and campus and seats > 0:
                feeder_data.append((course, campus, seats))

    buffer_multiplier = 1.0 + (buffer_percent / 100.0)
    output_rows: List[Dict] = []

    for course, campus, feeder_seats in feeder_data:
        ratio = historical_ratios.get(course, default_ratio)
        projected = feeder_seats * ratio * buffer_multiplier
        sections = compute_sections(projected, capacity)
        if sections > 0:
            output_rows.append({
                "course": course,
                "campus": campus,
                "projected_seats": projected,
                "sections": sections,
                "method": "ratio_based",
            })

    return output_rows


def load_previous_forecast(csv_path: Path) -> Dict[Tuple[str, str], float]:
    """Read an existing forecast CSV to compute change deltas.

    Returns {(course, campus): projected_seats}.
    Tries 'projected_seats' column first, falls back to columns ending
    with '_projected_seats' for backward compat with old CSVs.
    """
    result: Dict[Tuple[str, str], float] = {}
    if not csv_path.is_file():
        return result
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        # Find the projected_seats column
        seats_col = None
        if "projected_seats" in fieldnames:
            seats_col = "projected_seats"
        else:
            for col in fieldnames:
                if col.endswith("_projected_seats"):
                    seats_col = col
                    break
        if seats_col is None:
            return result
        for row in reader:
            course = (row.get("course") or "").strip()
            campus = (row.get("campus") or "").strip()
            seats = parse_number(row.get(seats_col))
            if course and campus:
                result[(course, campus)] = seats
    return result
