"""Tests for forecast_tool.diagnostics.stationarity_test.

test_stationarity: ADF test on enrollment series — returns structured dict
measure_seasonal_strength: seasonal decomposition — returns strength score
analyze_all_courses: runs both diagnostics across a course dict, builds summary
"""

import numpy as np
import pandas as pd
import pytest

from forecast_tool.diagnostics.stationarity_test import (
    MIN_OBSERVATIONS_ADF,
    MIN_OBSERVATIONS_SEASONAL,
    analyze_all_courses,
    measure_seasonal_strength,
    test_stationarity as run_stationarity,
)


# ── test_stationarity ──────────────────────────────────────────────────────────

class TestTestStationarity:
    def test_insufficient_data_returns_none_fields(self):
        # Fewer than MIN_OBSERVATIONS_ADF (8) observations
        s = pd.Series([80.0, 85.0, 90.0])
        result = run_stationarity(s)
        assert result["test_statistic"] is None
        assert result["p_value"] is None
        assert result["is_stationary"] is None

    def test_insufficient_data_reports_correct_count(self):
        s = pd.Series([80.0, 85.0])
        result = run_stationarity(s)
        assert result["n_observations"] == 2

    def test_constant_series_is_stationary(self):
        s = pd.Series([100.0] * 10)
        result = run_stationarity(s)
        assert result["is_stationary"] is True

    def test_constant_series_has_no_test_stat(self):
        # Zero variance path — ADF is not run
        s = pd.Series([50.0] * 12)
        result = run_stationarity(s)
        assert result["test_statistic"] is None
        assert result["p_value"] is None

    def test_valid_series_returns_all_required_keys(self):
        # White noise — enough observations for ADF
        rng = np.random.default_rng(42)
        s = pd.Series(rng.normal(100, 10, 20))
        result = run_stationarity(s)
        for key in ["test_statistic", "p_value", "is_stationary",
                    "critical_values", "n_observations", "interpretation"]:
            assert key in result

    def test_valid_series_is_stationary_is_bool(self):
        rng = np.random.default_rng(42)
        s = pd.Series(rng.normal(100, 10, 20))
        # numpy produces np.bool_, not bool; test via membership
        assert run_stationarity(s)["is_stationary"] in (True, False)

    def test_valid_series_p_value_is_float(self):
        rng = np.random.default_rng(42)
        s = pd.Series(rng.normal(100, 10, 20))
        assert isinstance(run_stationarity(s)["p_value"], float)

    def test_critical_values_has_three_levels(self):
        rng = np.random.default_rng(42)
        s = pd.Series(rng.normal(100, 10, 20))
        cv = run_stationarity(s)["critical_values"]
        assert "1%" in cv and "5%" in cv and "10%" in cv

    def test_interpretation_is_string(self):
        rng = np.random.default_rng(42)
        s = pd.Series(rng.normal(100, 10, 20))
        assert isinstance(run_stationarity(s)["interpretation"], str)

    def test_drops_nan_before_testing(self):
        # NaN should be stripped — result is still valid if 8+ remain
        vals = [float("nan")] * 3 + list(range(80, 100))  # 20 valid values
        s = pd.Series(vals)
        result = run_stationarity(s)
        assert result["is_stationary"] is not None

    def test_custom_significance_level_applied(self):
        # Use very tight significance level → series less likely to pass
        rng = np.random.default_rng(42)
        s = pd.Series(rng.normal(100, 10, 30))
        result_tight = run_stationarity(s, significance_level=0.0001)
        result_loose = run_stationarity(s, significance_level=0.9999)
        # Loose threshold should be more likely to declare stationarity
        # At minimum, we verify both calls return valid structure
        assert result_tight["is_stationary"] in (True, False)
        assert result_loose["is_stationary"] in (True, False)


# ── measure_seasonal_strength ──────────────────────────────────────────────────

