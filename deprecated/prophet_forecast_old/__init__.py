"""
Prophet Forecast Module for University Scheduling

Provides Prophet-based enrollment forecasting for course section planning.
"""

from prophet_forecast.forecaster import UniversityForecaster
from prophet_forecast.data_loader import load_historical_data, parse_term_code, term_to_date
from prophet_forecast.config import (
    TERM_MAP,
    DEFAULT_SECTION_CAPACITY,
    DEFAULT_BUFFER_PERCENT,
)

__all__ = [
    "UniversityForecaster",
    "load_historical_data",
    "parse_term_code",
    "term_to_date",
    "TERM_MAP",
    "DEFAULT_SECTION_CAPACITY",
    "DEFAULT_BUFFER_PERCENT",
]
