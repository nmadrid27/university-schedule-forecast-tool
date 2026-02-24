"""Tests for forecast_tool.validation.temporal_cv.

Pure helper functions:
  _compute_mape, _compute_rmse, _compute_mae — metric calculations
  expanding_window_splits — train/test index generation
  _extract_predictions — normalizes Prophet/ETS/ARIMA return formats

Orchestration:
  CVResult.to_dict — serialization
  temporal_cross_validate — expanding-window CV with a mock forecast callable
  cross_validate_course — convenience wrapper over historical DataFrame
"""

import math

import numpy as np
import pandas as pd
import pytest

from forecast_tool.validation.temporal_cv import (
    CVResult,
    FoldResult,
    _compute_mae,
    _compute_mape,
    _compute_rmse,
    _extract_predictions,
    cross_validate_course,
    expanding_window_splits,
    temporal_cross_validate,
)


# ── _compute_mape ──────────────────────────────────────────────────────────────

class TestComputeMape:
    def test_perfect_prediction_is_zero(self):
        a = np.array([100.0, 80.0, 60.0])
        assert _compute_mape(a, a) == pytest.approx(0.0)

    def test_known_error(self):
        # actuals=[100], preds=[110] → |10/100|*100 = 10%
        assert _compute_mape(np.array([100.0]), np.array([110.0])) == pytest.approx(10.0)

    def test_all_zeros_returns_none(self):
        a = np.array([0.0, 0.0, 0.0])
        assert _compute_mape(a, np.array([10.0, 10.0, 10.0])) is None

    def test_skips_zero_actuals(self):
        # actuals=[0, 100], preds=[5, 110] → only second pair used → 10%
        a = np.array([0.0, 100.0])
        p = np.array([5.0, 110.0])
        assert _compute_mape(a, p) == pytest.approx(10.0)

    def test_returns_float(self):
        assert isinstance(_compute_mape(np.array([100.0]), np.array([90.0])), float)


# ── _compute_rmse ──────────────────────────────────────────────────────────────

class TestComputeRmse:
    def test_perfect_prediction_is_zero(self):
        a = np.array([50.0, 60.0, 70.0])
        assert _compute_rmse(a, a) == pytest.approx(0.0)

    def test_known_error(self):
        # errors=[10, 10] → rmse = sqrt((100+100)/2) = 10
        a = np.array([100.0, 100.0])
        p = np.array([90.0, 110.0])
        assert _compute_rmse(a, p) == pytest.approx(10.0)

    def test_returns_float(self):
        assert isinstance(_compute_rmse(np.array([80.0]), np.array([70.0])), float)


# ── _compute_mae ───────────────────────────────────────────────────────────────

class TestComputeMae:
    def test_perfect_prediction_is_zero(self):
        a = np.array([50.0, 60.0])
        assert _compute_mae(a, a) == pytest.approx(0.0)

    def test_known_error(self):
        # errors=[10, 20] → mae = 15
        a = np.array([100.0, 100.0])
        p = np.array([90.0, 80.0])
        assert _compute_mae(a, p) == pytest.approx(15.0)

    def test_returns_float(self):
        assert isinstance(_compute_mae(np.array([80.0]), np.array([70.0])), float)


# ── expanding_window_splits ───────────────────────────────────────────────────