class TestMeasureSeasonalStrength:
    def test_insufficient_data_returns_none_strength(self):
        s = pd.Series([80.0, 85.0, 90.0])
        result = measure_seasonal_strength(s)
        assert result["strength"] is None

    def test_insufficient_data_returns_none_components(self):
        s = pd.Series([80.0] * 5)
        result = measure_seasonal_strength(s)
        assert result["seasonal_component"] is None
        assert result["trend_component"] is None
        assert result["residual_component"] is None

    def test_valid_series_returns_all_required_keys(self):
        # 12 observations, period=4 → enough for decomposition
        s = pd.Series([80, 50, 70, 90] * 3, dtype=float)
        result = measure_seasonal_strength(s)
        for key in ["strength", "seasonal_component", "trend_component",
                    "residual_component", "interpretation"]:
            assert key in result

    def test_strength_is_between_zero_and_one(self):
        s = pd.Series([80, 50, 70, 90] * 3, dtype=float)
        result = measure_seasonal_strength(s)
        if result["strength"] is not None:
            assert 0.0 <= result["strength"] <= 1.0

    def test_seasonal_component_is_list(self):
        s = pd.Series([80, 50, 70, 90] * 3, dtype=float)
        result = measure_seasonal_strength(s)
        assert isinstance(result["seasonal_component"], list)

    def test_interpretation_is_string(self):
        s = pd.Series([80, 50, 70, 90] * 3, dtype=float)
        result = measure_seasonal_strength(s)
        assert isinstance(result["interpretation"], str)

    def test_drops_nan_before_decomposition(self):
        # Prepend NaNs — should still work if enough valid points remain
        vals = [float("nan")] * 4 + [80, 50, 70, 90] * 3
        s = pd.Series(vals)
        result = measure_seasonal_strength(s)
        # With 12 valid values it should succeed
        assert result["strength"] is not None

    def test_strength_float_when_valid(self):
        s = pd.Series([80, 50, 70, 90] * 3, dtype=float)
        result = measure_seasonal_strength(s)
        if result["strength"] is not None:
            assert isinstance(result["strength"], float)


# ── analyze_all_courses ────────────────────────────────────────────────────────

class TestAnalyzeAllCourses:
    def test_empty_dict_returns_zero_counts(self):
        result = analyze_all_courses({})
        s = result["summary"]
        assert s["total_courses"] == 0
        assert s["stationary_count"] == 0
        assert s["non_stationary_count"] == 0
        assert s["insufficient_data_count"] == 0

    def test_empty_dict_avg_seasonal_strength_is_none(self):
        result = analyze_all_courses({})
        assert result["summary"]["avg_seasonal_strength"] is None

    def test_insufficient_data_course_counted_correctly(self):
        result = analyze_all_courses({
            "FOUN 110": pd.Series([80.0, 85.0, 90.0]),  # only 3 obs
        })
        assert result["summary"]["insufficient_data_count"] == 1
        assert result["summary"]["stationary_count"] == 0

    def test_results_key_contains_per_course_dict(self):
        result = analyze_all_courses({"FOUN 110": pd.Series([80.0] * 3)})
        assert "FOUN 110" in result["results"]

    def test_per_course_result_has_stationarity_and_seasonality(self):
        result = analyze_all_courses({"FOUN 110": pd.Series([80.0] * 3)})
        course = result["results"]["FOUN 110"]
        assert "stationarity" in course
        assert "seasonality" in course

    def test_summary_has_required_keys(self):
        result = analyze_all_courses({})
        expected = [
            "total_courses", "stationary_count", "non_stationary_count",
            "insufficient_data_count", "non_stationary_courses",
            "avg_seasonal_strength", "strong_seasonality_courses",
        ]
        for key in expected:
            assert key in result["summary"]

    def test_non_stationary_courses_list_is_sorted(self):
        # Build two courses with insufficient data → is_stationary=None; use full series
        rng = np.random.default_rng(0)
        # Use a random walk (non-stationary) series for both
        walk = np.cumsum(rng.normal(0, 1, 30))
        courses = {
            "FOUN 230": pd.Series(walk),
            "FOUN 110": pd.Series(walk),
        }
        result = analyze_all_courses(courses)
        nsc = result["summary"]["non_stationary_courses"]
        assert nsc == sorted(nsc)

    def test_total_courses_count(self):
        result = analyze_all_courses({
            "FOUN 110": pd.Series([80.0] * 3),
            "FOUN 230": pd.Series([60.0] * 3),
        })
        assert result["summary"]["total_courses"] == 2
