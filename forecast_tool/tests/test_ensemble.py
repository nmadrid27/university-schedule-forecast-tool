"""Tests for forecast_tool.forecasting.ensemble.

Pure functions tested:
  - calculate_sections: enrollment → section count with buffer
  - ensemble_forecast: backward-compatible 2/3-model weighted blend
  - ensemble_forecast_weighted: preferred dict-based interface with NaN handling
  - DEFAULT_WEIGHTS: verify expected values
"""

import math

import numpy as np
import pytest

from forecast_tool.forecasting.ensemble import (
    DEFAULT_WEIGHTS,
    calculate_sections,
    ensemble_forecast,
    ensemble_forecast_weighted,
)


# ── DEFAULT_WEIGHTS ────────────────────────────────────────────────────────────

class TestDefaultWeights:
    def test_prophet_weight(self):
        assert DEFAULT_WEIGHTS["prophet"] == pytest.approx(0.40)

    def test_ets_weight(self):
        assert DEFAULT_WEIGHTS["ets"] == pytest.approx(0.35)

    def test_arima_weight(self):
        assert DEFAULT_WEIGHTS["arima"] == pytest.approx(0.25)

    def test_weights_sum_to_one(self):
        assert sum(DEFAULT_WEIGHTS.values()) == pytest.approx(1.0)


# ── calculate_sections ─────────────────────────────────────────────────────────

class TestCalculateSections:
    def test_exact_multiple_no_buffer(self):
        # 100 / 20 = exactly 5
        assert calculate_sections(100, 20, 0.0) == 5

    def test_fractional_rounds_up_no_buffer(self):
        # 101 / 20 → ceil = 6
        assert calculate_sections(101, 20, 0.0) == 6

    def test_buffer_reduces_effective_capacity(self):
        # effective = 20 * (1 - 0.10) = 18; ceil(100/18) = 6
        assert calculate_sections(100, 20, 10.0) == 6

    def test_zero_enrollment_returns_zero_sections(self):
        assert calculate_sections(0, 20, 0.0) == 0

    def test_negative_enrollment_returns_zero(self):
        assert calculate_sections(-10, 20, 0.0) == 0

    def test_zero_capacity_returns_zero(self):
        assert calculate_sections(100, 0, 0.0) == 0

    def test_negative_capacity_returns_zero(self):
        assert calculate_sections(100, -5, 0.0) == 0

    def test_buffer_100_percent_returns_zero(self):
        # effective_capacity = 20 * (1 - 1.0) = 0 → invalid
        assert calculate_sections(100, 20, 100.0) == 0

    def test_returns_integer(self):
        assert isinstance(calculate_sections(90, 20, 5.0), int)

    def test_larger_capacity_fewer_sections(self):
        small = calculate_sections(100, 10, 0.0)
        large = calculate_sections(100, 25, 0.0)
        assert small > large

    def test_higher_buffer_more_sections(self):
        no_buf = calculate_sections(100, 20, 0.0)
        buffered = calculate_sections(100, 20, 20.0)
        assert buffered >= no_buf


# ── ensemble_forecast_weighted ────────────────────────────────────────────────

class TestEnsembleForecastWeighted:
    def test_all_valid_with_default_weights(self):
        # 100*0.40 + 80*0.35 + 60*0.25 = 40 + 28 + 15 = 83
        result = ensemble_forecast_weighted(
            {"prophet": 100.0, "ets": 80.0, "arima": 60.0}
        )
        assert result == pytest.approx(83.0)

    def test_all_nan_returns_nan(self):
        result = ensemble_forecast_weighted(
            {"prophet": float("nan"), "ets": float("nan"), "arima": float("nan")}
        )
        assert math.isnan(result)

    def test_one_nan_redistributes_weight(self):
        # ARIMA NaN → prophet/ets weights renormalized: 0.40/(0.40+0.35) and 0.35/(0.40+0.35)
        result = ensemble_forecast_weighted(
            {"prophet": 100.0, "ets": 80.0, "arima": float("nan")}
        )
        expected = 100.0 * (0.40 / 0.75) + 80.0 * (0.35 / 0.75)
        assert result == pytest.approx(expected, rel=1e-6)

    def test_only_one_valid_returns_that_value(self):
        result = ensemble_forecast_weighted(
            {"prophet": 50.0, "ets": float("nan"), "arima": float("nan")}
        )
        assert result == pytest.approx(50.0)

    def test_uses_default_weights_when_none_passed(self):
        a = ensemble_forecast_weighted({"prophet": 100.0, "ets": 80.0, "arima": 60.0})
        b = ensemble_forecast_weighted(
            {"prophet": 100.0, "ets": 80.0, "arima": 60.0},
            weights=DEFAULT_WEIGHTS,
        )
        assert a == pytest.approx(b)

    def test_custom_weights_applied(self):
        # Equal weights → simple average of 100 and 80
        result = ensemble_forecast_weighted(
            {"prophet": 100.0, "ets": 80.0},
            weights={"prophet": 0.5, "ets": 0.5},
        )
        assert result == pytest.approx(90.0)

    def test_two_model_dict(self):
        result = ensemble_forecast_weighted(
            {"prophet": 120.0, "ets": 100.0},
            weights={"prophet": 0.6, "ets": 0.4},
        )
        # 120*0.6 + 100*0.4 = 72 + 40 = 112
        assert result == pytest.approx(112.0)

    def test_returns_float(self):
        assert isinstance(ensemble_forecast_weighted({"prophet": 90.0, "ets": 80.0}), float)


# ── ensemble_forecast (backward-compatible) ───────────────────────────────────

class TestEnsembleForecast:
    def test_two_model_blend(self):
        # 100*0.6 + 80*0.4 = 60 + 32 = 92
        result = ensemble_forecast(100.0, 80.0, weight_prophet=0.6)
        assert result == pytest.approx(92.0)

    def test_default_weight_two_model(self):
        # Default weight_prophet=0.6 when not specified → backward compatible
        result = ensemble_forecast(100.0, 80.0)
        assert result == pytest.approx(100.0 * 0.6 + 80.0 * 0.4)

    def test_three_model_uses_default_weights(self):
        # 100*0.40 + 80*0.35 + 60*0.25 = 83
        result = ensemble_forecast(100.0, 80.0, arima_pred=60.0)
        assert result == pytest.approx(83.0)

    def test_three_model_custom_weights(self):
        result = ensemble_forecast(100.0, 80.0, weight_prophet=0.5, arima_pred=60.0, weight_arima=0.2)
        # ets_weight = 1 - 0.5 - 0.2 = 0.3
        # 100*0.5 + 80*0.3 + 60*0.2 = 50 + 24 + 12 = 86
        assert result == pytest.approx(86.0)

    def test_nan_prophet_excluded(self):
        # Prophet NaN → weight redistributed to ETS and ARIMA
        result = ensemble_forecast(float("nan"), 80.0, arima_pred=60.0)
        expected = 80.0 * (0.35 / 0.60) + 60.0 * (0.25 / 0.60)
        assert result == pytest.approx(expected, rel=1e-6)

    def test_all_nan_returns_nan(self):
        result = ensemble_forecast(float("nan"), float("nan"), arima_pred=float("nan"))
        assert math.isnan(result)

    def test_returns_float(self):
        assert isinstance(ensemble_forecast(100.0, 80.0), float)
