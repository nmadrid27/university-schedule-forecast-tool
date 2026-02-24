"""Tests for forecast_tool.data.loaders.

load_course_mapping: reads crosswalk CSV, returns legacy→FOUN dict
load_historical_data: reads FOUN_Historical.csv, parses TERM codes, applies crosswalk
calculate_summer_ratios: computes per-course Summer/Spring enrollment ratios
"""

from pathlib import Path

import pandas as pd
import pytest

from forecast_tool.data.loaders import (
    calculate_summer_ratios,
    load_course_mapping,
    load_historical_data,
)


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _hist_csv(tmp_path: Path, rows: list) -> None:
    """Write a minimal FOUN_Historical.csv."""
    lines = ["SUBJ,CRS NUMBER,ACT ENR,TERM"]
    for r in rows:
        lines.append(f"{r['subj']},{r['crs']},{r['enr']},{r['term']}")
    _write(tmp_path / "FOUN_Historical.csv", "\n".join(lines) + "\n")


# ── load_course_mapping ────────────────────────────────────────────────────────

class TestLoadCourseMapping:
    def test_loads_mapping_from_csv(self, tmp_path):
        _write(tmp_path / "sequence_crosswalk_template.csv",
               "legacy_code,foun_code\nDRAW 200,FOUN 230\nDSGN 100,FOUN 110\n")
        result = load_course_mapping(data_dir=str(tmp_path))
        assert result["DRAW 200"] == "FOUN 230"
        assert result["DSGN 100"] == "FOUN 110"

    def test_missing_file_returns_empty_dict(self, tmp_path):
        # No CSV written → should return {}
        assert load_course_mapping(data_dir=str(tmp_path)) == {}

    def test_strips_whitespace_from_codes(self, tmp_path):
        _write(tmp_path / "sequence_crosswalk_template.csv",
               "legacy_code,foun_code\n DRAW 200 , FOUN 230 \n")
        result = load_course_mapping(data_dir=str(tmp_path))
        assert result["DRAW 200"] == "FOUN 230"

    def test_empty_csv_returns_empty_dict(self, tmp_path):
        _write(tmp_path / "sequence_crosswalk_template.csv", "legacy_code,foun_code\n")
        assert load_course_mapping(data_dir=str(tmp_path)) == {}

    def test_returns_dict(self, tmp_path):
        _write(tmp_path / "sequence_crosswalk_template.csv",
               "legacy_code,foun_code\nDRAW 200,FOUN 230\n")
        assert isinstance(load_course_mapping(data_dir=str(tmp_path)), dict)


# ── load_historical_data ───────────────────────────────────────────────────────

class TestLoadHistoricalData:
    def test_returns_dataframe(self, tmp_path):
        _hist_csv(tmp_path, [{"subj": "FOUN", "crs": "110", "enr": 80, "term": 202630}])
        df = load_historical_data(data_dir=str(tmp_path))
        assert isinstance(df, pd.DataFrame)

    def test_missing_file_returns_empty_dataframe(self, tmp_path):
        df = load_historical_data(data_dir=str(tmp_path))
        assert df.empty

    def test_spring_term_code_parsed(self, tmp_path):
        # 202630 → Spring 2026
        _hist_csv(tmp_path, [{"subj": "FOUN", "crs": "110", "enr": 80, "term": 202630}])
        df = load_historical_data(data_dir=str(tmp_path))
        assert df.iloc[0]["quarter"] == "Spring"
        assert df.iloc[0]["year"] == 2026

    def test_fall_term_code_subtracts_one_from_year(self, tmp_path):
        # 202610 → Fall 2025 (year_part=2026, year=2025)
        _hist_csv(tmp_path, [{"subj": "FOUN", "crs": "110", "enr": 80, "term": 202610}])
        df = load_historical_data(data_dir=str(tmp_path))
        assert df.iloc[0]["quarter"] == "Fall"
        assert df.iloc[0]["year"] == 2025

    def test_winter_term_code_parsed(self, tmp_path):
        # 202620 → Winter 2026
        _hist_csv(tmp_path, [{"subj": "FOUN", "crs": "110", "enr": 80, "term": 202620}])
        df = load_historical_data(data_dir=str(tmp_path))
        assert df.iloc[0]["quarter"] == "Winter"
        assert df.iloc[0]["year"] == 2026

    def test_summer_term_code_parsed(self, tmp_path):
        # 202640 → Summer 2026
        _hist_csv(tmp_path, [{"subj": "FOUN", "crs": "110", "enr": 80, "term": 202640}])
        df = load_historical_data(data_dir=str(tmp_path))
        assert df.iloc[0]["quarter"] == "Summer"
        assert df.iloc[0]["year"] == 2026

    def test_course_code_combines_subj_and_crs(self, tmp_path):
        _hist_csv(tmp_path, [{"subj": "FOUN", "crs": "230", "enr": 60, "term": 202630}])
        df = load_historical_data(data_dir=str(tmp_path))
        assert df.iloc[0]["course_code"] == "FOUN 230"

    def test_waitlist_column_is_always_zero(self, tmp_path):
        _hist_csv(tmp_path, [
            {"subj": "FOUN", "crs": "110", "enr": 80, "term": 202630},
            {"subj": "FOUN", "crs": "230", "enr": 50, "term": 202630},
        ])
        df = load_historical_data(data_dir=str(tmp_path))
        assert (df["waitlist"] == 0).all()

    def test_output_has_required_columns(self, tmp_path):
        _hist_csv(tmp_path, [{"subj": "FOUN", "crs": "110", "enr": 80, "term": 202630}])
        df = load_historical_data(data_dir=str(tmp_path))
        for col in ["year", "quarter", "course_code", "enrollment", "waitlist"]:
            assert col in df.columns

    def test_enrollment_value_preserved(self, tmp_path):
        _hist_csv(tmp_path, [{"subj": "FOUN", "crs": "110", "enr": 95, "term": 202630}])
        df = load_historical_data(data_dir=str(tmp_path))
        assert df.iloc[0]["enrollment"] == 95

    def test_crosswalk_applied_when_present(self, tmp_path):
        _hist_csv(tmp_path, [{"subj": "DRAW", "crs": "200", "enr": 75, "term": 202630}])
        _write(tmp_path / "sequence_crosswalk_template.csv",
               "legacy_code,foun_code\nDRAW 200,FOUN 230\n")
        df = load_historical_data(data_dir=str(tmp_path))
        assert df.iloc[0]["course_code"] == "FOUN 230"

    def test_unmapped_course_code_preserved(self, tmp_path):
        # FOUN 110 has no crosswalk entry → kept as-is
        _hist_csv(tmp_path, [{"subj": "FOUN", "crs": "110", "enr": 80, "term": 202630}])
        _write(tmp_path / "sequence_crosswalk_template.csv",
               "legacy_code,foun_code\nDRAW 200,FOUN 230\n")
        df = load_historical_data(data_dir=str(tmp_path))
        assert df.iloc[0]["course_code"] == "FOUN 110"


