"""
Prophet-based forecasting model.
Extracted from app.py for modularity.
"""

from typing import TYPE_CHECKING
import pandas as pd
from prophet import Prophet

if TYPE_CHECKING:
    from prophet.forecaster import Prophet


def forecast_prophet(df_ts: pd.DataFrame, periods: int) -> pd.DataFrame:
    """
    Run Prophet forecast.

    Args:
        df_ts: DataFrame with columns 'ds' (datetime) and 'y' (values)
        periods: Number of periods to forecast

    Returns:
        DataFrame with columns 'ds', 'yhat', 'yhat_lower', 'yhat_upper' for forecast periods.
        Returns empty DataFrame if forecasting fails.
    """
    if df_ts.empty or len(df_ts) < 2:
        return pd.DataFrame()

    try:
        model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        model.fit(df_ts)
        future = model.make_future_dataframe(periods=periods, freq='QS')
        forecast = model.predict(future)
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
    except Exception:
        return pd.DataFrame()
