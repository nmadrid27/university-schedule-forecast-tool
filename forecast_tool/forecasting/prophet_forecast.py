"""
Prophet-based forecasting model.
Extracted from app.py for modularity.
"""

from prophet import Prophet


def forecast_prophet(df_ts, periods):
    """
    Run Prophet forecast.

    Args:
        df_ts: DataFrame with columns 'ds' (datetime) and 'y' (values)
        periods: Number of periods to forecast

    Returns:
        DataFrame with columns 'ds', 'yhat', 'yhat_lower', 'yhat_upper' for forecast periods
    """
    model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    model.fit(df_ts)
    future = model.make_future_dataframe(periods=periods, freq='QS')
    forecast = model.predict(future)
    return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
