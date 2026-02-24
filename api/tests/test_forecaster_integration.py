"""Integration tests for run_sequence_forecast and run_ratio_forecast.

These tests exercise the full forecast pipeline with minimal CSV fixtures,
verifying that the orchestrator functions correctly wire together:
  load_sequence_mappings, load_term_enrollments, distribute_enrollments,
  compute_sections, and buffer application.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forecaster import run_sequence_forecast, run_ratio_forecast


# ── Fixture helpers ────────────────────────────────────────────────────────────

def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _sequence_map(tmp_path: Path, fall="", winter="", spring="", summer="",
                  campus="GENERAL") -> Path:
    """Minimal sequence map with one row. Returns path."""
    p = tmp_path / "seq_map.csv"
    _write(p, (
        "program,degree,campus,year,fall,winter,spring,summer\n"
        f"TEST PROG,Test BFA,{campus},First Year,"
        f"{fall},{winter},{spring},{summer}\n"
    ))
    return p


def _master_schedule(tmp_path: Path, rows: list[dict]) -> Path:
    """Minimal Master Schedule CSV (SUBJ/CRS NUMBER/ACT ENR/CAMPUS/TERM format)."""
    p = tmp_path / "master.csv"
    lines = ["SUBJ,CRS NUMBER,ACT ENR,CAMPUS,TERM"]
    for r in rows:
        lines.append(f"{r['subj']},{r['crs']},{r['enr']},{r['campus']},{r['term']}")
    _write(p, "\n".join(lines) + "\n")
    return p


def _historical_csv(tmp_path: Path, rows: list[dict]) -> Path:
    """Minimal FOUN_Historical.csv (SUBJ/CRS NUMBER/ACT ENR/TERM columns)."""
    p = tmp_path / "FOUN_Historical.csv"
    lines = ["DEPT,SUBJ,CRS NUMBER,CAMPUS,MAX ENR,ACT ENR,TERM"]
    for r in rows:
        lines.append(
            f"FOUN,{r['subj']},{r['crs']},SAV,20,{r['enr']},{r['term']}"
        )
    _write(p, "\n".join(lines) + "\n")
    return p


def _feeder_forecast_csv(tmp_path: Path, rows: list[dict]) -> Path:
    """Minimal feeder forecast CSV (course/campus/projected_seats columns)."""
    p = tmp_path / "spring_forecast.csv"
    lines = ["course,campus,projected_seats"]
    for r in rows:
        lines.append(f"{r['course']},{r['campus']},{r['seats']}")
    _write(p, "\n".join(lines) + "\n")
    return p


# ── run_sequence_forecast ──────────────────────────────────────────────────────

class TestRunSequenceForecast:
    """Target: Spring 2026 (fall 202610 = farther feeder, winter 202620 = closer feeder)."""

    def _seq_map(self, tmp_path):
        # FOUN 110 in fall → FOUN 230 in spring; no winter data
        return _sequence_map(tmp_path, fall="FOUN 110", spring="FOUN 230")

    def _master(self, tmp_path, enr_fall=100, enr_winter=0):
        rows = [{"subj": "FOUN", "crs": "110", "enr": enr_fall,
                 "campus": "SAV", "term": "202610"}]
        if enr_winter > 0:
            rows.append({"subj": "FOUN", "crs": "110", "enr": enr_winter,
                         "campus": "SAV", "term": "202620"})
        return _master_schedule(tmp_path, rows)

    def test_returns_list(self, tmp_path):
        result = run_sequence_forecast(
            self._seq_map(tmp_path), self._master(tmp_path), "Spring 2026"
        )
        assert isinstance(result, list)

    def test_includes_savannah_row_for_mapped_course(self, tmp_path):
        result = run_sequence_forecast(
            self._seq_map(tmp_path), self._master(tmp_path), "Spring 2026"
        )
        courses = [(r["course"], r["campus"]) for r in result]
        assert ("FOUN 230", "Savannah") in courses

    def test_projected_seats_applies_progression_rate(self, tmp_path):
        result = run_sequence_forecast(
            self._seq_map(tmp_path), self._master(tmp_path, enr_fall=100),
            "Spring 2026", progression_rate=0.95,
        )
        sav = next(r for r in result if r["campus"] == "Savannah" and r["course"] == "FOUN 230")
        # farther feeder (exp=2): 100 * 0.95^2 = 90.25
        assert sav["projected_seats"] == pytest.approx(90.25, abs=0.5)

    def test_sections_computed_from_seats_and_capacity(self, tmp_path):
        result = run_sequence_forecast(
            self._seq_map(tmp_path), self._master(tmp_path, enr_fall=100),
            "Spring 2026", capacity=20, progression_rate=0.95,
        )
        sav = next(r for r in result if r["campus"] == "Savannah" and r["course"] == "FOUN 230")
        expected_sections = math.ceil(sav["projected_seats"] / 20)
        assert sav["sections"] == expected_sections

    def test_buffer_percent_scales_seats(self, tmp_path):
        base = run_sequence_forecast(
            self._seq_map(tmp_path), self._master(tmp_path, enr_fall=100),
            "Spring 2026", buffer_percent=0.0,
        )
        buffered = run_sequence_forecast(
            self._seq_map(tmp_path), self._master(tmp_path, enr_fall=100),
            "Spring 2026", buffer_percent=10.0,
        )
        base_sav = next(r for r in base if r["campus"] == "Savannah" and r["course"] == "FOUN 230")
        buf_sav = next(r for r in buffered if r["campus"] == "Savannah" and r["course"] == "FOUN 230")
        assert buf_sav["projected_seats"] == pytest.approx(base_sav["projected_seats"] * 1.1, rel=0.01)

    def test_method_field_is_sequence_map_feeder_mapping(self, tmp_path):
        result = run_sequence_forecast(
            self._seq_map(tmp_path), self._master(tmp_path), "Spring 2026"
        )
        sav = next(r for r in result if r["campus"] == "Savannah" and r["course"] == "FOUN 230")
        assert sav["method"] == "sequence_map_feeder_mapping"

    def test_empty_sequence_map_returns_empty_list(self, tmp_path):
        # Sequence map with no target quarter data → no rows
        seq_map = _sequence_map(tmp_path, fall="FOUN 110", spring="")
        result = run_sequence_forecast(
            seq_map, self._master(tmp_path), "Spring 2026"
        )
        assert result == []

    def test_no_enrollment_data_yields_zero_seats(self, tmp_path):
        # Sequence map has the mapping but no enrollment data exists for feeder term
        empty_master = _master_schedule(tmp_path, [])
        result = run_sequence_forecast(
            self._seq_map(tmp_path), empty_master, "Spring 2026"
        )
        savannah_rows = [r for r in result if r["campus"] == "Savannah"]
        # Target course appears with 0 seats because target_counts seeds it
        assert all(r["projected_seats"] == pytest.approx(0.0) for r in savannah_rows)

    def test_larger_capacity_reduces_section_count(self, tmp_path):
        small_cap = run_sequence_forecast(
            self._seq_map(tmp_path), self._master(tmp_path, enr_fall=100),
            "Spring 2026", capacity=10,
        )
        large_cap = run_sequence_forecast(
            self._seq_map(tmp_path), self._master(tmp_path, enr_fall=100),
            "Spring 2026", capacity=40,
        )
        sav_small = next(r for r in small_cap if r["campus"] == "Savannah" and r["course"] == "FOUN 230")
        sav_large = next(r for r in large_cap if r["campus"] == "Savannah" and r["course"] == "FOUN 230")
        assert sav_small["sections"] >= sav_large["sections"]


# ── run_ratio_forecast ─────────────────────────────────────────────────────────

class TestRunRatioForecast:
    """Target: Summer 2026 (closer feeder = spring, qq=30; target qq=40)."""

    def _historical(self, tmp_path, spring_enr=80, summer_enr=20):
        """FOUN 110 with one year of spring+summer history."""
        rows = [
            {"subj": "FOUN", "crs": "110", "enr": spring_enr, "term": "202230"},  # Spring 2022
            {"subj": "FOUN", "crs": "110", "enr": summer_enr, "term": "202240"},  # Summer 2022
        ]
        return _historical_csv(tmp_path, rows)

    def _feeder(self, tmp_path, seats=100):
        return _feeder_forecast_csv(tmp_path, [
            {"course": "FOUN 110", "campus": "SAV", "seats": seats}
        ])

    def test_returns_list(self, tmp_path):
        result = run_ratio_forecast(
            self._feeder(tmp_path), self._historical(tmp_path), "Summer 2026"
        )
        assert isinstance(result, list)

    def test_includes_row_for_feeder_course(self, tmp_path):
        result = run_ratio_forecast(
            self._feeder(tmp_path), self._historical(tmp_path), "Summer 2026"
        )
        assert any(r["course"] == "FOUN 110" for r in result)

    def test_projected_seats_uses_historical_ratio(self, tmp_path):
        # historical ratio = 20/80 = 0.25; feeder = 100 → projected = 25
        result = run_ratio_forecast(
            self._feeder(tmp_path), self._historical(tmp_path), "Summer 2026"
        )
        row = next(r for r in result if r["course"] == "FOUN 110")
        assert row["projected_seats"] == pytest.approx(25.0, rel=0.01)

    def test_sections_computed_correctly(self, tmp_path):
        result = run_ratio_forecast(
            self._feeder(tmp_path), self._historical(tmp_path),
            "Summer 2026", capacity=20,
        )
        row = next(r for r in result if r["course"] == "FOUN 110")
        assert row["sections"] == math.ceil(row["projected_seats"] / 20)

    def test_method_field_is_ratio_based(self, tmp_path):
        result = run_ratio_forecast(
            self._feeder(tmp_path), self._historical(tmp_path), "Summer 2026"
        )
        row = next(r for r in result if r["course"] == "FOUN 110")
        assert row["method"] == "ratio_based"

    def test_uses_default_ratio_when_no_history(self, tmp_path):
        empty_historical = _historical_csv(tmp_path, [])
        result = run_ratio_forecast(
            self._feeder(tmp_path, seats=100), empty_historical,
            "Summer 2026", default_ratio=0.1,
        )
        # No historical data → falls back to default_ratio=0.1 → 100 * 0.1 = 10 seats
        assert any(r["course"] == "FOUN 110" and r["projected_seats"] == pytest.approx(10.0) for r in result)

    def test_returns_empty_when_feeder_csv_missing(self, tmp_path):
        missing = tmp_path / "nonexistent_forecast.csv"
        result = run_ratio_forecast(
            missing, self._historical(tmp_path), "Summer 2026"
        )
        assert result == []

    def test_returns_empty_when_feeder_csv_has_no_seats_column(self, tmp_path):
        bad_feeder = tmp_path / "bad_feeder.csv"
        _write(bad_feeder, "course,campus\nFOUN 110,SAV\n")
        result = run_ratio_forecast(
            bad_feeder, self._historical(tmp_path), "Summer 2026"
        )
        assert result == []

    def test_buffer_percent_scales_projected_seats(self, tmp_path):
        base = run_ratio_forecast(
            self._feeder(tmp_path), self._historical(tmp_path),
            "Summer 2026", buffer_percent=0.0,
        )
        buffered = run_ratio_forecast(
            self._feeder(tmp_path), self._historical(tmp_path),
            "Summer 2026", buffer_percent=10.0,
        )
        base_seats = next(r["projected_seats"] for r in base if r["course"] == "FOUN 110")
        buf_seats  = next(r["projected_seats"] for r in buffered if r["course"] == "FOUN 110")
        assert buf_seats == pytest.approx(base_seats * 1.1, rel=0.01)

    def test_missing_historical_file_uses_default_ratio(self, tmp_path):
        missing_hist = tmp_path / "no_history.csv"
        result = run_ratio_forecast(
            self._feeder(tmp_path, seats=200), missing_hist,
            "Summer 2026", default_ratio=0.05,
        )
        row = next(r for r in result if r["course"] == "FOUN 110")
        assert row["projected_seats"] == pytest.approx(10.0)  # 200 * 0.05


class TestRunSequenceForecastAdmits:
    def test_admits_path_none_does_not_crash(self):
        """run_sequence_forecast with admits_path=None works as before."""
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
        from pathlib import Path
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
