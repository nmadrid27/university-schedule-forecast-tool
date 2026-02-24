"""Tests for load_term_enrollments and get_available_terms.

load_term_enrollments handles two distinct CSV layouts:
  - Term CSV:  Course / Section # / Room / Enrollment columns
  - Master Schedule: SUBJ / CRS NUMBER / ACT ENR / CAMPUS / TERM columns

get_available_terms scans the Master Schedule for distinct TERM values.
"""

import sys
from pathlib import Path

import openpyxl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forecaster import get_available_terms, load_admits_foun_demand, load_enrollment_by_major, load_term_enrollments


# ── Fixture helpers ────────────────────────────────────────────────────────────

def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


# ── load_term_enrollments — term CSV format ────────────────────────────────────

class TestLoadTermEnrollmentsTermCSV:
    """Term CSV uses Course / Section # / Room / Enrollment columns."""

    def test_loads_savannah_enrollment(self, tmp_path):
        csv = tmp_path / "term.csv"
        _write(csv, "Course,Section #,Room,Enrollment\nFOUN 110,S01,SAV-101,100\n")
        result = load_term_enrollments(csv)
        assert result[("SAVANNAH", "FOUN 110")] == 100.0

    def test_scadnow_detected_by_olnow_room(self, tmp_path):
        csv = tmp_path / "term.csv"
        _write(csv, "Course,Section #,Room,Enrollment\nFOUN 110,S01,OLNOW,50\n")
        result = load_term_enrollments(csv)
        assert result[("SCADNOW", "FOUN 110")] == 50.0

    def test_scadnow_detected_by_n_prefixed_section(self, tmp_path):
        csv = tmp_path / "term.csv"
        _write(csv, "Course,Section #,Room,Enrollment\nFOUN 230,N01,STUDIO,40\n")
        result = load_term_enrollments(csv)
        assert result[("SCADNOW", "FOUN 230")] == 40.0

    def test_non_foun_courses_are_excluded(self, tmp_path):
        csv = tmp_path / "term.csv"
        _write(csv, "Course,Section #,Room,Enrollment\nDRAW 200,S01,SAV-101,80\n")
        result = load_term_enrollments(csv)
        assert len(result) == 0

    def test_multiple_sections_accumulate_for_same_course(self, tmp_path):
        csv = tmp_path / "term.csv"
        _write(csv,
            "Course,Section #,Room,Enrollment\n"
            "FOUN 110,S01,SAV-101,50\n"
            "FOUN 110,S02,SAV-102,60\n"
        )
        result = load_term_enrollments(csv)
        assert result[("SAVANNAH", "FOUN 110")] == 110.0

    def test_empty_file_returns_empty_dict(self, tmp_path):
        csv = tmp_path / "term.csv"
        _write(csv, "Course,Section #,Room,Enrollment\n")
        assert load_term_enrollments(csv) == {}

    def test_crosswalk_maps_legacy_code_to_foun(self, tmp_path):
        csv = tmp_path / "term.csv"
        _write(csv, "Course,Section #,Room,Enrollment\nDRAW 200,S01,SAV-101,75\n")
        result = load_term_enrollments(csv, crosswalk={"DRAW 200": "FOUN 230"})
        assert result[("SAVANNAH", "FOUN 230")] == 75.0

    def test_crosswalk_does_not_affect_already_foun_codes(self, tmp_path):
        csv = tmp_path / "term.csv"
        _write(csv, "Course,Section #,Room,Enrollment\nFOUN 110,S01,SAV-101,90\n")
        result = load_term_enrollments(csv, crosswalk={"FOUN 110": "FOUN 999"})
        # Crosswalk maps the key exactly; FOUN 110 → FOUN 999, but still FOUN prefix
        assert result[("SAVANNAH", "FOUN 999")] == 90.0


# ── load_term_enrollments — Master Schedule format ────────────────────────────

