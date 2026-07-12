"""Tests for load_sequence_mappings and _compute_historical_ratios in forecaster.py.

load_sequence_mappings: two-pass anchor selection; dual-feeder path (closer vs farther);
    CHOICE weight splitting; campus filtering; weight accumulation.

_compute_historical_ratios: TERM-code parsing; per-year ratio averaging; zero-feeder/
    zero-target guard; crosswalk application; non-FOUN exclusion; missing file guard.

_active_curriculum_years: returns correct year labels based on how many years of the
    new FOUN curriculum have elapsed since its Fall 2025 start.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forecaster import (
    _active_curriculum_years,
    _compute_historical_ratios,
    distribute_enrollments,
    load_sequence_mappings,
)


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

    def test_empty_spring_row_still_dilutes_closer_source_totals(self, tmp_path):
        """A row with no Spring target must still inflate closer_source_totals so that
        the program's Winter feeder dilutes the fraction for programs that DO have a
        Spring target.  This prevents 100% routing when most feeder-course students
        are from programs without Spring FOUN continuations.

        Real-world example: Motion Media Design takes FOUN 251 in Winter but has no
        Spring FOUN course.  Without dilution, Photography B.F.A. (FOUN 251 → FOUN 220)
        claims 100% of all FOUN 251 Winter students, severely over-projecting FOUN 220.
        """
        p = _seq_csv(tmp_path, [
            # Photography routes FOUN 251 Winter → FOUN 220 Spring
            "PHOTO,BFA,GENERAL,Second Year,,FOUN 251,FOUN 220,",
            # Motion Media takes FOUN 251 in Winter but no Spring FOUN target
            "MMD,BFA,GENERAL,Second Year,,FOUN 251,,",
        ])
        m = load_sequence_mappings(p, "spring", "winter", "fall")
        # FOUN 220 should still appear in closer_to_target (Photography route active)
        assert m["SAVANNAH"]["closer_to_target"][("FOUN 251", "FOUN 220")] == pytest.approx(1.0)
        # closer_source_totals[FOUN 251] must be 2.0 (Photo contributes 1.0 + MMD 1.0)
        # so the fraction becomes 1/2 = 0.5 rather than 1/1 = 1.0
        assert m["SAVANNAH"]["closer_source_totals"]["FOUN 251"] == pytest.approx(2.0)

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


# ── concurrent (co-requisite) target courses ─────────────────────────────────

class TestConcurrentTargetCourses:
    """Non-CHOICE concurrent targets are co-requisites: the same cohort takes
    ALL of them, so each target must receive the program's full feeder share.
    The source_totals denominator must count each program-row once per source
    course, not once per (source, target) pair — otherwise co-req demand is
    split 1/k and sibling programs sharing the feeder get over-diluted.
    """

    def test_concurrent_targets_each_receive_full_program_share(self, tmp_path):
        # One program: Winter FOUN 112 → Spring co-reqs FOUN 240 AND FOUN 245.
        p = _seq_csv(tmp_path, ["FURN,BFA,GENERAL,First Year,,FOUN 112,FOUN 240; FOUN 245,"])
        m = load_sequence_mappings(p, "spring", "winter", "fall")
        sav = m["SAVANNAH"]
        # The row contributes 1.0 to the denominator (one program-cohort)...
        assert sav["closer_source_totals"]["FOUN 112"] == pytest.approx(1.0)
        # ...so 100 feeder students land in full on BOTH targets.
        result = distribute_enrollments(
            {"FOUN 112": 100.0}, sav["closer_to_target"], 1.0,
            source_totals=sav["closer_source_totals"])
        assert result["FOUN 240"] == pytest.approx(100.0)
        assert result["FOUN 245"] == pytest.approx(100.0)

    def test_concurrent_targets_do_not_dilute_sibling_programs(self, tmp_path):
        # PROG A routes to one target; PROG B routes to two co-reqs.
        # Each program is one cohort: the denominator is 2, not 3.
        p = _seq_csv(tmp_path, [
            "PROG A,BFA,GENERAL,First Year,,FOUN 112,FOUN 113,",
            "PROG B,BFA,GENERAL,First Year,,FOUN 112,FOUN 240; FOUN 245,",
        ])
        m = load_sequence_mappings(p, "spring", "winter", "fall")
        sav = m["SAVANNAH"]
        assert sav["closer_source_totals"]["FOUN 112"] == pytest.approx(2.0)
        result = distribute_enrollments(
            {"FOUN 112": 100.0}, sav["closer_to_target"], 1.0,
            source_totals=sav["closer_source_totals"])
        assert result["FOUN 113"] == pytest.approx(50.0)
        assert result["FOUN 240"] == pytest.approx(50.0)
        assert result["FOUN 245"] == pytest.approx(50.0)

    def test_concurrent_targets_full_share_via_farther_feeder(self, tmp_path):
        # Same co-req semantics on the farther (two-quarters-back) feeder path.
        p = _seq_csv(tmp_path, ["FURN,BFA,GENERAL,First Year,FOUN 112,,FOUN 240; FOUN 245,"])
        m = load_sequence_mappings(p, "spring", "winter", "fall")
        sav = m["SAVANNAH"]
        assert sav["farther_source_totals"]["FOUN 112"] == pytest.approx(1.0)
        result = distribute_enrollments(
            {"FOUN 112": 100.0}, sav["farther_to_target"], 1.0,
            source_totals=sav["farther_source_totals"])
        assert result["FOUN 240"] == pytest.approx(100.0)
        assert result["FOUN 245"] == pytest.approx(100.0)

    def test_choice_targets_still_split_and_dilute_once(self, tmp_path):
        # Regression pin: a CHOICE target cell splits 1/N and the row still
        # contributes exactly 1.0 to the denominator.
        p = _seq_csv(tmp_path, [
            "PROG A,BFA,GENERAL,First Year,,FOUN 112,CHOICE: FOUN 240 or FOUN 245,",
        ])
        m = load_sequence_mappings(p, "spring", "winter", "fall")
        sav = m["SAVANNAH"]
        assert sav["closer_source_totals"]["FOUN 112"] == pytest.approx(1.0)
        result = distribute_enrollments(
            {"FOUN 112": 100.0}, sav["closer_to_target"], 1.0,
            source_totals=sav["closer_source_totals"])
        assert result["FOUN 240"] == pytest.approx(50.0)
        assert result["FOUN 245"] == pytest.approx(50.0)


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


# ── load_sequence_mappings year_filter ───────────────────────────────────────

class TestYearFilter:
    def test_year_filter_excludes_second_year_routes(self, tmp_path):
        """When year_filter=["First Year"], second-year rows must not contribute
        to target_counts or routing tables."""
        p = _seq_csv(tmp_path, [
            "PROG A,BFA,GENERAL,First Year,FOUN 110,,FOUN 220,",
            "PROG B,BFA,GENERAL,Second Year,,FOUN 251,FOUN 220,",
        ])
        m = load_sequence_mappings(p, "spring", "winter", "fall",
                                   year_filter=["First Year"])
        # First-year farther route must be present
        assert m["SAVANNAH"]["farther_to_target"][("FOUN 110", "FOUN 220")] == pytest.approx(1.0)
        # Second-year closer route must be absent
        assert ("FOUN 251", "FOUN 220") not in m["SAVANNAH"]["closer_to_target"]

    def test_year_filter_none_includes_all_years(self, tmp_path):
        """year_filter=None (default) must include all rows regardless of year."""
        p = _seq_csv(tmp_path, [
            "PROG A,BFA,GENERAL,First Year,FOUN 110,,FOUN 220,",
            "PROG B,BFA,GENERAL,Second Year,,FOUN 251,FOUN 220,",
        ])
        m = load_sequence_mappings(p, "spring", "winter", "fall", year_filter=None)
        assert ("FOUN 110", "FOUN 220") in m["SAVANNAH"]["farther_to_target"]
        assert ("FOUN 251", "FOUN 220") in m["SAVANNAH"]["closer_to_target"]

    def test_year_filter_source_totals_exclude_filtered_rows(self, tmp_path):
        """closer_source_totals must only count rows that pass the year filter."""
        p = _seq_csv(tmp_path, [
            # First Year: FOUN 112 Winter → FOUN 220 Spring
            "PROG A,BFA,GENERAL,First Year,,FOUN 112,FOUN 220,",
            # Second Year: FOUN 112 Winter, no Spring target (should dilute without filter)
            "PROG B,BFA,GENERAL,Second Year,,FOUN 112,,",
        ])
        # Without filter: PROG B contributes 1.0 to closer_source_totals → total=2.0
        m_all = load_sequence_mappings(p, "spring", "winter", "fall", year_filter=None)
        assert m_all["SAVANNAH"]["closer_source_totals"]["FOUN 112"] == pytest.approx(2.0)

        # With First Year filter: only PROG A counted → total=1.0
        m_filtered = load_sequence_mappings(p, "spring", "winter", "fall",
                                            year_filter=["First Year"])
        assert m_filtered["SAVANNAH"]["closer_source_totals"]["FOUN 112"] == pytest.approx(1.0)


# ── _active_curriculum_years ─────────────────────────────────────────────────

class TestActiveCurriculumYears:
    """The FOUN curriculum was rolled out simultaneously across all four cohort
    years in Fall 2025, not phased in cohort-by-cohort.  PZSMSCP Spring 2026
    actuals show Second/Third Year FOUN courses (250/251/260/330/331/360) carrying
    real ACT enrollment, which is mathematically incompatible with a phased-launch
    model where the curriculum is only one term old.

    Therefore _active_curriculum_years should return all four labels (or None,
    which has identical effect on load_sequence_mappings) for any term at or
    after the curriculum launch, and None (filter disabled) for pre-launch
    terms so historical backtests can use unfiltered seq-map rows.
    """

    def test_spring_2026_returns_all_four_years(self):
        """Spring 2026 (post-launch) must return all four cohort labels so
        Second/Third Year seq-map routes contribute to the forecast."""
        assert _active_curriculum_years("202630") == [
            "First Year", "Second Year", "Third Year", "Fourth Year"
        ]

    def test_fall_2026_returns_all_four_years(self):
        assert _active_curriculum_years("202710") == [
            "First Year", "Second Year", "Third Year", "Fourth Year"
        ]

    def test_winter_2027_returns_all_four_years(self):
        assert _active_curriculum_years("202720") == [
            "First Year", "Second Year", "Third Year", "Fourth Year"
        ]

    def test_fall_2025_is_first_post_launch_term(self):
        """Fall 2025 = 202610 is the first term of the simultaneous rollout."""
        assert _active_curriculum_years("202610") == [
            "First Year", "Second Year", "Third Year", "Fourth Year"
        ]

    def test_pre_curriculum_terms_return_none(self):
        """Terms before the FOUN curriculum (pre Fall 2025 = 202610) must return
        None so historical backtests pass all seq-map rows through (filter
        disabled, not an empty list that filters everything)."""
        assert _active_curriculum_years("202510") is None   # Fall 2024
        assert _active_curriculum_years("202530") is None   # Spring 2025
        assert _active_curriculum_years("202410") is None   # Fall 2023
        assert _active_curriculum_years("202010") is None   # well before launch

    def test_far_future_terms_return_all_four_years(self):
        """No reason to drop the filter post-2028: the curriculum still has
        exactly four cohorts.  Returning all four labels is explicit and
        equivalent to None for the seq map (no rows have non-cohort year
        labels), so prefer the explicit list."""
        assert _active_curriculum_years("202910") == [
            "First Year", "Second Year", "Third Year", "Fourth Year"
        ]
        assert _active_curriculum_years("203010") == [
            "First Year", "Second Year", "Third Year", "Fourth Year"
        ]


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
