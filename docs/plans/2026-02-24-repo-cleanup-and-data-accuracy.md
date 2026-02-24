# Repo Cleanup and Data Accuracy Design
**Date:** 2026-02-24
**Status:** Approved

## Problem

The forecast tool has two distinct issues:

1. **Repo clutter** — legacy scripts, tracked build artifacts, misplaced docs, and stale configs have accumulated since initial development.
2. **Forecast inaccuracy** — the sequence model treats all programs as equal-sized, causing significant over- and under-forecasting. Example: FOUN 220 forecasts 367 seats vs. the SCAD official projection of 187.

**Accuracy target:** Match the SCAD official seat projection file (`clon_sav_atl_seat_projection_*.xlsx`) for each term.

**Root cause of inaccuracy:** The sequence map weights every program row equally (1.0), but Architecture has ~10× more students than Jewelry Design. A "fraction" computed from row counts is not a reliable proxy for enrollment share.

---

## Section 1 — Repo Cleanup

### Files to delete
| File | Reason |
|---|---|
| `calculate_foun_demand.py` | Legacy script, fully superseded by `api/forecaster.py` |
| `forecast_fall26_foun.py` | Older Fall 26 script, superseded by `forecast_fall26_from_sequence_guides.py` |
| `forecast_fall26_config.json` | Stale one-off config, not canonical |
| `sample_enrollment_data.csv` | Unclear origin, not referenced anywhere |
| `Data/Spring_2026_FOUN_Forecast.csv` | Intermediate run, superseded by `_From_Sequence_Guides.csv` |
| `Data/Spring_2026_FOUN_Forecast_SAV_SCADnow.csv` | Intermediate run, superseded |

### Files to move
| From | To |
|---|---|
| `Data_Gathering_Plan.md` | `docs/Data_Gathering_Plan.md` |
| `foun_demand_logic.md` | `docs/foun_demand_logic.md` |

### `.gitignore` additions
Stop tracking the following (remove from index, add to `.gitignore`):
- `forecast_tool/__pycache__/` — compiled Python bytecode
- `forecast_tool/.DS_Store` — macOS metadata
- `.obsidian/` — editor config, not code
- `Data/.archives/` — old forecast CSVs, regenerated outputs

### CLI scripts to keep
All three remain active; do not delete:
- `forecast_spring26_from_sequence_guides.py`
- `forecast_fall26_from_sequence_guides.py`
- `forecast_summer26_foun.py`

---

## Section 2 — Data Strategy

### Source 1: Admissions file (already available)
**File:** `PZSAAPF-SL31 - Accepted Applicants with Latest Decision.xlsx`
**Key column:** U — "Currently Registered Courses (NO WL)"
**Use:** For intro courses (FOUN 110, 111), new admits represent 32–51% of total Spring demand. Reading their actual FOUN registrations directly from column U is far more accurate than projecting from the sequence map.
**Scope:** New admit component only. Does not affect FOUN 112–260 (continuing students dominate those courses — new admits are <2% of demand).

### Source 2: Enrollment by major — needs to be pulled from Cognos
**Purpose:** Fix the equal-weighting assumption. Replace sequence map row counts with actual enrollment proportions per major per FOUN course.

**Cognos report specification:**
```
Report:  Section Enrollment Detail (or equivalent course roster summary)
Terms:   202610 (Fall 2025), 202620 (Winter 2026)
Filter:  Subject = FOUN
Fields:
  - Term code
  - Course code (e.g., FOUN 112)
  - Campus (SAV / NOW)
  - Major / Program code
  - Enrollment count (aggregate — no student IDs needed, FERPA compliant)
Format:  Excel or CSV
```

**Effect once available:**

| Course | Current forecast | SCAD projection | Expected after fix |
|---|---|---|---|
| FOUN 220 | 367 | 187 | ~180–200 |
| FOUN 240 | 97 | 16 | ~15–20 |
| FOUN 111 | 70 | 154 | ~140–160 |
| FOUN 112 | 505 | 598 | ~580–610 |

---

## Section 3 — Forecasting Engine Changes

Three focused additions to `api/forecaster.py`. All are opt-in via config — missing files fall back to current behavior.

### Change 1: New admits loader
```python
def load_admits_foun_demand(path: Path) -> Dict[str, Counter]:
    """Read PZSAAPF-SL31 xlsx, extract FOUN courses from col U (registered courses).
    Returns {campus_code: {foun_course: count}}.
    Campus codes: 'M' → 'SAVANNAH', 'O' → 'SCADNOW'.
    """
```
`run_sequence_forecast()` accepts optional `admits_path` parameter. When present, new admit FOUN counts are added to the continuing student projection for FOUN 110 and 111.

### Change 2: Enrollment-by-major loader
```python
def load_enrollment_by_major(path: Path) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Read Cognos enrollment-by-major CSV/xlsx.
    Returns {campus: {foun_course: {major_code: enrollment_count}}}.
    """
```
`load_sequence_mappings()` accepts optional `enrollment_weights` parameter. When provided, each program row in the sequence map is weighted by `enrollment_count[major] / total_enrollment[foun_course]` instead of 1.0.

### Change 3: Config file wiring
Two new optional fields in `forecast_config.json`:
```json
"admits_file": "Data/PZSAAPF-SL31 - Accepted Applicants with Latest Decision.xlsx",
"enrollment_by_major_file": "Data/enrollment_by_major.csv"
```
`api/main.py` passes these paths to `run_sequence_forecast()` when the files exist. If absent, no change in behavior.

### What does not change
- Sequence map format and logic
- Year filter (`_active_curriculum_years`)
- Ratio fallback for Summer
- Adjustment system
- CLI scripts
- Frontend

---

## Implementation Order

1. Repo cleanup (delete files, fix gitignore, move docs)
2. Pull enrollment-by-major Cognos report
3. Implement `load_admits_foun_demand()` + wire into `run_sequence_forecast()`
4. Implement `load_enrollment_by_major()` + wire into `load_sequence_mappings()`
5. Update `forecast_config.json` schema + `api/main.py` wiring
6. Test against Spring 2026 SCAD projection as ground truth
