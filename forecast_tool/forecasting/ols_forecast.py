"""
Season-aware OLS linear regression forecasting.

Replaces Prophet for trend-based enrollment forecasting. Groups historical
data by quarter (Fall, Winter, Spring, Summer) and fits a simple linear
trend per season. More interpretable and sufficient for 4-6 data points.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Quarter suffix in SCAD term codes
_QTR_MAP = {"10": "Fall", "20": "Winter", "30": "Spring", "40": "Summer"}


def _term_to_parts(term_code: str) -> Tuple[str, int]:
    """Return (season_label, calendar_year) for a SCAD term code."""
    year_str = term_code[:4]
    qtr = term_code[4:]
    season = _QTR_MAP.get(qtr, "Unknown")
    cal_year = int(year_str) - 1 if qtr == "10" else int(year_str)
    return season, cal_year


def _ols_slope_intercept(x: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    """Ordinary least-squares fit: y = slope * x + intercept."""
    x = x.astype(float)
    y = y.astype(float)
    n = len(x)
    if n < 2:
        return 0.0, float(y[0]) if n == 1 else 0.0
    x_bar, y_bar = x.mean(), y.mean()
    denom = ((x - x_bar) ** 2).sum()
    if denom == 0:
        return 0.0, y_bar
    slope = ((x - x_bar) * (y - y_bar)).sum() / denom
    intercept = y_bar - slope * x_bar
    return float(slope), float(intercept)


def _r_squared(x: np.ndarray, y: np.ndarray, slope: float, intercept: float) -> float:
    """Return R² for the fitted line."""
    y_pred = slope * x + intercept
    ss_res = ((y - y_pred) ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    return float(1 - ss_res / ss_tot) if ss_tot > 0 else 1.0


def forecast_ols(df_ts: pd.DataFrame, periods: int = 1) -> pd.DataFrame:
    """
    Season-aware OLS forecast.

    Args:
        df_ts: DataFrame with 'ds' (datetime or SCAD term code string)
               and 'y' (enrollment) columns. Rows from a single course/campus.
        periods: Number of future periods to forecast (default 1).

    Returns:
        DataFrame with columns ['ds', 'yhat', 'yhat_lower', 'yhat_upper',
        'slope', 'r_squared', 'n_train'] for the forecasted periods.
        Returns empty DataFrame if fitting fails.
    """
    if df_ts.empty or len(df_ts) < 2:
        return pd.DataFrame()

    try:
        df = df_ts.copy().sort_values("ds").reset_index(drop=True)

        # Represent each ds as a numeric index (position in the sorted series)
        x = np.arange(len(df), dtype=float)
        y = df["y"].values.astype(float)

        slope, intercept = _ols_slope_intercept(x, y)
        r2 = _r_squared(x, y, slope, intercept)

        # Residual std for simple prediction interval (~95%)
        y_pred_train = slope * x + intercept
        residuals = y - y_pred_train
        resid_std = float(residuals.std()) if len(residuals) > 2 else float(y.std())

        n = len(df)
        rows = []
        for i in range(1, periods + 1):
            x_fut = float(n - 1 + i)
            yhat = max(0.0, slope * x_fut + intercept)
            margin = 1.96 * resid_std
            rows.append({
                "ds": x_fut,
                "yhat": yhat,
                "yhat_lower": max(0.0, yhat - margin),
                "yhat_upper": yhat + margin,
                "slope": slope,
                "r_squared": r2,
                "n_train": n,
            })

        return pd.DataFrame(rows)

    except Exception as exc:
        logger.warning("OLS forecast failed: %s", exc)
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Season-grouped historical builder
# ---------------------------------------------------------------------------

def build_season_series(
    historical: Dict[str, int],
    season: str,
    crosswalk: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """
    Build a single-season time series from a {term_code: enrollment} dict.

    Args:
        historical: Mapping of SCAD term code -> total enrollment.
        season: One of "Fall", "Winter", "Spring", "Summer".
        crosswalk: Optional legacy_code -> foun_code mapping; unused here
                   (caller should aggregate before passing).

    Returns:
        DataFrame with columns ['ds', 'y', 'cal_year'] sorted by year.
        Empty if no matching season data.
    """
    rows = []
    for term_code, enroll in historical.items():
        s, cal_year = _term_to_parts(term_code)
        if s != season:
            continue
        rows.append({"ds": term_code, "y": float(enroll), "cal_year": cal_year})

    if not rows:
        return pd.DataFrame(columns=["ds", "y", "cal_year"])

    df = pd.DataFrame(rows).sort_values("cal_year").reset_index(drop=True)
    return df


def forecast_next_season(
    historical: Dict[str, int],
    target_season: str,
    next_year: int,
) -> Dict:
    """
    Fit OLS on same-season historical data and project one period ahead.

    Args:
        historical: {term_code: enrollment} for a single course+campus.
        target_season: "Fall", "Winter", "Spring", or "Summer".
        next_year: The calendar year of the target term.

    Returns:
        Dict with keys: yhat, yhat_lower, yhat_upper, slope, r_squared,
        n_train, season, next_year, trend_direction.
        Returns None if insufficient data (< 2 same-season points).
    """
    df = build_season_series(historical, target_season)
    if len(df) < 2:
        return None

    result_df = forecast_ols(df[["ds", "y"]], periods=1)
    if result_df.empty:
        return None

    row = result_df.iloc[0]
    yhat = float(row["yhat"])
    slope = float(row["slope"])

    return {
        "yhat": round(yhat, 1),
        "yhat_lower": round(float(row["yhat_lower"]), 1),
        "yhat_upper": round(float(row["yhat_upper"]), 1),
        "slope": round(slope, 2),
        "r_squared": round(float(row["r_squared"]), 3),
        "n_train": int(row["n_train"]),
        "season": target_season,
        "next_year": next_year,
        "trend_direction": "up" if slope > 5 else ("down" if slope < -5 else "flat"),
    }


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------

ANOMALY_THRESHOLD = 0.25  # flag if latest actual deviates > 25% from OLS trend


def detect_anomaly(
    historical: Dict[str, int],
    target_season: str,
    latest_actual: Optional[float] = None,
    threshold: float = ANOMALY_THRESHOLD,
) -> Dict:
    """
    Compare OLS trend projection against the latest available actual enrollment.

    If the latest actual deviates from the trend by more than `threshold`,
    returns a flag with details. Useful for catching sequencing guide changes.

    Args:
        historical: {term_code: enrollment} for one course+campus.
        target_season: Season to project for anomaly comparison.
        latest_actual: The most recent actual enrollment to compare against.
                       If None, uses the last value in historical.
        threshold: Fractional deviation to flag (default 0.25 = 25%).

    Returns:
        Dict with: flagged (bool), deviation_pct, trend_yhat, actual,
        message. Empty dict if insufficient data.
    """
    df = build_season_series(historical, target_season)
    if len(df) < 2:
        return {}

    # If no latest_actual supplied, leave-one-out: train on all-but-last, predict last
    if latest_actual is None:
        train_df = df.iloc[:-1][["ds", "y"]]
        actual = float(df.iloc[-1]["y"])
    else:
        train_df = df[["ds", "y"]]
        actual = float(latest_actual)

    result_df = forecast_ols(train_df, periods=1)
    if result_df.empty:
        return {}

    yhat = float(result_df.iloc[0]["yhat"])
    if yhat == 0:
        deviation = 0.0
    else:
        deviation = abs(actual - yhat) / yhat

    flagged = deviation > threshold
    direction = "above" if actual > yhat else "below"
    msg = (
        f"Actual ({actual:.0f}) is {deviation:.0%} {direction} OLS trend ({yhat:.0f}). "
        f"{'Review sequencing guide or structural shift.' if flagged else 'Within normal range.'}"
    )

    return {
        "flagged": flagged,
        "deviation_pct": round(deviation * 100, 1),
        "trend_yhat": round(yhat, 1),
        "actual": actual,
        "threshold_pct": round(threshold * 100, 1),
        "message": msg,
    }
