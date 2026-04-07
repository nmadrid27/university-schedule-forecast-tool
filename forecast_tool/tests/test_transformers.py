"""Tests for forecast_tool.data.transformers.

quarter_to_date: converts (year, quarter) → datetime
date_to_quarter_label: converts datetime → "Quarter YYYY" label
"""

from datetime import datetime

import pytest

from forecast_tool.data.transformers import date_to_quarter_label, quarter_to_date


# ── quarter_to_date ────────────────────────────────────────────────────────────

class TestQuarterToDate:
    def test_fall_returns_september(self):
        assert quarter_to_date(2022, "fall") == datetime(2022, 9, 1)

    def test_spring_returns_april(self):
        assert quarter_to_date(2022, "spring") == datetime(2022, 4, 1)

    def test_summer_returns_june(self):
        assert quarter_to_date(2022, "summer") == datetime(2022, 6, 1)

    def test_winter_keeps_same_year(self):
        dt = quarter_to_date(2025, "winter")
        assert dt.year == 2025

    def test_string_year_accepted(self):
        assert quarter_to_date("2022", "fall") == datetime(2022, 9, 1)

    def test_case_insensitive_fall(self):
        assert quarter_to_date(2022, "FALL") == quarter_to_date(2022, "fall")

    def test_case_insensitive_winter(self):
        assert quarter_to_date(2022, "Winter") == quarter_to_date(2022, "winter")

    def test_numeric_quarter_1_returns_january(self):
        assert quarter_to_date(2022, 1) == datetime(2022, 1, 1)

    def test_numeric_quarter_2_returns_april(self):
        assert quarter_to_date(2022, 2) == datetime(2022, 4, 1)

    def test_numeric_quarter_3_returns_june(self):
        assert quarter_to_date(2022, 3) == datetime(2022, 6, 1)

    def test_numeric_quarter_4_returns_september(self):
        assert quarter_to_date(2022, 4) == datetime(2022, 9, 1)

    def test_returns_first_of_month(self):
        assert quarter_to_date(2022, "spring").day == 1

    def test_returns_datetime_type(self):
        assert isinstance(quarter_to_date(2022, "fall"), datetime)


# ── date_to_quarter_label ──────────────────────────────────────────────────────

class TestDateToQuarterLabel:
    def test_january_is_winter(self):
        assert date_to_quarter_label(datetime(2026, 1, 1)) == "Winter 2026"

    def test_february_is_winter(self):
        assert date_to_quarter_label(datetime(2026, 2, 15)) == "Winter 2026"

    def test_march_is_winter(self):
        assert date_to_quarter_label(datetime(2026, 3, 31)) == "Winter 2026"

    def test_april_is_spring(self):
        assert date_to_quarter_label(datetime(2026, 4, 1)) == "Spring 2026"

    def test_may_is_spring(self):
        assert date_to_quarter_label(datetime(2026, 5, 31)) == "Spring 2026"

    def test_june_is_summer(self):
        assert date_to_quarter_label(datetime(2026, 6, 1)) == "Summer 2026"

    def test_july_is_summer(self):
        assert date_to_quarter_label(datetime(2026, 7, 15)) == "Summer 2026"

    def test_august_is_summer(self):
        assert date_to_quarter_label(datetime(2026, 8, 31)) == "Summer 2026"

    def test_september_is_fall(self):
        assert date_to_quarter_label(datetime(2026, 9, 1)) == "Fall 2026"

    def test_october_is_fall(self):
        assert date_to_quarter_label(datetime(2026, 10, 15)) == "Fall 2026"

    def test_november_is_fall(self):
        assert date_to_quarter_label(datetime(2026, 11, 30)) == "Fall 2026"

    def test_december_is_fall(self):
        assert date_to_quarter_label(datetime(2026, 12, 31)) == "Fall 2026"

    def test_label_includes_year(self):
        label = date_to_quarter_label(datetime(2024, 9, 1))
        assert "2024" in label

    def test_returns_string(self):
        assert isinstance(date_to_quarter_label(datetime(2026, 4, 1)), str)
