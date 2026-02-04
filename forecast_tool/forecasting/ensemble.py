"""
Ensemble forecasting methods and section calculations.
Extracted from app.py for modularity.
"""

import numpy as np


def calculate_sections(enrollment, capacity, buffer_pct):
    """
    Calculate sections needed with buffer.

    Args:
        enrollment: Forecasted enrollment count
        capacity: Students per section
        buffer_pct: Capacity buffer percentage (0-100)

    Returns:
        Number of sections needed (integer)
    """
    effective_capacity = capacity * (1 - buffer_pct / 100)
    return int(np.ceil(enrollment / effective_capacity))


def ensemble_forecast(prophet_pred, ets_pred, weight_prophet=0.6):
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
