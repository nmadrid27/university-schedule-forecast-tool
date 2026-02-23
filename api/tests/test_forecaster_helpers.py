"""Tests for pure helper functions in forecaster.py:
normalize_text, parse_campuses, campus_matches,
extract_foun_codes, parse_quarter_courses, parse_number,
load_crosswalk, load_previous_forecast.
"""

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forecaster import (
    campus_matches,
    extract_foun_codes,
    load_crosswalk,
    load_previous_forecast,
    normalize_text,
    parse_campuses,
    parse_number,
    parse_quarter_courses,
)


# ─── normalize_text ───────────────────────────────────────────────────────

class TestNormalizeText:
    def test_uppercases(self):
        assert normalize_text("hello world") == "HELLO WORLD"

    def test_collapses_whitespace(self):
        assert normalize_text("  A   B  ") == "A B"

    def test_replaces_ampersand(self):
        assert normalize_text("Art & Design") == "ART AND DESIGN"

    def test_empty_string_returns_empty(self):
        assert normalize_text("") == ""

    def test_none_returns_empty(self):
        assert normalize_text(None) == ""

    def test_tabs_and_newlines_collapsed(self):
        assert normalize_text("A\t\nB") == "A B"


# ─── parse_campuses ───────────────────────────────────────────────────────

class TestParseCampuses:
    def test_general_returns_general(self):
        assert parse_campuses("GENERAL") == ("GENERAL",)

    def test_single_campus(self):
        assert parse_campuses("SAVANNAH") == ("SAVANNAH",)

    def test_pipe_separated(self):
        result = parse_campuses("SAVANNAH|SCADNOW")
        assert "SAVANNAH" in result
        assert "SCADNOW" in result

    def test_strips_major_course_sequencing_guide_suffix(self):
        # Some CSV cells have this trailer; it should be removed before parsing
        result = parse_campuses("GENERAL Major Course Sequencing Guide")
        assert result == ("GENERAL",)

    def test_empty_returns_empty_tuple(self):
        assert parse_campuses("") == ()

    def test_lowercase_normalized(self):
        assert parse_campuses("general") == ("GENERAL",)


# ─── campus_matches ───────────────────────────────────────────────────────

class TestCampusMatches:
    def test_general_matches_any_campus(self):
        assert campus_matches(("GENERAL",), "SAVANNAH") is True
        assert campus_matches(("GENERAL",), "SCADNOW") is True

    def test_exact_match(self):
        assert campus_matches(("SAVANNAH",), "SAVANNAH") is True

    def test_no_match(self):
        assert campus_matches(("SAVANNAH",), "SCADNOW") is False

    def test_multiple_campuses(self):
        assert campus_matches(("SAVANNAH", "SCADNOW"), "SCADNOW") is True

    def test_empty_campuses_no_match(self):
        assert campus_matches((), "SAVANNAH") is False


# ─── extract_foun_codes ───────────────────────────────────────────────────

class TestExtractFounCodes:
    def test_single_code(self):
        assert extract_foun_codes("FOUN 110") == ["FOUN 110"]

    def test_multiple_codes(self):
        result = extract_foun_codes("FOUN 110 or FOUN 120")
        assert "FOUN 110" in result
        assert "FOUN 120" in result

    def test_deduplicates_repeated_code(self):
        assert extract_foun_codes("FOUN 110 FOUN 110") == ["FOUN 110"]

    def test_empty_returns_empty(self):
        assert extract_foun_codes("") == []

    def test_none_returns_empty(self):
        assert extract_foun_codes(None) == []

    def test_no_foun_code_returns_empty(self):
        assert extract_foun_codes("DRAW 200") == []

    def test_preserves_order(self):
        result = extract_foun_codes("FOUN 230 and FOUN 110")
        assert result == ["FOUN 230", "FOUN 110"]

    def test_case_insensitive(self):
        assert extract_foun_codes("foun 110") == ["FOUN 110"]


# ─── parse_quarter_courses ────────────────────────────────────────────────