class TestLoadTermEnrollmentsMasterSchedule:
    """Master Schedule uses SUBJ / CRS NUMBER / ACT ENR / CAMPUS / TERM."""

    def _master(self, path: Path, rows: list[dict]) -> None:
        lines = ["SUBJ,CRS NUMBER,ACT ENR,CAMPUS,TERM"]
        for r in rows:
            lines.append(f"{r['subj']},{r['crs']},{r['enr']},{r['campus']},{r['term']}")
        _write(path, "\n".join(lines) + "\n")

    def test_loads_savannah_row_with_term_filter(self, tmp_path):
        csv = tmp_path / "master.csv"
        self._master(csv, [{"subj": "FOUN", "crs": "110", "enr": 100, "campus": "SAV", "term": "202630"}])
        result = load_term_enrollments(csv, term_code="202630")
        assert result[("SAVANNAH", "FOUN 110")] == 100.0

    def test_loads_scadnow_row(self, tmp_path):
        csv = tmp_path / "master.csv"
        self._master(csv, [{"subj": "FOUN", "crs": "230", "enr": 60, "campus": "NOW", "term": "202630"}])
        result = load_term_enrollments(csv, term_code="202630")
        assert result[("SCADNOW", "FOUN 230")] == 60.0

    def test_term_filter_excludes_other_terms(self, tmp_path):
        csv = tmp_path / "master.csv"
        self._master(csv, [
            {"subj": "FOUN", "crs": "110", "enr": 100, "campus": "SAV", "term": "202630"},
            {"subj": "FOUN", "crs": "110", "enr": 50,  "campus": "SAV", "term": "202620"},
        ])
        result = load_term_enrollments(csv, term_code="202630")
        assert result[("SAVANNAH", "FOUN 110")] == 100.0

    def test_no_term_filter_loads_all_terms(self, tmp_path):
        csv = tmp_path / "master.csv"
        self._master(csv, [
            {"subj": "FOUN", "crs": "110", "enr": 100, "campus": "SAV", "term": "202630"},
            {"subj": "FOUN", "crs": "110", "enr": 50,  "campus": "SAV", "term": "202620"},
        ])
        result = load_term_enrollments(csv)  # no term_code
        assert result[("SAVANNAH", "FOUN 110")] == 150.0

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

    def test_non_foun_subjects_excluded(self, tmp_path):
        csv = tmp_path / "master.csv"
        self._master(csv, [{"subj": "DRAW", "crs": "200", "enr": 70, "campus": "SAV", "term": "202630"}])
        result = load_term_enrollments(csv, term_code="202630")
        assert len(result) == 0

    def test_crosswalk_maps_legacy_subject_code(self, tmp_path):
        csv = tmp_path / "master.csv"
        self._master(csv, [{"subj": "DRAW", "crs": "200", "enr": 70, "campus": "SAV", "term": "202630"}])
        result = load_term_enrollments(csv, term_code="202630", crosswalk={"DRAW 200": "FOUN 230"})
        assert result[("SAVANNAH", "FOUN 230")] == 70.0

    def test_multiple_sections_accumulate(self, tmp_path):
        csv = tmp_path / "master.csv"
        self._master(csv, [
            {"subj": "FOUN", "crs": "110", "enr": 20, "campus": "SAV", "term": "202630"},
            {"subj": "FOUN", "crs": "110", "enr": 18, "campus": "SAV", "term": "202630"},
        ])
        result = load_term_enrollments(csv, term_code="202630")
        assert result[("SAVANNAH", "FOUN 110")] == 38.0

    def test_missing_crs_number_skipped(self, tmp_path):
        csv = tmp_path / "master.csv"
        _write(csv, "SUBJ,CRS NUMBER,ACT ENR,CAMPUS,TERM\nFOUN,,20,SAV,202630\n")
        result = load_term_enrollments(csv, term_code="202630")
        assert len(result) == 0


# ── get_available_terms ────────────────────────────────────────────────────────

class TestGetAvailableTerms:
    def test_returns_sorted_unique_term_codes(self, tmp_path):
        csv = tmp_path / "master.csv"
        csv.write_text(
            "TERM,SUBJ,CRS NUMBER\n"
            "202630,FOUN,110\n"
            "202610,FOUN,110\n"
            "202630,FOUN,230\n"
        )
        result = get_available_terms(csv)
        assert result == ["202610", "202630"]

    def test_empty_file_returns_empty_list(self, tmp_path):
        csv = tmp_path / "master.csv"
        csv.write_text("TERM,SUBJ,CRS NUMBER\n")
        assert get_available_terms(csv) == []

    def test_skips_rows_with_empty_term(self, tmp_path):
        csv = tmp_path / "master.csv"
        csv.write_text("TERM,SUBJ,CRS NUMBER\n,FOUN,110\n202630,FOUN,230\n")
        result = get_available_terms(csv)
        assert result == ["202630"]


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


# ── load_enrollment_by_major ──────────────────────────────────────────────────


class TestLoadEnrollmentByMajor:
    def _csv(self, tmp_path: Path, rows: list) -> Path:
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
