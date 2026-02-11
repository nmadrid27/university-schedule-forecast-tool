"""
ARIMA-based forecasting model for enrollment data.
Uses statsmodels ARIMA with cascading fallbacks for robustness.
"""

from typing import Union
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA


def forecast_arima(df_ts: pd.DataFrame, periods: int) -> Union[np.ndarray, pd.Series]:
    """
    Run ARIMA forecast on quarterly enrollment data.

    Args:
        df_ts: DataFrame with columns 'ds' (datetime) and 'y' (values)
        periods: Number of periods to forecast

    Returns:
        Array or Series of forecasted values. Returns array of NaN if all methods fail.
    """
    if df_ts.empty or len(df_ts) < 4:
        if not df_ts.empty and len(df_ts) >= 2:
            return np.full(periods, df_ts['y'].mean())
        return np.full(periods, np.nan)

    endog = df_ts['y'].values

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        try:
            # ARIMA(1,1,1) — one autoregressive term, first differencing, one MA term
            model = ARIMA(endog, order=(1, 1, 1))
            fitted = model.fit()
            forecast = fitted.forecast(steps=periods)
            if np.any(np.isnan(forecast)):
                raise ValueError("NaN in forecast output")
            return forecast
        except Exception:
            try:
                # Fallback 1: ARIMA(1,1,0) — simpler model without MA component
                model = ARIMA(endog, order=(1, 1, 0))
                fitted = model.fit()
                forecast = fitted.forecast(steps=periods)
                if np.any(np.isnan(forecast)):
                    raise ValueError("NaN in forecast output")
                return forecast
            except Exception:
                try:
                    # Fallback 2: ARIMA(0,1,1) — MA-only with differencing
                    model = ARIMA(endog, order=(0, 1, 1))
                    fitted = model.fit()
                    forecast = fitted.forecast(steps=periods)
                    if np.any(np.isnan(forecast)):
                        raise ValueError("NaN in forecast output")
                    return forecast
                except Exception:
                    # Fallback 3: Naive mean
                    return np.full(periods, df_ts['y'].mean())