class TestExpandingWindowSplits:
    def test_basic_case_returns_correct_count(self):
        # n=10, min_train=8, horizon=1, step=1 → 2 splits (at start=8 and start=9)
        splits = expanding_window_splits(10, min_train_size=8, horizon=1, step=1)
        assert len(splits) == 2

    def test_not_enough_data_returns_empty(self):
        # n=5, min_train=8 → no valid splits
        assert expanding_window_splits(5, min_train_size=8) == []

    def test_train_indices_start_at_zero(self):
        splits = expanding_window_splits(10, min_train_size=8, horizon=1)
        train_idx, _ = splits[0]
        assert train_idx[0] == 0

    def test_train_indices_grow_across_folds(self):
        splits = expanding_window_splits(12, min_train_size=8, horizon=1, step=1)
        sizes = [len(t) for t, _ in splits]
        assert sizes == sorted(sizes)

    def test_test_indices_immediately_follow_train(self):
        splits = expanding_window_splits(10, min_train_size=8, horizon=1)
        train_idx, test_idx = splits[0]
        assert test_idx[0] == train_idx[-1] + 1

    def test_horizon_controls_test_window_size(self):
        splits = expanding_window_splits(12, min_train_size=8, horizon=2)
        for _, test_idx in splits:
            assert len(test_idx) == 2

    def test_step_controls_fold_count(self):
        step1 = expanding_window_splits(14, min_train_size=8, horizon=1, step=1)
        step2 = expanding_window_splits(14, min_train_size=8, horizon=1, step=2)
        assert len(step1) > len(step2)

    def test_no_overlap_between_train_and_test(self):
        splits = expanding_window_splits(12, min_train_size=8, horizon=1)
        for train_idx, test_idx in splits:
            assert len(set(train_idx) & set(test_idx)) == 0


# ── _extract_predictions ──────────────────────────────────────────────────────

class TestExtractPredictions:
    def test_prophet_dataframe_with_yhat(self):
        df = pd.DataFrame({"yhat": [100.0, 90.0, 80.0]})
        result = _extract_predictions(df, horizon=2)
        np.testing.assert_array_almost_equal(result, [100.0, 90.0])

    def test_empty_dataframe_returns_all_nan(self):
        result = _extract_predictions(pd.DataFrame(), horizon=2)
        assert all(math.isnan(v) for v in result)
        assert len(result) == 2

    def test_dataframe_without_yhat_uses_first_numeric(self):
        df = pd.DataFrame({"forecast": [95.0, 85.0]})
        result = _extract_predictions(df, horizon=1)
        assert result[0] == pytest.approx(95.0)

    def test_ndarray_input(self):
        arr = np.array([120.0, 110.0, 100.0])
        result = _extract_predictions(arr, horizon=2)
        np.testing.assert_array_almost_equal(result, [120.0, 110.0])

    def test_list_input(self):
        result = _extract_predictions([80.0, 70.0], horizon=1)
        assert result[0] == pytest.approx(80.0)

    def test_series_input(self):
        s = pd.Series([55.0, 65.0])
        result = _extract_predictions(s, horizon=2)
        np.testing.assert_array_almost_equal(result, [55.0, 65.0])

    def test_horizon_clips_output(self):
        # Input has 5 values but horizon=2
        result = _extract_predictions(np.array([1.0, 2.0, 3.0, 4.0, 5.0]), horizon=2)
        assert len(result) == 2


# ── CVResult.to_dict ──────────────────────────────────────────────────────────

class TestCVResultToDict:
    def _make_result(self):
        fold = FoldResult(
            fold=1, train_size=8, test_size=1,
            mape=5.0, rmse=3.0, mae=2.5,
            actuals=np.array([100.0]),
            predictions=np.array([95.0]),
        )
        return CVResult(
            n_folds=1,
            mean_mape=5.0, std_mape=0.0,
            mean_rmse=3.0, std_rmse=0.0,
            mean_mae=2.5, std_mae=0.0,
            folds=[fold],
        )

    def test_returns_dict(self):
        assert isinstance(self._make_result().to_dict(), dict)

    def test_has_aggregate_keys(self):
        d = self._make_result().to_dict()
        for k in ["n_folds", "mean_mape", "std_mape", "mean_rmse",
                  "std_rmse", "mean_mae", "std_mae"]:
            assert k in d

    def test_has_per_fold_list(self):
        d = self._make_result().to_dict()
        assert "per_fold" in d
        assert isinstance(d["per_fold"], list)
        assert len(d["per_fold"]) == 1

    def test_per_fold_has_required_keys(self):
        fold_d = self._make_result().to_dict()["per_fold"][0]
        for k in ["fold", "train_size", "test_size", "mape", "rmse", "mae"]:
            assert k in fold_d

    def test_n_folds_matches(self):
        assert self._make_result().to_dict()["n_folds"] == 1


