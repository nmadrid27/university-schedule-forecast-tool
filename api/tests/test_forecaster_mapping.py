"""Tests for load_sequence_mappings and _compute_historical_ratios in forecaster.py.

load_sequence_mappings: two-pass anchor selection; dual-feeder path (closer vs farther);
    CHOICE weight splitting; campus filtering; weight accumulation.

_compute_historical_ratios: TERM-code parsing; per-year ratio averaging; zero-feeder/
    zero-target guard; crosswalk application; non-FOUN exclusion; missing file guard.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forecaster import _compute_historical_ratios, load_sequence_mappings


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _seq_csv(tmp_path: Path, rows: list[str]) -> Path:
    """Minimal sequence-map CSV with standard header + given data rows."""
    p = tmp_path / "seq_map.csv"
    _write(p, "program,degree,campus,year,fall,winter,spring,summer\n"
              + "\n".join(rows) + "\n")
    return p


def _hist_csv(tmp_path: Path, rows: list[str]) -> Path:
    """Minimal FOUN_Historical CSV: SUBJ / CRS NUMBER / ACT ENR / TERM."""
    p = tmp_path / "hist.csv"
    _write(p, "SUBJ,CRS NUMBER,ACT ENR,TERM\n" + "\n".join(rows) + "\n")
    return p


# ── load_sequence_mappings ────────────────────────────────────────────────────

class TestLoadSequenceMappings:
    def test_farther_feeder_populates_farther_to_target(self, tmp_path):
        # winter empty → no closer feeder → fall should land in farther_to_target
        p = _seq_csv(tmp_path, ["TEST,BFA,GENERAL,First Year,FOUN 110,,FOUN 230,"])
        m = load_sequence_mappings(p, "spring", "winter", "fall")
        assert m["SAVANNAH"]["farther_to_target"][("FOUN 110", "FOUN 230")] == pytest.approx(1.0)

    def test_general_campus_applies_to_both_campuses(self, tmp_path):
        p = _seq_csv(tmp_path, ["TEST,BFA,GENERAL,First Year,FOUN 110,,FOUN 230,"])
        m = load_sequence_mappings(p, "spring", "winter", "fall")
        assert m["SCADNOW"]["farther_to_target"][("FOUN 110", "FOUN 230")] == pytest.approx(1.0)

    def test_savannah_only_row_excluded_from_scadnow(self, tmp_path):
        p = _seq_csv(tmp_path, ["TEST,BFA,SAVANNAH,First Year,FOUN 110,,FOUN 230,"])
        m = load_sequence_mappings(p, "spring", "winter", "fall")
        assert ("FOUN 110", "FOUN 230") not in m["SCADNOW"]["farther_to_target"]

    def test_closer_feeder_populated_in_closer_to_target(self, tmp_path):
        # winter=FOUN 110 is the closer feeder
        p = _seq_csv(tmp_path, ["TEST,BFA,GENERAL,First Year,,FOUN 110,FOUN 230,"])
        m = load_sequence_mappings(p, "spring", "winter", "fall")
        assert m["SAVANNAH"]["closer_to_target"][("FOUN 110", "FOUN 230")] == pytest.approx(1.0)

    def test_closer_feeder_suppresses_farther_feeder_path(self, tmp_path):
        # Row has both fall (farther) and winter (closer) — farther must NOT appear
        # in farther_to_target because the same cohort is captured via the closer path.
        p = _seq_csv(tmp_path, ["TEST,BFA,GENERAL,First Year,FOUN 110,FOUN 110,FOUN 230,"])
        m = load_sequence_mappings(p, "spring", "winter", "fall")
        assert ("FOUN 110", "FOUN 230") not in m["SAVANNAH"]["farther_to_target"]

    def test_choice_courses_split_weight_evenly(self, tmp_path):
        p = _seq_csv(tmp_path, ["TEST,BFA,GENERAL,First Year,CHOICE: FOUN 110 or FOUN 120,,FOUN 230,"])
        m = load_sequence_mappings(p, "spring", "winter", "fall")
        w1 = m["SAVANNAH"]["farther_to_target"][("FOUN 110", "FOUN 230")]
        w2 = m["SAVANNAH"]["farther_to_target"][("FOUN 120", "FOUN 230")]
        assert w1 == pytest.approx(0.5)
        assert w2 == pytest.approx(0.5)

    def test_target_counts_incremented_per_row(self, tmp_path):
        p = _seq_csv(tmp_path, ["TEST,BFA,GENERAL,First Year,FOUN 110,,FOUN 230,"])
        m = load_sequence_mappings(p, "spring", "winter", "fall")
        assert m["SAVANNAH"]["target_counts"]["FOUN 230"] == pytest.approx(1.0)

    def test_row_without_target_course_skipped(self, tmp_path):
        # spring column empty → parse_quarter_courses returns [] → row skipped
        p = _seq_csv(tmp_path, ["TEST,BFA,GENERAL,First Year,FOUN 110,,,"])
        m = load_sequence_mappings(p, "spring", "winter", "fall")
        assert len(m["SAVANNAH"]["farther_to_target"]) == 0

    def test_multiple_rows_accumulate_weights(self, tmp_path):
        # Two programs both routing FOUN 110 (fall) → FOUN 230 (spring)
        p = _seq_csv(tmp_path, [
            "PROG A,BFA,GENERAL,First Year,FOUN 110,,FOUN 230,",
            "PROG B,BFA,GENERAL,First Year,FOUN 110,,FOUN 230,",
        ])
        m = load_sequence_mappings(p, "spring", "winter", "fall")
        assert m["SAVANNAH"]["farther_to_target"][("FOUN 110", "FOUN 230")] == pytest.approx(2.0)

    def test_anchor_selection_drops_less_frequent_concurrent_course(self, tmp_path):
        # Three rows: FOUN 110 appears in fall in all three; FOUN 120 in only one.
        # _select_anchor_courses picks FOUN 110 (most frequent) and drops FOUN 120.
        p = _seq_csv(tmp_path, [
            "PROG A,BFA,GENERAL,First Year,FOUN 110 FOUN 120,,FOUN 230,",
            "PROG B,BFA,GENERAL,First Year,FOUN 110,,FOUN 230,",
            "PROG C,BFA,GENERAL,First Year,FOUN 110,,FOUN 231,",
        ])
        m = load_sequence_mappings(p, "spring", "winter", "fall")
        sav = m["SAVANNAH"]["farther_to_target"]
        has_110 = any(src == "FOUN 110" for src, _ in sav)
        has_120 = any(src == "FOUN 120" for src, _ in sav)
        assert has_110
        assert not has_120


# ── _compute_historical_ratios ────────────────────────────────────────────────

class TestComputeHistoricalRatios:
    def test_basic_ratio(self, tmp_path):
        # Spring feeder=80, Summer target=20 → ratio = 0.25
        p = _hist_csv(tmp_path, ["FOUN,110,80,202230", "FOUN,110,20,202240"])
        result = _compute_historical_ratios(p, target_quarter_code="40",
                                               feeder_quarter_code="30")
        assert result["FOUN 110"] == pytest.approx(0.25)

    def test_multi_year_average(self, tmp_path):
        # 2022: 20/100 = 0.20; 2023: 40/80 = 0.50 → avg = 0.35
        p = _hist_csv(tmp_path, [
            "FOUN,110,100,202230", "FOUN,110,20,202240",
            "FOUN,110,80,202330",  "FOUN,110,40,202340",
        ])
        result = _compute_historical_ratios(p, "40", "30")
        assert result["FOUN 110"] == pytest.approx(0.35)

    def test_year_with_zero_feeder_excluded(self, tmp_path):
        # 2022 feeder=0 → excluded; 2023 ratio = 25/100 = 0.25
        p = _hist_csv(tmp_path, [
            "FOUN,110,0,202230",  "FOUN,110,20,202240",
            "FOUN,110,100,202330", "FOUN,110,25,202340",
        ])
        result = _compute_historical_ratios(p, "40", "30")
        assert result["FOUN 110"] == pytest.approx(0.25)

    def test_year_with_zero_target_excluded(self, tmp_path):
        # 2022 target=0 → excluded; 2023 ratio = 25/100 = 0.25
        p = _hist_csv(tmp_path, [
            "FOUN,110,80,202230",  "FOUN,110,0,202240",
            "FOUN,110,100,202330", "FOUN,110,25,202340",
        ])
        result = _compute_historical_ratios(p, "40", "30")
        assert result["FOUN 110"] == pytest.approx(0.25)

    def test_non_foun_course_excluded(self, tmp_path):
        p = _hist_csv(tmp_path, ["DRAW,200,80,202230", "DRAW,200,20,202240"])
        result = _compute_historical_ratios(p, "40", "30")
        assert "DRAW 200" not in result

    def test_crosswalk_maps_legacy_to_foun(self, tmp_path):
        hist = _hist_csv(tmp_path, ["DRAW,200,80,202230", "DRAW,200,20,202240"])
        xwalk = tmp_path / "crosswalk.csv"
        _write(xwalk, "legacy_code,foun_code\nDRAW 200,FOUN 230\n")
        result = _compute_historical_ratios(hist, "40", "30", crosswalk_path=xwalk)
        assert "FOUN 230" in result
        assert result["FOUN 230"] == pytest.approx(0.25)

    def test_missing_file_returns_empty_dict(self, tmp_path):
        assert _compute_historical_ratios(tmp_path / "nope.csv", "40", "30") == {}

    def test_multiple_courses_computed_independently(self, tmp_path):
        p = _hist_csv(tmp_path, [
            "FOUN,110,100,202230", "FOUN,110,20,202240",  # ratio 0.20
            "FOUN,230,50,202230",  "FOUN,230,10,202240",  # ratio 0.20
        ])
        result = _compute_historical_ratios(p, "40", "30")
        assert "FOUN 110" in result
        assert "FOUN 230" in result
        assert result["FOUN 110"] == pytest.approx(0.20)
        assert result["FOUN 230"] == pytest.approx(0.20)

    def test_course_with_no_valid_years_excluded(self, tmp_path):
        # Only a feeder row, no target row → no valid year pair → no ratio
        p = _hist_csv(tmp_path, ["FOUN,110,80,202230"])  # no summer row
        result = _compute_historical_ratios(p, "40", "30")
        assert "FOUN 110" not in result
