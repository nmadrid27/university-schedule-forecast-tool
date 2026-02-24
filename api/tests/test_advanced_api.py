"""Tests for /api/data/files, /api/forecast/ensemble, and /api/diagnostics.

Ensemble and diagnostics are tested with mocked data pipeline so the tests
remain fast and deterministic (no actual Prophet/ETS/ARIMA fitting).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402

client = TestClient(main.app)


# ── /api/data/files ───────────────────────────────────────────────────────────

class TestDataFilesEndpoint:
    def test_returns_200(self):
        r = client.get("/api/data/files")
        assert r.status_code == 200

    def test_response_has_files_key(self):
        body = client.get("/api/data/files").json()
        assert "files" in body

    def test_files_list_is_list(self):
        body = client.get("/api/data/files").json()
        assert isinstance(body["files"], list)

    def test_each_file_entry_has_required_keys(self):
        body = client.get("/api/data/files").json()
        for entry in body["files"]:
            assert "name" in entry
            assert "path" in entry
            assert "size" in entry
            assert "modified" in entry

    def test_only_csv_and_xlsx_files_returned(self):
        body = client.get("/api/data/files").json()
        for entry in body["files"]:
            assert entry["name"].endswith(".csv") or entry["name"].endswith(".xlsx")

    def test_returns_empty_files_when_directory_missing(self):
        # Patch Path.exists on the data directory to simulate missing dir
        with patch("pathlib.Path.exists", return_value=False):
            r = client.get("/api/data/files")
        assert r.status_code == 200
        assert r.json()["files"] == []


# ── Shared minimal DataFrame fixture ─────────────────────────────────────────

def _make_hist_df(n_quarters: int = 6) -> pd.DataFrame:
    """Minimal FOUN_Historical-shaped DataFrame with n_quarters of data."""
    quarters = (["fall", "winter", "spring", "summer"] * 4)[:n_quarters]
    years = [2022 + i // 4 for i in range(n_quarters)]
    return pd.DataFrame({
        "course_code": ["FOUN 110"] * n_quarters,
        "year": years,
        "quarter": quarters,
        "enrollment": [80 + i * 5 for i in range(n_quarters)],
    })


# ── /api/forecast/ensemble ───────────────────────────────────────────────────

class TestEnsembleEndpoint:
    """Mock the data pipeline and individual forecast models for speed."""

    @staticmethod
    def _mock_forecast_fn(df, periods):
        """Returns a trivial prediction: last value + 5."""
        import pandas as pd
        last = float(df["y"].iloc[-1]) + 5
        return pd.DataFrame({"ds": [None], "yhat": [last]})

    def _patches(self):
        return [
            patch("forecast_tool.data.loaders.load_historical_data",
                  return_value=_make_hist_df()),
            patch("forecast_tool.data.transformers.quarter_to_date",
                  side_effect=lambda y, q: pd.Timestamp(f"{y}-01-01")),
            patch("forecast_tool.forecasting.prophet_forecast.forecast_prophet",
                  side_effect=self._mock_forecast_fn),
            patch("forecast_tool.forecasting.ets_forecast.forecast_ets",
                  side_effect=self._mock_forecast_fn),
            patch("forecast_tool.forecasting.arima_forecast.forecast_arima",
                  side_effect=self._mock_forecast_fn),
        ]

    def test_returns_200(self):
        with (
            patch("forecast_tool.data.loaders.load_historical_data",
                  return_value=_make_hist_df()),
            patch("forecast_tool.data.transformers.quarter_to_date",
                  side_effect=lambda y, q: pd.Timestamp(f"{y}-01-01")),
            patch("forecast_tool.forecasting.prophet_forecast.forecast_prophet",
                  side_effect=self._mock_forecast_fn),
            patch("forecast_tool.forecasting.ets_forecast.forecast_ets",
                  side_effect=self._mock_forecast_fn),
            patch("forecast_tool.forecasting.arima_forecast.forecast_arima",
                  side_effect=self._mock_forecast_fn),
        ):
            r = client.post("/api/forecast/ensemble", json={})
        assert r.status_code == 200

    def test_response_has_results_and_summary(self):
        with (
            patch("forecast_tool.data.loaders.load_historical_data",
                  return_value=_make_hist_df()),
            patch("forecast_tool.data.transformers.quarter_to_date",
                  side_effect=lambda y, q: pd.Timestamp(f"{y}-01-01")),
            patch("forecast_tool.forecasting.prophet_forecast.forecast_prophet",
                  side_effect=self._mock_forecast_fn),
            patch("forecast_tool.forecasting.ets_forecast.forecast_ets",
                  side_effect=self._mock_forecast_fn),
            patch("forecast_tool.forecasting.arima_forecast.forecast_arima",
                  side_effect=self._mock_forecast_fn),
        ):
            body = client.post("/api/forecast/ensemble", json={}).json()
        assert "results" in body
        assert "summary" in body

    def test_returns_404_when_historical_data_empty(self):
        with patch("forecast_tool.data.loaders.load_historical_data",
                   return_value=pd.DataFrame()):
            r = client.post("/api/forecast/ensemble", json={})
        assert r.status_code == 404

    def test_returns_404_when_no_foun_courses(self):
        df = pd.DataFrame({
            "course_code": ["DRAW 200"],
            "year": [2022],
            "quarter": ["fall"],
            "enrollment": [50],
        })
        with patch("forecast_tool.data.loaders.load_historical_data",
                   return_value=df):
            r = client.post("/api/forecast/ensemble", json={})
        assert r.status_code == 404


# ── /api/diagnostics ─────────────────────────────────────────────────────────

class TestDiagnosticsEndpoint:
    _MOCK_ANALYSIS = {
        "results": {
            "FOUN 110": {
                "stationarity": {"adf_statistic": -3.5, "p_value": 0.01, "is_stationary": True},
                "seasonality": {"seasonal_strength": 0.4},
            }
        },
        "summary": {
            "total_courses": 1,
            "stationary_courses": 1,
            "non_stationary_courses": 0,
        },
    }

    def test_returns_200(self):
        with (
            patch("forecast_tool.data.loaders.load_historical_data",
                  return_value=_make_hist_df()),
            patch("forecast_tool.data.transformers.quarter_to_date",
                  side_effect=lambda y, q: pd.Timestamp(f"{y}-01-01")),
            patch("forecast_tool.diagnostics.stationarity_test.analyze_all_courses",
                  return_value=self._MOCK_ANALYSIS),
        ):
            r = client.get("/api/diagnostics")
        assert r.status_code == 200

    def test_response_has_results_and_summary(self):
        with (
            patch("forecast_tool.data.loaders.load_historical_data",
                  return_value=_make_hist_df()),
            patch("forecast_tool.data.transformers.quarter_to_date",
                  side_effect=lambda y, q: pd.Timestamp(f"{y}-01-01")),
            patch("forecast_tool.diagnostics.stationarity_test.analyze_all_courses",
                  return_value=self._MOCK_ANALYSIS),
        ):
            body = client.get("/api/diagnostics").json()
        assert "results" in body
        assert "summary" in body

    def test_returns_404_when_historical_data_empty(self):
        with patch("forecast_tool.data.loaders.load_historical_data",
                   return_value=pd.DataFrame()):
            r = client.get("/api/diagnostics")
        assert r.status_code == 404

    def test_returns_404_when_insufficient_data(self):
        # Only 2 quarters per course → filtered out by len(agg) >= 4 check
        df = pd.DataFrame({
            "course_code": ["FOUN 110", "FOUN 110"],
            "year": [2022, 2022],
            "quarter": ["fall", "winter"],
            "enrollment": [80, 70],
        })
        with (
            patch("forecast_tool.data.loaders.load_historical_data",
                  return_value=df),
            patch("forecast_tool.data.transformers.quarter_to_date",
                  side_effect=lambda y, q: pd.Timestamp(f"{y}-01-01")),
        ):
            r = client.get("/api/diagnostics")
        assert r.status_code == 404
