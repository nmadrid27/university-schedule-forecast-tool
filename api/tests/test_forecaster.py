"""Tests for compute_sections and distribute_enrollments."""

import math
import pytest
from api.forecaster import compute_sections, distribute_enrollments


# --------------- distribute_enrollments ---------------

def test_applies_multiplier_to_single_source_target():
    enrollments = {"FOUN 110": 100.0}
    mapping = {("FOUN 110", "FOUN 210"): 1.0}

    result = distribute_enrollments(enrollments, mapping, multiplier=0.95)

    assert result["FOUN 210"] == pytest.approx(95.0)


def test_normalizes_weights_across_multiple_targets():
    # FOUN 110 maps to FOUN 210 (weight 2) and FOUN 230 (weight 1)
    # total_weight = 3, so FOUN 210 gets 2/3 and FOUN 230 gets 1/3
    enrollments = {"FOUN 110": 90.0}
    mapping = {
        ("FOUN 110", "FOUN 210"): 2.0,
        ("FOUN 110", "FOUN 230"): 1.0,
    }

    result = distribute_enrollments(enrollments, mapping, multiplier=1.0)

    assert result["FOUN 210"] == pytest.approx(60.0)
    assert result["FOUN 230"] == pytest.approx(30.0)


def test_source_totals_overrides_internal_weight_sum():
    # source_totals says FOUN 110 has total weight 3.0
    # The mapping weight to FOUN 210 is 1.0, so only 1/3 of seats route here
    enrollments = {"FOUN 110": 90.0}
    mapping = {("FOUN 110", "FOUN 210"): 1.0}
    source_totals = {"FOUN 110": 3.0}

    result = distribute_enrollments(enrollments, mapping, multiplier=1.0, source_totals=source_totals)

    assert result["FOUN 210"] == pytest.approx(30.0)


def test_multiple_sources_accumulate_to_same_target():
    enrollments = {"FOUN 110": 60.0, "FOUN 120": 40.0}
    mapping = {
        ("FOUN 110", "FOUN 210"): 1.0,
        ("FOUN 120", "FOUN 210"): 1.0,
    }

    result = distribute_enrollments(enrollments, mapping, multiplier=1.0)

    assert result["FOUN 210"] == pytest.approx(100.0)


def test_skips_source_with_zero_seats():
    enrollments = {"FOUN 110": 0.0, "FOUN 120": 50.0}
    mapping = {
        ("FOUN 110", "FOUN 210"): 1.0,
        ("FOUN 120", "FOUN 210"): 1.0,
    }

    result = distribute_enrollments(enrollments, mapping, multiplier=1.0)

    assert result["FOUN 210"] == pytest.approx(50.0)


def test_unmapped_source_course_contributes_nothing():
    enrollments = {"FOUN 999": 100.0}
    mapping = {("FOUN 110", "FOUN 210"): 1.0}

    result = distribute_enrollments(enrollments, mapping, multiplier=1.0)

    assert "FOUN 210" not in result


def test_source_totals_zero_value_skips_source():
    enrollments = {"FOUN 110": 50.0}
    mapping = {("FOUN 110", "FOUN 210"): 1.0}
    source_totals = {"FOUN 110": 0.0}

    result = distribute_enrollments(enrollments, mapping, multiplier=1.0, source_totals=source_totals)

    assert "FOUN 210" not in result


# --------------- compute_sections ---------------

def test_rounds_up_when_enrollment_exceeds_whole_sections():
    # 35 students, cap 20 → needs 2 sections (not 1, which would seat only 20)
    assert compute_sections(35.0, 20) == 2


def test_exact_division_does_not_add_extra_section():
    # 40 students / 20 cap = exactly 2.0 → 2 sections, not 3
    assert compute_sections(40.0, 20) == 2


def test_zero_seats_returns_zero_sections():
    assert compute_sections(0.0, 20) == 0


def test_negative_seats_returns_zero_sections():
    # Negative values can arise from adjustment math; should never open a section
    assert compute_sections(-5.0, 20) == 0


def test_any_positive_fraction_opens_one_section():
    # Even 0.5 projected seats means some students need this course
    assert compute_sections(0.5, 20) == 1


def test_single_student_within_capacity_needs_one_section():
    assert compute_sections(1.0, 20) == 1


def test_capacity_of_one_yields_section_per_student():
    assert compute_sections(5.0, 1) == 5
