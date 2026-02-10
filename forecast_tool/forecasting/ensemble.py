"""
Ensemble forecasting methods and section calculations.
Extracted from app.py for modularity.
"""

from typing import Union
import numpy as np


def calculate_sections(enrollment: Union[int, float], capacity: int, buffer_pct: float) -> int:
    """
    Calculate sections needed with buffer.

    Args:
        enrollment: Forecasted enrollment count
        capacity: Students per section
        buffer_pct: Capacity buffer percentage (0-100)

    Returns:
        Number of sections needed (integer). Returns 0 for invalid inputs.
    """
    if capacity <= 0 or enrollment < 0:
        return 0
    effective_capacity = capacity * (1 - buffer_pct / 100)
    if effective_capacity <= 0:
        return 0
    return int(np.ceil(enrollment / effective_capacity))


def ensemble_forecast(prophet_pred: Union[int, float], ets_pred: Union[int, float],
                      weight_prophet: float = 0.6) -> float:
    """
    Combine Prophet and ETS forecasts using weighted ensemble.

    Args:
        prophet_pred: Prophet forecast value
        ets_pred: ETS forecast value
        weight_prophet: Weight for Prophet (0.0 to 1.0), ETS gets (1 - weight_prophet)

    Returns:
        Weighted ensemble prediction
    """
    return (weight_prophet * prophet_pred + (1 - weight_prophet) * ets_pred)