class TestParseQuarterCourses:
    def test_single_course_weight_one(self):
        result = parse_quarter_courses("FOUN 110")
        assert result == [("FOUN 110", 1.0)]

    def test_choice_splits_weight_evenly(self):
        result = parse_quarter_courses("CHOICE: FOUN 110 or FOUN 120")
        assert len(result) == 2
        for _, weight in result:
            assert weight == pytest.approx(0.5)

    def test_three_way_choice(self):
        result = parse_quarter_courses("CHOICE FOUN 110 FOUN 120 FOUN 130")
        assert len(result) == 3
        for _, weight in result:
            assert weight == pytest.approx(1 / 3)

    def test_empty_returns_empty(self):
        assert parse_quarter_courses("") == []

    def test_none_returns_empty(self):
        assert parse_quarter_courses(None) == []

    def test_no_foun_codes_returns_empty(self):
        assert parse_quarter_courses("See advisor") == []

    def test_concurrent_courses_weight_one_each(self):
        # Multiple codes without CHOICE = concurrent co-reqs, weight 1.0 each
        result = parse_quarter_courses("FOUN 110 FOUN 120")
        assert all(w == 1.0 for _, w in result)


# ─── parse_number ─────────────────────────────────────────────────────────

class TestParseNumber:
    def test_integer_string(self):
        assert parse_number("42") == 42.0

    def test_float_string(self):
        assert parse_number("3.14") == pytest.approx(3.14)

    def test_comma_separated(self):
        assert parse_number("1,200") == 1200.0

    def test_empty_string_returns_zero(self):
        assert parse_number("") == 0.0

    def test_none_returns_zero(self):
        assert parse_number(None) == 0.0

    def test_non_numeric_returns_zero(self):
        assert parse_number("N/A") == 0.0


# ─── load_crosswalk ───────────────────────────────────────────────────────

class TestLoadCrosswalk:
    def test_loads_mappings(self, tmp_path):
        csv_file = tmp_path / "crosswalk.csv"
        csv_file.write_text("legacy_code,foun_code\nDSGN 100,FOUN 110\nDRAW 200,FOUN 230\n")
        result = load_crosswalk(csv_file)
        assert result["DSGN 100"] == "FOUN 110"
        assert result["DRAW 200"] == "FOUN 230"

    def test_returns_empty_when_file_missing(self, tmp_path):
        assert load_crosswalk(tmp_path / "nonexistent.csv") == {}

    def test_skips_rows_with_empty_codes(self, tmp_path):
        csv_file = tmp_path / "crosswalk.csv"
        csv_file.write_text("legacy_code,foun_code\nDSGN 100,FOUN 110\n,\n")
        result = load_crosswalk(csv_file)
        assert len(result) == 1


# ─── load_previous_forecast ───────────────────────────────────────────────

class TestLoadPreviousForecast:
    def _write_csv(self, path: Path, rows: list, fieldnames: list):
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

    def test_loads_projected_seats(self, tmp_path):
        csv_file = tmp_path / "forecast.csv"
        self._write_csv(csv_file,
            [{"course": "FOUN 110", "campus": "SAV", "projected_seats": "100"}],
            ["course", "campus", "projected_seats"])
        result = load_previous_forecast(csv_file)
        assert result[("FOUN 110", "SAV")] == 100.0

    def test_falls_back_to_suffixed_column(self, tmp_path):
        csv_file = tmp_path / "forecast.csv"
        self._write_csv(csv_file,
            [{"course": "FOUN 110", "campus": "SAV", "spring_projected_seats": "80"}],
            ["course", "campus", "spring_projected_seats"])
        result = load_previous_forecast(csv_file)
        assert result[("FOUN 110", "SAV")] == 80.0

    def test_returns_empty_when_file_missing(self, tmp_path):
        assert load_previous_forecast(tmp_path / "nope.csv") == {}

    def test_returns_empty_when_no_seats_column(self, tmp_path):
        csv_file = tmp_path / "forecast.csv"
        self._write_csv(csv_file,
            [{"course": "FOUN 110", "campus": "SAV"}],
            ["course", "campus"])
        assert load_previous_forecast(csv_file) == {}

    def test_multiple_rows(self, tmp_path):
        csv_file = tmp_path / "forecast.csv"
        self._write_csv(csv_file,
            [
                {"course": "FOUN 110", "campus": "SAV", "projected_seats": "100"},
                {"course": "FOUN 120", "campus": "NOW", "projected_seats": "50"},
            ],
            ["course", "campus", "projected_seats"])
        result = load_previous_forecast(csv_file)
        assert len(result) == 2
        assert result[("FOUN 120", "NOW")] == 50.0