# ── calculate_summer_ratios ────────────────────────────────────────────────────

class TestCalculateSummerRatios:
    def _df(self, rows):
        return pd.DataFrame(rows)

    def test_computes_ratio_from_spring_and_summer(self):
        df = self._df([
            {"course_code": "FOUN 110", "year": 2022, "quarter": "Spring", "enrollment": 100},
            {"course_code": "FOUN 110", "year": 2022, "quarter": "Summer", "enrollment": 20},
        ])
        assert calculate_summer_ratios(df)["FOUN 110"] == pytest.approx(0.20)

    def test_averages_ratios_across_multiple_years(self):
        # Year 1: 20/100=0.20, Year 2: 30/100=0.30 → avg 0.25
        df = self._df([
            {"course_code": "FOUN 110", "year": 2022, "quarter": "Spring", "enrollment": 100},
            {"course_code": "FOUN 110", "year": 2022, "quarter": "Summer", "enrollment": 20},
            {"course_code": "FOUN 110", "year": 2023, "quarter": "Spring", "enrollment": 100},
            {"course_code": "FOUN 110", "year": 2023, "quarter": "Summer", "enrollment": 30},
        ])
        assert calculate_summer_ratios(df)["FOUN 110"] == pytest.approx(0.25)

    def test_course_with_no_spring_data_excluded(self):
        df = self._df([
            {"course_code": "FOUN 110", "year": 2022, "quarter": "Summer", "enrollment": 20},
        ])
        assert "FOUN 110" not in calculate_summer_ratios(df)

    def test_zero_spring_enrollment_skipped(self):
        # Guard: spring_val > 0 — avoids division by zero
        df = self._df([
            {"course_code": "FOUN 110", "year": 2022, "quarter": "Spring", "enrollment": 0},
            {"course_code": "FOUN 110", "year": 2022, "quarter": "Summer", "enrollment": 10},
        ])
        assert "FOUN 110" not in calculate_summer_ratios(df)

    def test_missing_required_columns_returns_empty(self):
        df = pd.DataFrame({"x": [1, 2]})
        assert calculate_summer_ratios(df) == {}

    def test_multiple_courses_computed_independently(self):
        df = self._df([
            {"course_code": "FOUN 110", "year": 2022, "quarter": "Spring", "enrollment": 100},
            {"course_code": "FOUN 110", "year": 2022, "quarter": "Summer", "enrollment": 10},
            {"course_code": "FOUN 230", "year": 2022, "quarter": "Spring", "enrollment": 50},
            {"course_code": "FOUN 230", "year": 2022, "quarter": "Summer", "enrollment": 15},
        ])
        ratios = calculate_summer_ratios(df)
        assert ratios["FOUN 110"] == pytest.approx(0.10)
        assert ratios["FOUN 230"] == pytest.approx(0.30)

    def test_returns_dict(self):
        df = self._df([
            {"course_code": "FOUN 110", "year": 2022, "quarter": "Spring", "enrollment": 80},
            {"course_code": "FOUN 110", "year": 2022, "quarter": "Summer", "enrollment": 16},
        ])
        assert isinstance(calculate_summer_ratios(df), dict)
