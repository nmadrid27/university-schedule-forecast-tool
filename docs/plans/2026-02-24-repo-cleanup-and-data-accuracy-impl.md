# Repo Cleanup and Data Accuracy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Clean up repo clutter, add Atlanta (ATL) campus support to the forecast engine, and wire two new Cognos data sources in to fix the program-enrollment-inequality accuracy gap.

**Architecture:** ATL campus is added as a first-class campus alongside SAVANNAH and SCADNOW throughout the pipeline. New admits (PZSAAPF-SL31 xlsx) add real FOUN demand for intro courses; enrollment-by-major (Cognos CSV) replaces equal program weights with actual enrollment proportions in `load_sequence_mappings`. Both are opt-in via `forecast_config.json` — missing files fall back to current behavior.

**Tech Stack:** Python 3.14, pytest, openpyxl, FastAPI/Pydantic, Next.js frontend (unchanged)

---

## Context

- Project root: `/Users/nathanmadrid/projects/forecast-tool/`
- Run backend tests: `python -m pytest` from project root
- Run a single test class: `python -m pytest api/tests/test_forecaster_mapping.py::TestEnrollmentWeights -v`
- Backend test config: `pytest.ini` — `pythonpath = . api`, `testpaths = api/tests forecast_tool/tests`
- Key existing test helpers:
  - `_write(path, content)` in `test_forecaster_loaders.py` and `test_forecaster_mapping.py`
  - `_seq_csv(tmp_path, rows)` in `test_forecaster_mapping.py` — creates sequence map CSV with header `program,degree,campus,year,fall,winter,spring,summer`
- Sequence map column names: `program, degree, campus, year, fall, winter, spring, summer`
- Campus normalization: SAV/M → "SAVANNAH", NOW/O → "SCADNOW"
- `FOUN_CODE_RE = re.compile(r"\bFOUN\s*(\d{3})\b", re.IGNORECASE)` already exists in `forecaster.py`

---

## Task 1: Repo Cleanup

**Files:** No code changes — git operations only.

**Step 1: Delete legacy root-level files**

```bash
cd /Users/nathanmadrid/projects/forecast-tool
git rm calculate_foun_demand.py forecast_fall26_foun.py forecast_fall26_config.json sample_enrollment_data.csv
```

Expected: 4 files deleted from index and disk.

