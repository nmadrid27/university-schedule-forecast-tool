"""
Exponential Smoothing (ETS/Holt-Winters) forecasting model.
Extracted from app.py for modularity.
"""

from typing import TYPE_CHECKING, Union
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

if TYPE_CHECKING:
    from pandas import Series, DataFrame


def forecast_ets(df_ts: pd.DataFrame, periods: int) -> Union[np.ndarray, pd.Series]:
    """
    Run Exponential Smoothing (Holt-Winters) forecast.

    Args:
        df_ts: DataFrame with columns 'ds' (datetime) and 'y' (values)
        periods: Number of periods to forecast

    Returns:
        Array or Series of forecasted values. Returns array of NaN if all methods fail.
    """
    if df_ts.empty or len(df_ts) < 2:
        return np.full(periods, np.nan)
    try:
        # Try full Holt-Winters (Trend + Seasonality)
        # seasonal_periods=4 for quarterly data
        model = ExponentialSmoothing(
            df_ts['y'].values,
            seasonal_periods=4,
            trend='add',
            seasonal='add',
            damped_trend=True
        )
        fitted = model.fit()
        forecast = fitted.forecast(steps=periods)
        return forecast
    except Exception:
        try:
            # Fallback 1: Simple Exponential Smoothing (Level only)
            model = ExponentialSmoothing(df_ts['y'].values, trend='add')
            fitted = model.fit()
            return fitted.forecast(steps=periods)
        except Exception:
            # Fallback 2: Naive mean
            return np.full(periods, df_ts['y'].mean())
