"""Tests for resolve_term_info and term_code_to_label pure functions."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forecaster import resolve_term_info, term_code_to_label


# ─── term_code_to_label ───────────────────────────────────────────────────

class TestTermCodeToLabel:
    def test_spring(self):
        assert term_code_to_label("202630") == "Spring 2026"

    def test_winter(self):
        assert term_code_to_label("202620") == "Winter 2026"

    def test_summer(self):
        assert term_code_to_label("202640") == "Summer 2026"

    def test_fall_subtracts_one_from_academic_year(self):
        # Fall 2025 is stored as academic year 2026, code 202610
        assert term_code_to_label("202610") == "Fall 2025"

    def test_returns_raw_code_when_wrong_length(self):
        assert term_code_to_label("2026") == "2026"

    def test_returns_raw_code_for_unknown_quarter_digit(self):
        assert term_code_to_label("202699") == "202699"


# ─── resolve_term_info ────────────────────────────────────────────────────

class TestResolveTermInfoTargetCode:
    def test_spring_target_code(self):
        info = resolve_term_info("Spring 2026")
        assert info["target_term_code"] == "202630"

    def test_winter_target_code(self):
        info = resolve_term_info("Winter 2026")
        assert info["target_term_code"] == "202620"

    def test_summer_target_code(self):
        info = resolve_term_info("Summer 2026")
        assert info["target_term_code"] == "202640"

    def test_fall_target_code_uses_next_academic_year(self):
        # Fall 2025 calendar year → academic year 2026 → code 202610
        info = resolve_term_info("Fall 2025")
        assert info["target_term_code"] == "202610"

    def test_quarter_name_is_lowercase(self):
        info = resolve_term_info("Spring 2026")
        assert info["target_quarter"] == "spring"


class TestResolveTermInfoFeeders:
    def test_spring_closer_feeder_is_winter(self):
        info = resolve_term_info("Spring 2026")
        assert info["closer_feeder"]["quarter"] == "winter"

    def test_spring_farther_feeder_is_fall(self):
        info = resolve_term_info("Spring 2026")
        assert info["farther_feeder"]["quarter"] == "fall"

    def test_fall_closer_feeder_is_summer(self):
        info = resolve_term_info("Fall 2025")
        assert info["closer_feeder"]["quarter"] == "summer"

    def test_fall_farther_feeder_is_spring(self):
        info = resolve_term_info("Fall 2025")
        assert info["farther_feeder"]["quarter"] == "spring"

    def test_closer_feeder_multiplier_exp_is_1(self):
        info = resolve_term_info("Spring 2026")
        assert info["closer_feeder"]["multiplier_exp"] == 1

    def test_farther_feeder_multiplier_exp_is_2(self):
        info = resolve_term_info("Spring 2026")
        assert info["farther_feeder"]["multiplier_exp"] == 2

    def test_spring_2026_closer_feeder_term_code_is_winter_2026(self):
        info = resolve_term_info("Spring 2026")
        # Winter 2026 → academic year 2026, code 202620
        assert info["closer_feeder"]["term_code"] == "202620"

    def test_spring_2026_farther_feeder_term_code_is_fall_2025(self):
        info = resolve_term_info("Spring 2026")
        # Fall 2025 → academic year 2026, code 202610
        assert info["farther_feeder"]["term_code"] == "202610"


class TestResolveTermInfoNumericInput:
    def test_accepts_six_digit_term_code(self):
        info = resolve_term_info("202630")
        assert info["target_quarter"] == "spring"
        assert info["target_term_code"] == "202630"

    def test_numeric_fall_term_code(self):
        info = resolve_term_info("202610")
        assert info["target_quarter"] == "fall"


class TestResolveTermInfoErrors:
    def test_raises_on_unknown_quarter(self):
        with pytest.raises(ValueError, match="Unknown quarter"):
            resolve_term_info("Autumn 2026")

    def test_raises_on_malformed_format(self):
        with pytest.raises(ValueError):
            resolve_term_info("Spring")

    def test_raises_on_invalid_term_code_suffix(self):
        with pytest.raises(ValueError, match="Invalid term code suffix"):
            resolve_term_info("202699")
