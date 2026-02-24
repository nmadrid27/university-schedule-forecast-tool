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
    target_term = target_term.strip()
    # Accept YYYYQQ numeric term codes (e.g. "202630") and convert to "Quarter YYYY"
    if re.match(r'^\d{6}$', target_term):
        code_year = int(target_term[:4])
        code_suffix = int(target_term[4:])
        suffix_to_quarter = {10: "fall", 20: "winter", 30: "spring", 40: "summer"}
        if code_suffix not in suffix_to_quarter:
            raise ValueError(f"Invalid term code suffix '{code_suffix}' in '{target_term}'. Expected 10/20/30/40.")
        q = suffix_to_quarter[code_suffix]
        cal_year = code_year - 1 if code_suffix == 10 else code_year
        target_term = f"{q.capitalize()} {cal_year}"

    parts = target_term.split()
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


def _select_anchor_courses(
    courses: List[Tuple[str, float]],
    freq: Dict[str, int],
) -> List[Tuple[str, float]]:
    """Pick one representative from concurrent courses to avoid double-counting.

    Concurrent courses (weight >= 1.0) are co-requisites taken by the same
    cohort. Picking only the most-frequent one prevents counting that cohort
    multiple times. CHOICE courses (weight < 1.0) are alternatives — kept as-is.
    """
    if not courses:
        return courses
    concurrent = [(c, w) for c, w in courses if w >= 1.0]
    if len(concurrent) <= 1:
        return courses
    best = max(concurrent, key=lambda cw: freq.get(cw[0], 0))
    return [best]


