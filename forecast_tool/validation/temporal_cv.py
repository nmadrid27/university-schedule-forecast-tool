"""
Expanding-window temporal cross-validation for enrollment forecasting.

Generates train/test splits that respect chronological order, evaluates
forecast callables on each fold, and aggregates error metrics (MAPE, RMSE, MAE).
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FoldResult:
    """Metrics for a single cross-validation fold."""

    fold: int
    train_size: int
    test_size: int
    mape: Optional[float]
    rmse: float
    mae: float
    actuals: np.ndarray
    predictions: np.ndarray


@dataclass
class CVResult:
    """Aggregated cross-validation results across all folds."""

    n_folds: int
    mean_mape: Optional[float]
    std_mape: Optional[float]
    mean_rmse: float
    std_rmse: float
    mean_mae: float
    std_mae: float
    folds: List[FoldResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return results as a plain dictionary."""
        return {
            "n_folds": self.n_folds,
            "mean_mape": self.mean_mape,
            "std_mape": self.std_mape,
            "mean_rmse": self.mean_rmse,
            "std_rmse": self.std_rmse,
            "mean_mae": self.mean_mae,
            "std_mae": self.std_mae,
            "per_fold": [
                {
                    "fold": f.fold,
                    "train_size": f.train_size,
                    "test_size": f.test_size,
                    "mape": f.mape,
                    "rmse": f.rmse,
                    "mae": f.mae,
                }
                for f in self.folds
            ],
        }


def _compute_mape(actuals: np.ndarray, predictions: np.ndarray) -> Optional[float]:
    """Compute Mean Absolute Percentage Error, skipping zero actuals.

    Returns None if all actuals are zero (MAPE undefined).
    """
    mask = actuals != 0
    if not mask.any():
        return None
    return float(np.mean(np.abs((actuals[mask] - predictions[mask]) / actuals[mask])) * 100)


def _compute_rmse(actuals: np.ndarray, predictions: np.ndarray) -> float:
    """Compute Root Mean Squared Error."""
    return float(np.sqrt(np.mean((actuals - predictions) ** 2)))


def _compute_mae(actuals: np.ndarray, predictions: np.ndarray) -> float:
    """Compute Mean Absolute Error."""
    return float(np.mean(np.abs(actuals - predictions)))


def expanding_window_splits(
    n_obs: int,
    min_train_size: int = 8,
    horizon: int = 1,
    step: int = 1,
) -> List[tuple]:
    """Generate expanding-window train/test index pairs.

    Args:
        n_obs: Total number of observations.
        min_train_size: Minimum observations in the training window.
        horizon: Number of periods in the test window.
        step: How many periods to advance the split point per fold.

    Returns:
        List of (train_indices, test_indices) tuples. Each element is a
        numpy array of integer indices.
    """
    splits = []
    start = min_train_size
    while start + horizon <= n_obs:
        train_idx = np.arange(0, start)
        test_idx = np.arange(start, start + horizon)
        splits.append((train_idx, test_idx))
        start += step
    return splits


def _extract_predictions(raw_output, horizon: int) -> np.ndarray:
    """Normalise forecast function output to a 1-D numpy array.

    Handles the two return conventions used in this project:
      - Prophet: pd.DataFrame with a ``yhat`` column
      - ETS / ARIMA: np.ndarray or pd.Series of values
    """
    if isinstance(raw_output, pd.DataFrame):
        if raw_output.empty:
            return np.full(horizon, np.nan)
        if "yhat" in raw_output.columns:
            return raw_output["yhat"].values[:horizon]
        # Fall back to the first numeric column
        numeric_cols = raw_output.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            return raw_output[numeric_cols[0]].values[:horizon]
        return np.full(horizon, np.nan)
    # array-like (ndarray, Series, list)
    arr = np.asarray(raw_output).flatten()
    return arr[:horizon]