**Step 2: Move docs to docs/**

```bash
git mv Data_Gathering_Plan.md docs/Data_Gathering_Plan.md
git mv foun_demand_logic.md docs/foun_demand_logic.md
```

**Step 3: Delete redundant Data/ forecast outputs**

```bash
git rm "Data/Spring_2026_FOUN_Forecast.csv" "Data/Spring_2026_FOUN_Forecast_SAV_SCADnow.csv"
```

**Step 4: Remove tracked build artifacts from the index**

```bash
git rm -r --cached forecast_tool/__pycache__/
git rm --cached forecast_tool/.DS_Store
git rm -r --cached .obsidian/
git rm -r --cached "Data/.archives/"
```

**Step 5: Update `.gitignore`**

Open `.gitignore` and add these lines at the end:

```
__pycache__/
*.pyc
.obsidian/
Data/.archives/
```

Note: `.DS_Store`, `.venv/`, `node_modules/` are already in `.gitignore`. The `__pycache__/` and `*.pyc` entries already exist — just verify `forecast_tool/__pycache__/` is now excluded.

**Step 6: Verify clean state and commit**

```bash
git status
```

Expected: only the modified `.gitignore` and staged deletions/moves. No `__pycache__` or `.DS_Store` listed.

```bash
git add .gitignore
git commit -m "chore: clean up repo — remove legacy scripts, fix gitignore, move docs"
```

---

## Task 2: ATL Campus Support (TDD)

**Files:**
- Modify: `api/forecaster.py` — `load_term_enrollments`, `load_sequence_mappings`, `run_sequence_forecast`
- Test: `api/tests/test_forecaster_loaders.py` — update `test_atl_campus_rows_excluded`, add ATL test
- Test: `api/tests/test_forecaster_mapping.py` — add ATLANTA to mappings assertion

**Background:** Atlanta students in the Master Schedule use campus code `ATL`. The Spring 2026
admissions file has no Atlanta new admits (only M/O codes), so `load_admits_foun_demand` needs
no change. The sequence map uses "GENERAL" rows that already apply to all campuses — Atlanta
students follow the same curriculum. Adding ATLANTA as a third campus is the only structural change.

**Step 1: Write the failing tests**

In `api/tests/test_forecaster_loaders.py`, replace this existing test:

```python
# OLD — delete this:
def test_atl_campus_rows_excluded(self, tmp_path):
    csv = tmp_path / "master.csv"
    self._master(csv, [{"subj": "FOUN", "crs": "110", "enr": 80, "campus": "ATL", "term": "202630"}])
    result = load_term_enrollments(csv, term_code="202630")
    assert len(result) == 0
```

Replace with:

```python
def test_atl_campus_maps_to_atlanta(self, tmp_path):
    csv = tmp_path / "master.csv"
    self._master(csv, [{"subj": "FOUN", "crs": "110", "enr": 80, "campus": "ATL", "term": "202630"}])
    result = load_term_enrollments(csv, term_code="202630")
    assert result[("ATLANTA", "FOUN 110")] == 80.0

def test_unknown_campus_still_excluded(self, tmp_path):
    csv = tmp_path / "master.csv"
    self._master(csv, [{"subj": "FOUN", "crs": "110", "enr": 80, "campus": "HK", "term": "202630"}])
    result = load_term_enrollments(csv, term_code="202630")
    assert len(result) == 0
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest api/tests/test_forecaster_loaders.py::TestLoadTermEnrollmentsMasterSchedule -v
```

Expected: `test_atl_campus_maps_to_atlanta` FAIL (ATL is currently excluded → returns empty dict)

**Step 3: Update `load_term_enrollments` in `api/forecaster.py`**

Find the campus mapping block (around line 421):

```python
# OLD:
                if campus_code == "NOW":
                    campus = "SCADNOW"
                elif campus_code == "SAV":
                    campus = "SAVANNAH"
                else:
                    continue  # ATL and any other campus codes are intentionally excluded

# NEW:
                if campus_code == "NOW":
                    campus = "SCADNOW"
                elif campus_code == "SAV":
                    campus = "SAVANNAH"
                elif campus_code == "ATL":
                    campus = "ATLANTA"
                else:
                    continue  # other campus codes excluded
```

**Step 4: Add ATLANTA to `load_sequence_mappings` in `api/forecaster.py`**

Find the `mappings` dict initialization (around line 242) and add ATLANTA:

```python
    mappings = {
        "SAVANNAH": {
            "farther_to_target": defaultdict(float),
            "farther_source_totals": defaultdict(float),
            "closer_to_target": defaultdict(float),
            "closer_source_totals": defaultdict(float),
            "target_counts": defaultdict(float),
        },
        "SCADNOW": { ... },  # unchanged
        "ATLANTA": {
            "farther_to_target": defaultdict(float),
            "farther_source_totals": defaultdict(float),
            "closer_to_target": defaultdict(float),
            "closer_source_totals": defaultdict(float),
            "target_counts": defaultdict(float),
        },
    }
```

Also update the campus loop in Pass 2 (line 293):

```python
# OLD:
            for campus in ("SAVANNAH", "SCADNOW"):
# NEW:
            for campus in ("SAVANNAH", "SCADNOW", "ATLANTA"):
```

**Step 5: Add ATLANTA to `run_sequence_forecast` in `api/forecaster.py`**

Find the output campus loop (around line 548):

```python
# OLD:
    for campus in ("SAVANNAH", "SCADNOW"):
# NEW:
    for campus in ("SAVANNAH", "SCADNOW", "ATLANTA"):
```

Find the campus label in the output dict (around line 590):

```python
# OLD:
                    "campus": "Savannah" if campus == "SAVANNAH" else "SCADnow",
# NEW:
                    "campus": {"SAVANNAH": "Savannah", "SCADNOW": "SCADnow", "ATLANTA": "Atlanta"}.get(campus, campus),
```

**Step 6: Run tests to verify they pass**

```bash
python -m pytest api/tests/test_forecaster_loaders.py::TestLoadTermEnrollmentsMasterSchedule -v
```

Expected: all tests PASS including the new ATL test.

**Step 7: Run full suite**

```bash
python -m pytest
```

Expected: all tests pass. Check any tests that assert on result length or campus labels.

**Step 8: Commit**

```bash
git add api/forecaster.py api/tests/test_forecaster_loaders.py api/tests/test_forecaster_mapping.py
git commit -m "feat: add Atlanta (ATL) campus support to forecast engine"
```

---

## Task 3: `load_admits_foun_demand()` (TDD) — note: Atlanta not in admits file

**Files:**
- Modify: `api/forecaster.py` (add new function after `load_crosswalk`)
- Test: `api/tests/test_forecaster_loaders.py` (add new test class at bottom)

**Step 1: Write the failing test**

Add to the bottom of `api/tests/test_forecaster_loaders.py`:

```python
import openpyxl  # add to top-of-file imports if not already present


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _admits_xlsx(tmp_path: Path, students: list) -> Path:
    """Create minimal PZSAAPF-style xlsx.
    students = [(campus_code, registered_courses_string), ...]
    Campus codes: 'M'=Savannah, 'O'=SCADnow.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    # Rows 1–10: empty (metadata region in real file)
    for _ in range(10):
        ws.append([None])
    # Row 11: headers — only cols 0 (A), 12 (M), 20 (U) matter
    header_row = [None] * 39
    header_row[0] = "Student ID"
    header_row[12] = "Campus"
    header_row[20] = "Currently Registered Courses (NO WL)"
    ws.append(header_row)
    # Data rows
    for i, (campus_code, reg_courses) in enumerate(students):
        row = [None] * 39
        row[0] = f"student_{i}"
        row[12] = campus_code
        row[20] = reg_courses
        ws.append(row)
    p = tmp_path / "admits.xlsx"
    wb.save(p)
    return p


# ── load_admits_foun_demand ────────────────────────────────────────────────────

from forecaster import load_admits_foun_demand  # add to existing import block


class TestLoadAdmitsFounDemand:
    def test_counts_foun_courses_for_savannah(self, tmp_path):
        p = _admits_xlsx(tmp_path, [
            ("M", "FOUN 110; FOUN 111; ENGL 123"),
            ("M", "FOUN 110; FSYR 101"),
        ])
        result = load_admits_foun_demand(p)
        assert result["SAVANNAH"]["FOUN 110"] == 2
        assert result["SAVANNAH"]["FOUN 111"] == 1

    def test_counts_foun_courses_for_scadnow(self, tmp_path):
        p = _admits_xlsx(tmp_path, [
            ("O", "FOUN 111; CTXT 122"),
        ])
        result = load_admits_foun_demand(p)
        assert result["SCADNOW"]["FOUN 111"] == 1

    def test_non_foun_courses_excluded(self, tmp_path):
        p = _admits_xlsx(tmp_path, [
            ("M", "ENGL 123; FSYR 101"),
        ])
        result = load_admits_foun_demand(p)
        assert result.get("SAVANNAH", {}) == {}

    def test_unknown_campus_code_skipped(self, tmp_path):
        p = _admits_xlsx(tmp_path, [
            ("X", "FOUN 110"),
        ])
        result = load_admits_foun_demand(p)
        assert result.get("SAVANNAH", {}) == {}
        assert result.get("SCADNOW", {}) == {}

    def test_missing_file_returns_empty_dict(self, tmp_path):
        result = load_admits_foun_demand(tmp_path / "nonexistent.xlsx")
        assert result == {}

    def test_student_with_no_registered_courses_skipped(self, tmp_path):
        p = _admits_xlsx(tmp_path, [
            ("M", None),
            ("M", "FOUN 112"),
        ])
        result = load_admits_foun_demand(p)
        assert result["SAVANNAH"]["FOUN 112"] == 1
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest api/tests/test_forecaster_loaders.py::TestLoadAdmitsFounDemand -v
```

Expected: `ImportError: cannot import name 'load_admits_foun_demand'`

**Step 3: Add `load_admits_foun_demand` to `api/forecaster.py`**

Add after `load_crosswalk` (around line 370):

```python
def load_admits_foun_demand(path: Path) -> Dict[str, Dict[str, int]]:
    """Extract FOUN course demand from accepted applicants xlsx (PZSAAPF-SL31).

    Reads column U (Currently Registered Courses) for each student.
    Campus M → SAVANNAH, O → SCADNOW. Returns {campus: {foun_course: count}}.
    Returns empty dict if file is missing or unreadable.
    """
    if not path.is_file():
        return {}
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
    except Exception:
        return {}

    CAMPUS_MAP = {"M": "SAVANNAH", "O": "SCADNOW"}
    result: Dict[str, DefaultDict] = {
        "SAVANNAH": defaultdict(int),
        "SCADNOW": defaultdict(int),
    }

    for row in rows:
        if not row or row[0] is None:
            continue
        if str(row[0]).strip() == "Student ID":
            continue  # skip header row
        campus_code = str(row[12]).strip() if len(row) > 12 and row[12] else ""
        campus = CAMPUS_MAP.get(campus_code)
        if not campus:
            continue
        reg_courses = row[20] if len(row) > 20 else None
        if not reg_courses:
            continue
        for code in FOUN_CODE_RE.findall(str(reg_courses)):
            result[campus][f"FOUN {code}"] += 1

    return {k: dict(v) for k, v in result.items()}
```

Also add `DefaultDict` to the import at the top of `forecaster.py` if not already present (check line 15: `from typing import Dict, Iterable, List, Optional, Tuple, DefaultDict`).

**Step 4: Run test to verify it passes**

```bash
python -m pytest api/tests/test_forecaster_loaders.py::TestLoadAdmitsFounDemand -v
```

Expected: 6 tests PASS

**Step 5: Run full test suite to confirm no regressions**

```bash
python -m pytest
```

Expected: all tests pass.

**Step 6: Commit**

```bash
git add api/forecaster.py api/tests/test_forecaster_loaders.py
git commit -m "feat: add load_admits_foun_demand to extract FOUN demand from applicants xlsx"
```

---

## Task 3: `load_enrollment_by_major()` (TDD)

**Files:**
- Modify: `api/forecaster.py` (add new function after `load_admits_foun_demand`)
- Test: `api/tests/test_forecaster_loaders.py` (add new test class)

**Step 1: Write the failing test**

Add to the bottom of `api/tests/test_forecaster_loaders.py`:

```python
from forecaster import load_enrollment_by_major  # add to existing import block


class TestLoadEnrollmentByMajor:
    def _csv(self, tmp_path: Path, rows: list[str]) -> Path:
        p = tmp_path / "enrollment_by_major.csv"
        _write(p, "term,course,campus,major,enrollment\n" + "\n".join(rows) + "\n")
        return p

    def test_loads_savannah_row(self, tmp_path):
        p = self._csv(tmp_path, ["202610,FOUN 112,SAV,ARCHITECTURE,300"])
        result = load_enrollment_by_major(p)
        assert result["SAVANNAH"]["FOUN 112"]["ARCHITECTURE"] == 300.0

    def test_loads_scadnow_row(self, tmp_path):
        p = self._csv(tmp_path, ["202620,FOUN 112,NOW,ARCHITECTURE,50"])
        result = load_enrollment_by_major(p)
        assert result["SCADNOW"]["FOUN 112"]["ARCHITECTURE"] == 50.0

    def test_loads_atlanta_row(self, tmp_path):
        p = self._csv(tmp_path, ["202610,FOUN 112,ATL,ARCHITECTURE,80"])
        result = load_enrollment_by_major(p)
        assert result["ATLANTA"]["FOUN 112"]["ARCHITECTURE"] == 80.0

    def test_aggregates_across_terms(self, tmp_path):
        p = self._csv(tmp_path, [
            "202610,FOUN 112,SAV,ARCHITECTURE,280",
            "202620,FOUN 112,SAV,ARCHITECTURE,310",
        ])
        result = load_enrollment_by_major(p)
        assert result["SAVANNAH"]["FOUN 112"]["ARCHITECTURE"] == pytest.approx(590.0)

    def test_non_foun_courses_excluded(self, tmp_path):
        p = self._csv(tmp_path, ["202610,DRAW 200,SAV,ILLUSTRATION,100"])
        result = load_enrollment_by_major(p)
        assert "SAVANNAH" not in result or "DRAW 200" not in result.get("SAVANNAH", {})

    def test_unknown_campus_skipped(self, tmp_path):
        p = self._csv(tmp_path, ["202610,FOUN 112,HK,ARCHITECTURE,50"])
        result = load_enrollment_by_major(p)
        assert result == {}

    def test_missing_file_returns_empty_dict(self, tmp_path):
        result = load_enrollment_by_major(tmp_path / "nonexistent.csv")
        assert result == {}

    def test_multiple_majors_for_same_course(self, tmp_path):
        p = self._csv(tmp_path, [
            "202610,FOUN 112,SAV,ARCHITECTURE,300",
            "202610,FOUN 112,SAV,ACCESSORY DESIGN,15",
        ])
        result = load_enrollment_by_major(p)
        assert result["SAVANNAH"]["FOUN 112"]["ARCHITECTURE"] == 300.0
        assert result["SAVANNAH"]["FOUN 112"]["ACCESSORY DESIGN"] == 15.0
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest api/tests/test_forecaster_loaders.py::TestLoadEnrollmentByMajor -v
```

Expected: `ImportError: cannot import name 'load_enrollment_by_major'`

**Step 3: Add `load_enrollment_by_major` to `api/forecaster.py`**

Add after `load_admits_foun_demand`:

```python
def load_enrollment_by_major(path: Path) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Load Cognos enrollment-by-major CSV.

    Expected columns: term, course, campus, major, enrollment
    campus values: SAV → SAVANNAH, NOW → SCADNOW
    major values must match program names in FOUN_sequencing_map_by_major.csv
    (e.g. "ARCHITECTURE", "ACCESSORY DESIGN")

    Aggregates enrollment across all terms in the file.
    Returns {campus: {foun_course: {major: total_enrollment}}}.
    Returns empty dict if file is missing.
    """
    if not path.is_file():
        return {}
    CAMPUS_MAP = {"SAV": "SAVANNAH", "NOW": "SCADNOW", "ATL": "ATLANTA"}
    result: Dict[str, Dict[str, Dict[str, float]]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            campus = CAMPUS_MAP.get(row.get("campus", "").strip().upper())
            if not campus:
                continue
            course = row.get("course", "").strip()
            if not course.upper().startswith("FOUN"):
                continue
            major = row.get("major", "").strip().upper()
            try:
                enrollment = float(row.get("enrollment") or 0)
            except ValueError:
                continue
            result.setdefault(campus, {}).setdefault(course, {})
            result[campus][course][major] = result[campus][course].get(major, 0.0) + enrollment
    return result
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest api/tests/test_forecaster_loaders.py::TestLoadEnrollmentByMajor -v
```

Expected: 7 tests PASS

**Step 5: Run full suite**

```bash
python -m pytest
```

Expected: all tests pass.

**Step 6: Commit**

```bash
git add api/forecaster.py api/tests/test_forecaster_loaders.py
git commit -m "feat: add load_enrollment_by_major for Cognos enrollment-by-program data"
```

---

## Task 4: Wire enrollment weights into `load_sequence_mappings()` (TDD)

**Files:**
- Modify: `api/forecaster.py` — add `enrollment_weights` parameter to `load_sequence_mappings`
- Test: `api/tests/test_forecaster_mapping.py` — add `TestEnrollmentWeights` class

**Step 1: Write the failing test**

Add to the bottom of `api/tests/test_forecaster_mapping.py`:

```python
# ── Enrollment weights ────────────────────────────────────────────────────────

class TestEnrollmentWeights:
    def test_weights_scale_source_totals(self, tmp_path):
        """Architecture (100 students) and Jewelry (5 students) both route
        FOUN 112 Winter → FOUN 220 Spring. Weighted totals should reflect
        actual enrollment, not row count."""
        p = _seq_csv(tmp_path, [
            "ARCHITECTURE,BFA,GENERAL,First Year,,FOUN 112,FOUN 220,",
            "JEWELRY,BFA,GENERAL,First Year,,FOUN 112,FOUN 220,",
        ])
        weights = {"SAVANNAH": {"FOUN 112": {"ARCHITECTURE": 100.0, "JEWELRY": 5.0}}}
        m = load_sequence_mappings(p, "spring", "winter", "fall",
                                   enrollment_weights=weights)
        assert m["SAVANNAH"]["closer_source_totals"]["FOUN 112"] == pytest.approx(105.0)
        assert m["SAVANNAH"]["closer_to_target"][("FOUN 112", "FOUN 220")] == pytest.approx(105.0)

    def test_weights_affect_fraction_not_missing_programs(self, tmp_path):
        """A program with no enrollment data (missing from weights dict) defaults
        to 0.0 — it contributes nothing when we have real data for others."""
        p = _seq_csv(tmp_path, [
            "ARCHITECTURE,BFA,GENERAL,First Year,,FOUN 112,FOUN 220,",
            "UNKNOWNPROG,BFA,GENERAL,First Year,,FOUN 112,FOUN 220,",
        ])
        weights = {"SAVANNAH": {"FOUN 112": {"ARCHITECTURE": 100.0}}}
        m = load_sequence_mappings(p, "spring", "winter", "fall",
                                   enrollment_weights=weights)
        # Only Architecture contributes
        assert m["SAVANNAH"]["closer_source_totals"]["FOUN 112"] == pytest.approx(100.0)

    def test_weights_none_preserves_current_behavior(self, tmp_path):
        """enrollment_weights=None (default) must behave exactly as before."""
        p = _seq_csv(tmp_path, [
            "ARCHITECTURE,BFA,GENERAL,First Year,,FOUN 112,FOUN 220,",
            "JEWELRY,BFA,GENERAL,First Year,,FOUN 112,FOUN 220,",
        ])
        m = load_sequence_mappings(p, "spring", "winter", "fall",
                                   enrollment_weights=None)
        # Each row contributes 1.0 — current behavior unchanged
        assert m["SAVANNAH"]["closer_source_totals"]["FOUN 112"] == pytest.approx(2.0)

    def test_weights_applied_to_farther_feeder(self, tmp_path):
        """Enrollment weights also apply to farther-feeder routes."""
        p = _seq_csv(tmp_path, [
            "ARCHITECTURE,BFA,GENERAL,First Year,FOUN 110,,FOUN 220,",
            "JEWELRY,BFA,GENERAL,First Year,FOUN 110,,FOUN 220,",
        ])
        weights = {"SAVANNAH": {"FOUN 110": {"ARCHITECTURE": 200.0, "JEWELRY": 8.0}}}
        m = load_sequence_mappings(p, "spring", "winter", "fall",
                                   enrollment_weights=weights)
        assert m["SAVANNAH"]["farther_source_totals"]["FOUN 110"] == pytest.approx(208.0)
        assert m["SAVANNAH"]["farther_to_target"][("FOUN 110", "FOUN 220")] == pytest.approx(208.0)
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest api/tests/test_forecaster_mapping.py::TestEnrollmentWeights -v
```

Expected: `TypeError: load_sequence_mappings() got an unexpected keyword argument 'enrollment_weights'`

**Step 3: Add `enrollment_weights` parameter to `load_sequence_mappings` in `api/forecaster.py`**

Update the function signature (around line 221):

```python
def load_sequence_mappings(
    path: Path,
    target_quarter: str,
    closer_quarter: str,
    farther_quarter: str,
    year_filter: Optional[List[str]] = None,
    enrollment_weights: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None,
) -> Dict[str, Dict[str, Dict[str, float]]]:
```

In Pass 2, read the program name and compute `row_weight`. The weight multiplier must be applied to ALL accumulations for that row. Find the block starting at `for campus in ("SAVANNAH", "SCADNOW"):` and add the weight computation at the top of that loop:

```python
for campus in ("SAVANNAH", "SCADNOW"):
    if not campus_matches(campuses, campus):
        continue

    # Compute enrollment-based row weight (1.0 if no weights provided)
    row_weight = 1.0
    if enrollment_weights:
        program = row.get("program", "").strip().upper()
        campus_w = enrollment_weights.get(campus, {})
        # Prefer closer feeder enrollment; fall back to farther
        if closer_raw:
            row_weight = campus_w.get(closer_raw[0][0], {}).get(program, 0.0)
        elif farther_raw:
            row_weight = campus_w.get(farther_raw[0][0], {}).get(program, 0.0)
```

Then multiply every weight accumulation in that campus block by `row_weight`. Replace all occurrences of `+= closer_weight` with `+= closer_weight * row_weight` and `+= farther_weight` with `+= farther_weight * row_weight`, and `+= closer_weight * target_weight` with `+= closer_weight * target_weight * row_weight`, etc.

Specifically, the 8 accumulation lines in the campus block become:

```python
                if target_courses:
                    for closer_course, closer_weight in closer_raw:
                        for target_course, target_weight in target_courses:
                            mappings[campus]["closer_source_totals"][closer_course] += closer_weight * target_weight * row_weight
                    for farther_course, farther_weight in farther_courses:
                        for target_course, target_weight in target_courses:
                            mappings[campus]["farther_source_totals"][farther_course] += farther_weight * target_weight * row_weight
                else:
                    for closer_course, closer_weight in closer_raw:
                        mappings[campus]["closer_source_totals"][closer_course] += closer_weight * row_weight
                    for farther_course, farther_weight in farther_courses:
                        mappings[campus]["farther_source_totals"][farther_course] += farther_weight * row_weight
                    continue

                for target_course, target_weight in target_courses:
                    mappings[campus]["target_counts"][target_course] += target_weight * row_weight

                if not closer_courses:
                    for farther_course, farther_weight in farther_courses:
                        for target_course, target_weight in target_courses:
                            key = (farther_course, target_course)
                            mappings[campus]["farther_to_target"][key] += farther_weight * target_weight * row_weight

                for closer_course, closer_weight in closer_courses:
                    for target_course, target_weight in target_courses:
                        key = (closer_course, target_course)
                        mappings[campus]["closer_to_target"][key] += closer_weight * target_weight * row_weight
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest api/tests/test_forecaster_mapping.py::TestEnrollmentWeights -v
```

Expected: 4 tests PASS

**Step 5: Run full suite**

```bash
python -m pytest
```

Expected: all tests pass. If `TestYearFilter` or `TestLoadSequenceMappings` break, check that `row_weight=1.0` is correct when `enrollment_weights=None`.

**Step 6: Commit**

```bash
git add api/forecaster.py api/tests/test_forecaster_mapping.py
git commit -m "feat: add enrollment_weights parameter to load_sequence_mappings"
```

---

## Task 5: Wire both data sources through `run_sequence_forecast()` and config

**Files:**
- Modify: `api/forecaster.py` — add optional paths to `run_sequence_forecast`
- Modify: `api/main.py` — add `admitsFile`/`enrollmentByMajorFile` to `ConfigModel`, pass paths in forecast endpoint

**Step 1: Write the failing tests**

Add to `api/tests/test_forecaster_integration.py` (look at existing integration tests for the pattern) or add a new class to `api/tests/test_forecast_api.py`:

Check what's in `api/tests/test_forecaster_integration.py` first:

```bash
python -m pytest api/tests/test_forecaster_integration.py -v --collect-only
```

Add to `api/tests/test_forecaster_integration.py`:

```python
class TestRunSequenceForecastAdmits:
    def test_admits_path_none_does_not_crash(self, tmp_path):
        """run_sequence_forecast with admits_path=None works as before."""
        # Uses real data files — just verify it runs without error
        from pathlib import Path
        seq = Path("Data/FOUN_sequencing_map_by_major.csv")
        enr = Path("Data/Master Schedule of Classes.csv")
        if not seq.exists() or not enr.exists():
            pytest.skip("Real data files not present")
        rows = run_sequence_forecast(
            sequence_map_path=seq,
            enrollment_source_path=enr,
            target_term="Spring 2026",
            admits_path=None,
        )
        assert isinstance(rows, list)

    def test_admits_path_missing_file_falls_back_gracefully(self, tmp_path):
        """Missing admits file → no crash, just no new-admit demand added."""
        seq = Path("Data/FOUN_sequencing_map_by_major.csv")
        enr = Path("Data/Master Schedule of Classes.csv")
        if not seq.exists() or not enr.exists():
            pytest.skip("Real data files not present")
        rows_without = run_sequence_forecast(
            sequence_map_path=seq,
            enrollment_source_path=enr,
            target_term="Spring 2026",
        )
        rows_missing = run_sequence_forecast(
            sequence_map_path=seq,
            enrollment_source_path=enr,
            target_term="Spring 2026",
            admits_path=tmp_path / "nonexistent.xlsx",
        )
        # Nonexistent file should produce same result as no file
        assert rows_without == rows_missing
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest api/tests/test_forecaster_integration.py::TestRunSequenceForecastAdmits -v
```

Expected: `TypeError: run_sequence_forecast() got an unexpected keyword argument 'admits_path'`

**Step 3: Update `run_sequence_forecast` in `api/forecaster.py`**

Add two optional parameters to the function signature:

```python
def run_sequence_forecast(
    sequence_map_path: Path,
    enrollment_source_path: Path,
    target_term: str,
    capacity: int = 20,
    progression_rate: float = 0.95,
    buffer_percent: float = 0.0,
    admits_path: Optional[Path] = None,
    enrollment_by_major_path: Optional[Path] = None,
) -> List[Dict]:
```

Load enrollment weights after loading the crosswalk:

```python
    # Load optional enrollment-by-major weights for sequence map
    enrollment_weights = None
    if enrollment_by_major_path:
        enrollment_weights = load_enrollment_by_major(enrollment_by_major_path)

    year_filter = _active_curriculum_years(info["target_term_code"])
    mappings = load_sequence_mappings(
        sequence_map_path,
        target_quarter=target_quarter,
        closer_quarter=closer["quarter"],
        farther_quarter=farther["quarter"],
        year_filter=year_filter,
        enrollment_weights=enrollment_weights,
    )
```

After building `combined` for each campus (just before the `for course in mappings[campus]["target_counts"]` loop), add the new admits demand:

```python
        # Add new-admit FOUN demand (intro courses entered directly from admits file)
        if admits_path:
            admits_demand = load_admits_foun_demand(admits_path)
            for course, count in admits_demand.get(campus, {}).items():
                combined[course] += count
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest api/tests/test_forecaster_integration.py::TestRunSequenceForecastAdmits -v
```

Expected: 2 tests PASS (or SKIP if data files absent in CI).

**Step 5: Update `ConfigModel` in `api/main.py`**

Add two optional fields to `ConfigModel` (around line 219):

```python
class ConfigModel(BaseModel):
    capacity: int = Field(default=20, ge=1, le=100)
    progressionRate: float = Field(default=0.95, ge=0.0, le=1.0)
    bufferPercent: float = Field(default=10.0, ge=0.0, le=100.0)
    quartersToForecast: int = Field(default=2, ge=1, le=8)
    defaultTerm: str = "Spring 2026"
    admitsFile: Optional[str] = None
    enrollmentByMajorFile: Optional[str] = None
```

**Step 6: Wire paths into the forecast endpoint in `api/main.py`**

In the `POST /api/forecast` endpoint, after `sequence_map_path = resolve(...)`:

```python
        sequence_map_path = resolve("sequence_map", "Data/FOUN_sequencing_map_by_major.csv")
        enrollment_source_path = resolve("enrollment_source", "Data/Master Schedule of Classes.csv")

        # Optional data enrichment files (None = not configured)
        def resolve_optional(key: str) -> Optional[Path]:
            raw = disk_cfg.get(key)
            if not raw:
                return None
            p = Path(raw)
            return p if p.is_absolute() else PROJECT_ROOT / p

        admits_path = resolve_optional("admitsFile")
        enrollment_by_major_path = resolve_optional("enrollmentByMajorFile")

        # Run the real forecast
        rows = run_sequence_forecast(
            sequence_map_path=sequence_map_path,
            enrollment_source_path=enrollment_source_path,
            target_term=target_term,
            capacity=capacity,
            progression_rate=progression_rate,
            buffer_percent=buffer_percent,
            admits_path=admits_path,
            enrollment_by_major_path=enrollment_by_major_path,
        )
```

**Step 7: Run full suite**

```bash
python -m pytest
```

Expected: all tests pass.

**Step 8: Commit**

```bash
git add api/forecaster.py api/main.py api/tests/test_forecaster_integration.py
git commit -m "feat: wire admits and enrollment-by-major paths through run_sequence_forecast and config"
```

---

## Task 6: Validate Against Spring 2026 Projection

This task does not require new code — it validates the implementation against known ground truth.

**Step 1: Copy admissions file into Data/**

```bash
cp "/Users/nathanmadrid/Desktop/PZSAAPF-SL31 - Accepted Applicants with Latest Decision.xlsx" \
   "Data/PZSAAPF-SL31 - Accepted Applicants with Latest Decision.xlsx"
```

**Step 2: Update `forecast_config.json` to point to the admits file**

Edit `forecast_config.json` to add:

```json
"admitsFile": "Data/PZSAAPF-SL31 - Accepted Applicants with Latest Decision.xlsx"
```

Leave `enrollmentByMajorFile` absent for now — the Cognos report hasn't been pulled yet.

**Step 3: Start the tool and run the Spring 2026 forecast**

```bash
./Forecast_Tool_Launcher.command
```

Navigate to the UI at http://localhost:3000, select Spring 2026, and run forecast.

**Step 4: Compare results against the SCAD official projection**

Expected improvement vs. current state (with admits only, without enrollment-by-major):
- FOUN 110 (SAV): closer to 92 — new admits contribute ~30 real seats
- FOUN 111 (SAV): closer to 154 — new admits contribute ~32 real seats
- FOUN 112–260: unchanged until Cognos enrollment-by-major data is added

**Step 5: Once Cognos enrollment-by-major report is available**

1. Save it as `Data/enrollment_by_major.csv` with columns: `term, course, campus, major, enrollment`
2. Ensure `major` values match the `program` column in `FOUN_sequencing_map_by_major.csv` (uppercase, exact match — e.g., "ARCHITECTURE", "ACCESSORY DESIGN")
3. Add to `forecast_config.json`: `"enrollmentByMajorFile": "Data/enrollment_by_major.csv"`
4. Re-run the Spring 2026 forecast and compare against the projection file

**Step 6: Commit data files**

```bash
git add "Data/PZSAAPF-SL31 - Accepted Applicants with Latest Decision.xlsx"
git add forecast_config.json
git commit -m "data: add Spring 2026 admits file and update config paths"
```

---

## Cognos Report Request (for Step 5)

When pulling from Cognos, request a report with these exact specifications:

```
Report type:  Course Enrollment Summary (or Section Enrollment Detail)
Terms:        202610 (Fall 2025) AND 202620 (Winter 2026)
Filter:       Subject = FOUN
Campus:       SAV, NOW, and ATL (all three campuses)
Output cols:  term | course (e.g. "FOUN 112") | campus (SAV/NOW/ATL) | major | enrollment count
Aggregation:  Sum enrollment by (term + course + campus + major)
Format:       CSV, UTF-8
```

The `major` column must use full program names matching those in `FOUN_sequencing_map_by_major.csv`. If Cognos exports abbreviated codes (e.g., "ARCH"), create a one-column mapping to translate them before saving the file.

---

## Summary of Files Changed

| File | Change |
|---|---|
| `api/forecaster.py` | +ATL campus support in `load_term_enrollments`, `load_sequence_mappings`, `run_sequence_forecast`; +`load_admits_foun_demand`; +`load_enrollment_by_major`; +`enrollment_weights` param on `load_sequence_mappings`; +`admits_path`/`enrollment_by_major_path` params on `run_sequence_forecast` |
| `api/main.py` | +`admitsFile`/`enrollmentByMajorFile` on `ConfigModel`, +`resolve_optional()` + new params passed to `run_sequence_forecast` |
| `api/tests/test_forecaster_loaders.py` | +`TestLoadAdmitsFounDemand`, +`TestLoadEnrollmentByMajor` |
| `api/tests/test_forecaster_mapping.py` | +`TestEnrollmentWeights` |
| `api/tests/test_forecaster_integration.py` | +`TestRunSequenceForecastAdmits` |
| `.gitignore` | +`__pycache__/`, `.obsidian/`, `Data/.archives/` |
| Deleted | `calculate_foun_demand.py`, `forecast_fall26_foun.py`, `forecast_fall26_config.json`, `sample_enrollment_data.csv`, `Data/Spring_2026_FOUN_Forecast.csv`, `Data/Spring_2026_FOUN_Forecast_SAV_SCADnow.csv` |
| Moved | `Data_Gathering_Plan.md` → `docs/`, `foun_demand_logic.md` → `docs/` |