def load_sequence_mappings(
    path: Path,
    target_quarter: str,
    closer_quarter: str,
    farther_quarter: str,
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Load the sequencing map CSV and build mappings for the given quarters.

    Returns per-campus dicts with keys:
        farther_to_target     – source→target weights, only from rows with no closer course
        farther_source_totals – total program weight per farther source across ALL rows
                                (used to normalize farther-feeder proportions correctly)
        closer_to_target      – source→target weights from rows with a closer course
        closer_source_totals  – total program weight per closer source, computed from
                                UNFILTERED data so co-occurring courses get diluted
        target_counts
    """
    mappings = {
        "SAVANNAH": {
            "farther_to_target": defaultdict(float),
            "farther_source_totals": defaultdict(float),
            "closer_to_target": defaultdict(float),
            "closer_source_totals": defaultdict(float),
            "target_counts": defaultdict(float),
        },
        "SCADNOW": {
            "farther_to_target": defaultdict(float),
            "farther_source_totals": defaultdict(float),
            "closer_to_target": defaultdict(float),
            "closer_source_totals": defaultdict(float),
            "target_counts": defaultdict(float),
        },
    }

    # --- Pass 1: Count how often each course appears as a concurrent source ---
    # This determines which course is the best anchor per quarter.
    closer_freq: Dict[str, int] = defaultdict(int)
    farther_freq: Dict[str, int] = defaultdict(int)

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for c, w in parse_quarter_courses(row.get(closer_quarter)):
                if w >= 1.0:
                    closer_freq[c] += 1
            for c, w in parse_quarter_courses(row.get(farther_quarter)):
                if w >= 1.0:
                    farther_freq[c] += 1

    # --- Pass 2: Build mappings using anchor-filtered source courses ---
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            campuses = parse_campuses(row.get("campus", ""))
            if not campuses:
                continue

            farther_raw = parse_quarter_courses(row.get(farther_quarter))
            closer_raw = parse_quarter_courses(row.get(closer_quarter))
            target_courses = parse_quarter_courses(row.get(target_quarter))

            farther_courses = _select_anchor_courses(farther_raw, farther_freq)
            closer_courses = _select_anchor_courses(closer_raw, closer_freq)

            for campus in ("SAVANNAH", "SCADNOW"):
                if not campus_matches(campuses, campus):
                    continue

                # Source totals accumulate for ALL rows, including those with no Spring
                # target.  Programs that take a feeder course in Winter but don't route
                # to any Spring FOUN course (e.g. Animation students whose CHOICE winter
                # FOUN has an empty Spring, or Motion Media Design taking FOUN 251 in
                # Winter with nothing in Spring) must still dilute the fraction so that
                # the few programs which do have Spring targets don't claim 100% of that
                # feeder's enrollment.  Without this, source_totals[FOUN 251] = 1.0
                # (Photography only) and all 264 Winter FOUN 251 students project to
                # FOUN 220, even though Fashion Marketing and Motion Media Design also
                # fill those seats and go nowhere in Spring.
                if target_courses:
                    for closer_course, closer_weight in closer_raw:
                        for target_course, target_weight in target_courses:
                            mappings[campus]["closer_source_totals"][closer_course] += closer_weight * target_weight
                    for farther_course, farther_weight in farther_courses:
                        for target_course, target_weight in target_courses:
                            mappings[campus]["farther_source_totals"][farther_course] += farther_weight * target_weight
                else:
                    # No Spring target: count feeder courses toward the denominator
                    # using weight 1.0 as the implicit single-target equivalent.
                    for closer_course, closer_weight in closer_raw:
                        mappings[campus]["closer_source_totals"][closer_course] += closer_weight
                    for farther_course, farther_weight in farther_courses:
                        mappings[campus]["farther_source_totals"][farther_course] += farther_weight
                    continue  # nothing else to build for this campus row

                for target_course, target_weight in target_courses:
                    mappings[campus]["target_counts"][target_course] += target_weight

                # Only populate farther_to_target for rows that have no closer-quarter course.
                # When a row has both a closer course and a farther course leading to the
                # same target, those students will be captured via the closer feeder path.
                # Adding the farther feeder as well would double-count the same cohort.
                if not closer_courses:
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


def load_crosswalk(crosswalk_path: Path) -> Dict[str, str]:
    """Load legacy→FOUN course code mappings from the crosswalk CSV.

    Returns a dict like {"DSGN 100": "FOUN 110", "DRAW 200": "FOUN 230", ...}.
    Returns an empty dict if the file doesn't exist.
    """
    if not crosswalk_path.is_file():
        return {}
    mapping: Dict[str, str] = {}
    with crosswalk_path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            legacy = (row.get("legacy_code") or "").strip()
            foun = (row.get("foun_code") or "").strip()
            if legacy and foun:
                mapping[legacy] = foun
    return mapping


def load_term_enrollments(
    path: Path,
    term_code: Optional[str] = None,
    crosswalk: Optional[Dict[str, str]] = None,
) -> Dict[Tuple[str, str], float]:
    """Load enrollment totals per (campus, course) from a term CSV or Master Schedule.

    Args:
        crosswalk: Optional legacy→FOUN code mapping. When provided, rows with
            legacy subject codes (DRAW, DSGN, etc.) are mapped to their FOUN
            equivalents so feeder enrollment is not silently dropped.
    """
    totals: Dict[Tuple[str, str], float] = defaultdict(float)
    xwalk = crosswalk or {}
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        fieldnames = [name or "" for name in (reader.fieldnames or [])]
        has_course = "Course" in fieldnames and "Enrollment" in fieldnames
        has_master = "SUBJ" in fieldnames and "CRS NUMBER" in fieldnames and "ACT ENR" in fieldnames
        for row in reader:
            if has_course:
                course = (row.get("Course") or "").strip()
                course = xwalk.get(course, course)
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
                crs = (row.get("CRS NUMBER") or "").strip()
                if not crs:
                    continue
                raw_course = f"{subj} {crs}"
                course = xwalk.get(raw_course, raw_course)
                if not course.startswith("FOUN "):
                    continue
                enrollment = parse_number(row.get("ACT ENR"))
                campus_code = (row.get("CAMPUS") or "").strip().upper()
                # Only model Savannah (SAV) and SCADnow (NOW); skip Atlanta (ATL) and other campuses.
                if campus_code == "NOW":
                    campus = "SCADNOW"
                elif campus_code == "SAV":
                    campus = "SAVANNAH"
                else:
                    continue  # ATL and any other campus codes are intentionally excluded
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
    source_totals: Optional[Dict[str, float]] = None,
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
        # If a source_totals normalizer is provided, use it so that the proportion
        # reflects the share of programs routing through this source, not just
        # the subset captured by this mapping.
        total_weight = (
            source_totals.get(source_course, 0.0)
            if source_totals is not None
            else sum(targets.values())
        )
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

    # Load crosswalk so legacy course codes (DRAW, DSGN) map to FOUN
    crosswalk_path = enrollment_source_path.parent / "sequence_crosswalk_template.csv"
    crosswalk = load_crosswalk(crosswalk_path)

    farther_enrollments = load_term_enrollments(enrollment_source_path, farther["term_code"], crosswalk=crosswalk)
    closer_enrollments = load_term_enrollments(enrollment_source_path, closer["term_code"], crosswalk=crosswalk)

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
            farther_by_course,
            mappings[campus]["farther_to_target"],
            farther_multiplier,
            source_totals=mappings[campus]["farther_source_totals"],
        )
        from_closer = distribute_enrollments(
            closer_by_course,
            mappings[campus]["closer_to_target"],
            closer_multiplier,
            source_totals=mappings[campus]["closer_source_totals"],
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
    crosswalk_path: Optional[Path] = None,
) -> Dict[str, float]:
    """Compute average target/feeder enrollment ratios per course from historical data.

    Quarter codes: "10"=Fall, "20"=Winter, "30"=Spring, "40"=Summer.
    Returns {course: ratio}.
    """
    # Load legacy→FOUN crosswalk so DRAW/DSGN rows map to FOUN codes
    crosswalk = load_crosswalk(crosswalk_path) if crosswalk_path else {}

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
            if not crs:
                continue
            raw_course = f"{subj} {crs}"
            # Map legacy codes to FOUN codes; keep FOUN codes as-is
            course = crosswalk.get(raw_course, raw_course)
            if not course.startswith("FOUN "):
                continue
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

    # Compute per-course historical ratios (with legacy code crosswalk)
    crosswalk_path = historical_data_path.parent / "sequence_crosswalk_template.csv"
    historical_ratios = _compute_historical_ratios(
        historical_data_path, target_qq, feeder_qq, crosswalk_path=crosswalk_path
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