def temporal_cross_validate(
    df_ts: pd.DataFrame,
    forecast_fn: Callable[[pd.DataFrame, int], Union[pd.DataFrame, np.ndarray]],
    min_train_size: int = 8,
    horizon: int = 1,
    step: int = 1,
) -> CVResult:
    """Run expanding-window temporal cross-validation on a single time series.

    Args:
        df_ts: DataFrame with ``ds`` (datetime) and ``y`` (numeric) columns,
               sorted chronologically.  This matches the format expected by
               ``forecast_prophet`` and ``forecast_ets``.
        forecast_fn: A callable with signature ``(df_ts, periods) -> predictions``.
                     The return value is either a DataFrame with a ``yhat``
                     column (Prophet convention) or an array-like of values
                     (ETS convention).
        min_train_size: Minimum observations required in the training window
                        before the first fold is created.
        horizon: Number of future periods to forecast (test window length).
        step: How many periods to advance the split point between folds.

    Returns:
        CVResult with per-fold and aggregated MAPE, RMSE, MAE.

    Raises:
        ValueError: If ``df_ts`` has fewer rows than ``min_train_size + horizon``
                    (no valid folds can be created).
    """
    if len(df_ts) < min_train_size + horizon:
        raise ValueError(
            f"Insufficient data for cross-validation: {len(df_ts)} observations, "
            f"need at least {min_train_size + horizon} "
            f"(min_train_size={min_train_size} + horizon={horizon})."
        )

    # Ensure sorted by date
    df_sorted = df_ts.sort_values("ds").reset_index(drop=True)
    splits = expanding_window_splits(len(df_sorted), min_train_size, horizon, step)

    fold_results: List[FoldResult] = []

    for fold_num, (train_idx, test_idx) in enumerate(splits, start=1):
        train_df = df_sorted.iloc[train_idx][["ds", "y"]].copy()
        test_df = df_sorted.iloc[test_idx]
        actuals = test_df["y"].values.astype(float)

        try:
            raw_pred = forecast_fn(train_df, horizon)
            predictions = _extract_predictions(raw_pred, horizon)
        except Exception as exc:
            logger.warning("Fold %d forecast failed: %s", fold_num, exc)
            predictions = np.full(horizon, np.nan)

        # Skip folds where forecast returned NaN
        if np.all(np.isnan(predictions)):
            logger.warning("Fold %d produced all-NaN predictions, skipping.", fold_num)
            continue

        mape = _compute_mape(actuals, predictions)
        rmse = _compute_rmse(actuals, predictions)
        mae = _compute_mae(actuals, predictions)

        fold_results.append(
            FoldResult(
                fold=fold_num,
                train_size=len(train_idx),
                test_size=len(test_idx),
                mape=mape,
                rmse=rmse,
                mae=mae,
                actuals=actuals,
                predictions=predictions,
            )
        )

    if not fold_results:
        raise ValueError("All folds failed to produce valid predictions.")

    # Aggregate metrics
    rmse_vals = np.array([f.rmse for f in fold_results])
    mae_vals = np.array([f.mae for f in fold_results])

    mape_vals = [f.mape for f in fold_results if f.mape is not None]
    mean_mape = float(np.mean(mape_vals)) if mape_vals else None
    std_mape = float(np.std(mape_vals)) if mape_vals else None

    return CVResult(
        n_folds=len(fold_results),
        mean_mape=mean_mape,
        std_mape=std_mape,
        mean_rmse=float(np.mean(rmse_vals)),
        std_rmse=float(np.std(rmse_vals)),
        mean_mae=float(np.mean(mae_vals)),
        std_mae=float(np.std(mae_vals)),
        folds=fold_results,
    )


def cross_validate_course(
    df_hist: pd.DataFrame,
    course_code: str,
    forecast_fn: Callable[[pd.DataFrame, int], Union[pd.DataFrame, np.ndarray]],
    min_train_size: int = 8,
    horizon: int = 1,
    step: int = 1,
) -> CVResult:
    """Convenience wrapper: filter historical data to one course, build a
    ``ds``/``y`` time series, and run ``temporal_cross_validate``.

    Args:
        df_hist: DataFrame produced by ``data.loaders.load_historical_data`` with
                 columns ``year``, ``quarter``, ``course_code``, ``enrollment``.
        course_code: e.g. ``"DRAW 100"``
        forecast_fn: Forecast callable (same interface as ``temporal_cross_validate``).
        min_train_size: Passed through to ``temporal_cross_validate``.
        horizon: Passed through.
        step: Passed through.

    Returns:
        CVResult for the given course.
    """
    from forecast_tool.data.transformers import quarter_to_date

    course_df = df_hist[df_hist["course_code"] == course_code].copy()
    if course_df.empty:
        raise ValueError(f"No data found for course '{course_code}'.")

    # Aggregate enrollment per quarter in case of multiple sections
    agg = (
        course_df.groupby(["year", "quarter"])["enrollment"]
        .sum()
        .reset_index()
    )

    agg["ds"] = agg.apply(
        lambda row: quarter_to_date(row["year"], row["quarter"]), axis=1
    )
    agg = agg.rename(columns={"enrollment": "y"}).sort_values("ds").reset_index(drop=True)

    return temporal_cross_validate(
        agg[["ds", "y"]],
        forecast_fn,
        min_train_size=min_train_size,
        horizon=horizon,
        step=step,
    )