# ── temporal_cross_validate ───────────────────────────────────────────────────

def _make_ts(n: int) -> pd.DataFrame:
    """Minimal ds/y DataFrame with n chronological observations."""
    dates = pd.date_range("2020-01-01", periods=n, freq="QE")
    return pd.DataFrame({"ds": dates, "y": np.arange(n, dtype=float) * 10 + 80})


def _perfect_forecast(df: pd.DataFrame, periods: int) -> np.ndarray:
    """Returns the last training value as prediction (naive forecast)."""
    last = float(df["y"].iloc[-1])
    return np.array([last] * periods)


def _nan_forecast(df: pd.DataFrame, periods: int) -> np.ndarray:
    return np.full(periods, np.nan)


class TestTemporalCrossValidate:
    def test_raises_when_too_few_observations(self):
        df = _make_ts(5)
        with pytest.raises(ValueError, match="Insufficient data"):
            temporal_cross_validate(df, _perfect_forecast, min_train_size=8, horizon=1)

    def test_returns_cvresult(self):
        df = _make_ts(12)
        result = temporal_cross_validate(df, _perfect_forecast, min_train_size=8, horizon=1)
        assert isinstance(result, CVResult)

    def test_n_folds_correct(self):
        # n=12, min_train=8, horizon=1, step=1 → 4 valid folds
        df = _make_ts(12)
        result = temporal_cross_validate(df, _perfect_forecast, min_train_size=8, horizon=1)
        assert result.n_folds == 4

    def test_mean_rmse_is_float(self):
        df = _make_ts(12)
        result = temporal_cross_validate(df, _perfect_forecast, min_train_size=8, horizon=1)
        assert isinstance(result.mean_rmse, float)

    def test_all_nan_forecast_raises(self):
        df = _make_ts(12)
        with pytest.raises(ValueError, match="All folds failed"):
            temporal_cross_validate(df, _nan_forecast, min_train_size=8, horizon=1)

    def test_step_parameter_reduces_fold_count(self):
        df = _make_ts(16)
        r1 = temporal_cross_validate(df, _perfect_forecast, min_train_size=8, horizon=1, step=1)
        r2 = temporal_cross_validate(df, _perfect_forecast, min_train_size=8, horizon=1, step=3)
        assert r1.n_folds > r2.n_folds

    def test_folds_list_length_matches_n_folds(self):
        df = _make_ts(12)
        result = temporal_cross_validate(df, _perfect_forecast, min_train_size=8, horizon=1)
        assert len(result.folds) == result.n_folds


# ── cross_validate_course ─────────────────────────────────────────────────────

class TestCrossValidateCourse:
    def _hist_df(self, n_quarters: int = 12) -> pd.DataFrame:
        """Minimal load_historical_data-shaped DataFrame."""
        quarters = (["Fall", "Winter", "Spring", "Summer"] * 4)[:n_quarters]
        years = [2020 + i // 4 for i in range(n_quarters)]
        return pd.DataFrame({
            "year": years,
            "quarter": quarters,
            "course_code": ["FOUN 110"] * n_quarters,
            "enrollment": np.arange(n_quarters, dtype=float) * 5 + 80,
        })

    def test_raises_for_unknown_course(self):
        df = self._hist_df()
        with pytest.raises(ValueError, match="No data found"):
            cross_validate_course(df, "FOUN 999", _perfect_forecast)

    def test_returns_cvresult(self):
        df = self._hist_df(12)
        result = cross_validate_course(df, "FOUN 110", _perfect_forecast,
                                       min_train_size=8, horizon=1)
        assert isinstance(result, CVResult)

    def test_n_folds_greater_than_zero(self):
        df = self._hist_df(12)
        result = cross_validate_course(df, "FOUN 110", _perfect_forecast,
                                       min_train_size=8, horizon=1)
        assert result.n_folds > 0
