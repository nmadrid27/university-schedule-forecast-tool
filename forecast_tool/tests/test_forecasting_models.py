"""Tests for forecast_tool.forecasting model wrappers.

Each model (ETS, ARIMA, Prophet) exposes a single forecast_* function with:
  - Guard clauses for empty / too-short DataFrames
  - Fallback chain to naive mean
  - Return shape: array or DataFrame of length == periods

Slow model fits (Prophet, large datasets) are kept minimal or skipped;
guard clauses and small-data fallbacks are fast (no actual fitting).
"""

import math
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from forecast_tool.forecasting.arima_forecast import forecast_arima
from forecast_tool.forecasting.ets_forecast import forecast_ets
from forecast_tool.forecasting.prophet_forecast import forecast_prophet


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_ts(n: int, start: str = "2020-01-01") -> pd.DataFrame:
    """Minimal ds/y DataFrame for model input."""
    dates = pd.date_range(start, periods=n, freq="QE")
    return pd.DataFrame({"ds": dates, "y": np.arange(n, dtype=float) * 5 + 80})


# ── forecast_ets ───────────────────────────────────────────────────────────────

class TestForecastEts:
    def test_empty_df_returns_nan_array(self):
        result = forecast_ets(pd.DataFrame(), periods=2)
        assert all(math.isnan(v) for v in result)
        assert len(result) == 2

    def test_one_row_returns_nan_array(self):
        result = forecast_ets(_make_ts(1), periods=1)
        assert all(math.isnan(v) for v in result)

    def test_returns_correct_number_of_periods(self):
        # 3 rows → fallback to naive mean (too short for seasonal HW)
        result = forecast_ets(_make_ts(3), periods=3)
        assert len(result) == 3

    def test_output_is_numeric(self):
        result = forecast_ets(_make_ts(3), periods=2)
        for v in result:
            assert isinstance(float(v), float)

    def test_two_rows_returns_array_not_dataframe(self):
        result = forecast_ets(_make_ts(2), periods=1)
        # should be array-like, not a DataFrame
        assert not isinstance(result, pd.DataFrame)

    def test_minimal_fit_path_returns_correct_length(self):
        # 10 rows triggers the Holt-Winters or simple ETS path
        result = forecast_ets(_make_ts(10), periods=2)
        assert len(result) == 2

    def test_minimal_fit_path_values_are_finite(self):
        result = forecast_ets(_make_ts(10), periods=2)
        for v in result:
            assert math.isfinite(float(v))

    def test_periods_param_respected(self):
        for p in [1, 2, 4]:
            assert len(forecast_ets(_make_ts(3), periods=p)) == p


# ── forecast_arima ─────────────────────────────────────────────────────────────

class TestForecastArima:
    def test_empty_df_returns_nan_array(self):
        result = forecast_arima(pd.DataFrame(), periods=2)
        assert all(math.isnan(v) for v in result)
        assert len(result) == 2

    def test_one_row_returns_nan_array(self):
        # len < 2 → NaN path
        result = forecast_arima(_make_ts(1), periods=1)
        assert all(math.isnan(v) for v in result)

    def test_two_rows_returns_naive_mean(self):
        # len in [2, 3] → mean fallback (not NaN)
        df = _make_ts(2)
        result = forecast_arima(df, periods=1)
        expected_mean = float(df["y"].mean())
        assert float(result[0]) == pytest.approx(expected_mean)

    def test_three_rows_returns_naive_mean(self):
        df = _make_ts(3)
        result = forecast_arima(df, periods=2)
        expected_mean = float(df["y"].mean())
        for v in result:
            assert float(v) == pytest.approx(expected_mean)

    def test_returns_correct_number_of_periods(self):
        result = forecast_arima(_make_ts(2), periods=3)
        assert len(result) == 3

    def test_minimal_fit_path_returns_correct_length(self):
        # 8 rows → tries ARIMA(1,1,1) or falls back
        result = forecast_arima(_make_ts(8), periods=2)
        assert len(result) == 2

    def test_minimal_fit_path_values_are_finite(self):
        result = forecast_arima(_make_ts(8), periods=2)
        for v in result:
            assert math.isfinite(float(v))

    def test_periods_param_respected(self):
        for p in [1, 2, 3]:
            assert len(forecast_arima(_make_ts(2), periods=p)) == p


# ── forecast_prophet ───────────────────────────────────────────────────────────

class TestForecastProphet:
    def test_empty_df_returns_empty_dataframe(self):
        result = forecast_prophet(pd.DataFrame(), periods=2)
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_one_row_returns_empty_dataframe(self):
        result = forecast_prophet(_make_ts(1), periods=1)
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_returns_dataframe(self):
        # Guard-only test: verify return type is always DataFrame
        result = forecast_prophet(pd.DataFrame(), periods=1)
        assert isinstance(result, pd.DataFrame)

    def test_empty_result_has_no_yhat_rows(self):
        result = forecast_prophet(pd.DataFrame(), periods=2)
        assert len(result) == 0

    def _mock_prophet(self, periods: int):
        """Return a mock Prophet instance whose predict() output matches periods."""
        future_dates = pd.date_range("2022-01-01", periods=periods, freq="QS")
        forecast_df = pd.DataFrame({
            "ds": future_dates,
            "yhat": [90.0] * periods,
            "yhat_lower": [85.0] * periods,
            "yhat_upper": [95.0] * periods,
        })
        mock_instance = MagicMock()
        mock_instance.make_future_dataframe.return_value = forecast_df
        mock_instance.predict.return_value = forecast_df
        return mock_instance

    def test_fit_path_returns_dataframe_with_correct_row_count(self):
        with patch("forecast_tool.forecasting.prophet_forecast.Prophet") as MockProphet:
            MockProphet.return_value = self._mock_prophet(2)
            result = forecast_prophet(_make_ts(10), periods=2)
        assert len(result) == 2

    def test_fit_path_has_yhat_column(self):
        with patch("forecast_tool.forecasting.prophet_forecast.Prophet") as MockProphet:
            MockProphet.return_value = self._mock_prophet(1)
            result = forecast_prophet(_make_ts(10), periods=1)
        assert "yhat" in result.columns

    def test_fit_path_has_expected_columns(self):
        with patch("forecast_tool.forecasting.prophet_forecast.Prophet") as MockProphet:
            MockProphet.return_value = self._mock_prophet(1)
            result = forecast_prophet(_make_ts(10), periods=1)
        for col in ["ds", "yhat", "yhat_lower", "yhat_upper"]:
            assert col in result.columns

    def test_fit_path_yhat_values_are_finite(self):
        with patch("forecast_tool.forecasting.prophet_forecast.Prophet") as MockProphet:
            MockProphet.return_value = self._mock_prophet(2)
            result = forecast_prophet(_make_ts(10), periods=2)
        assert result["yhat"].apply(lambda v: math.isfinite(v)).all()
