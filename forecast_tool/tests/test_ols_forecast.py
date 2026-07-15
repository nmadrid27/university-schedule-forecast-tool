"""Tests for forecast_ols, forecast_next_season, and detect_anomaly.

The x-axis must reflect real calendar spacing: a same-season series with a
missing year ("2020", "2021", "2023") is NOT three adjacent points, and a
requested target year sets the extrapolation distance. Datetime series (the
ensemble path) keep the positional axis.
"""

import pandas as pd
import pytest

from forecast_tool.forecasting.ols_forecast import (
    detect_anomaly,
    forecast_next_season,
    forecast_ols,
)


class TestForecastOlsAxis:
    def test_consecutive_years_prediction_unchanged(self):
        df = pd.DataFrame({"ds": ["2020", "2021", "2022"], "y": [100, 110, 120]})
        out = forecast_ols(df, periods=1)
        assert out.iloc[0]["yhat"] == pytest.approx(130.0)

    def test_year_gap_respected(self):
        # Perfect 10/year trend with 2022 missing: the next year is 2024 -> 140.
        # A positional axis would compress the 3-year span and predict 143.3.
        df = pd.DataFrame({"ds": ["2020", "2021", "2023"], "y": [100, 110, 130]})
        out = forecast_ols(df, periods=1)
        assert out.iloc[0]["yhat"] == pytest.approx(140.0)

    def test_term_code_axis_respects_gap(self):
        # Fall term codes: 202010/202110/202310 are calendar 2019/2020/2022.
        df = pd.DataFrame({"ds": ["202010", "202110", "202310"], "y": [100, 110, 130]})
        out = forecast_ols(df, periods=1)
        assert out.iloc[0]["yhat"] == pytest.approx(140.0)

    def test_datetime_ds_keeps_positional_axis(self):
        df = pd.DataFrame({
            "ds": pd.to_datetime(["2020-01-01", "2021-01-01", "2023-01-01"]),
            "y": [100, 110, 130],
        })
        out = forecast_ols(df, periods=1)
        assert out.iloc[0]["yhat"] == pytest.approx(143.333, abs=0.01)


class TestForecastNextSeason:
    def test_targets_requested_year(self):
        # Spring 2020=100, Spring 2021=110; asking for 2024 must extrapolate
        # 3 more years (-> 140), not one position (-> 120).
        historical = {"202030": 100, "202130": 110}
        result = forecast_next_season(historical, "Spring", next_year=2024)
        assert result["yhat"] == pytest.approx(140.0)
        assert result["next_year"] == 2024


class TestDetectAnomalyLeaveOneOut:
    def test_loo_projects_to_leftout_year(self):
        # Train on Spring 2020/2021 (slope 10), left-out point is Spring 2023:
        # the trend value AT 2023 is 130, so actual 155 deviates 19% (no flag).
        # A positional projection (120) would misreport 29% and flag it.
        historical = {"202030": 100, "202130": 110, "202330": 155}
        result = detect_anomaly(historical, "Spring")
        assert result["trend_yhat"] == pytest.approx(130.0)
        assert result["flagged"] is False
