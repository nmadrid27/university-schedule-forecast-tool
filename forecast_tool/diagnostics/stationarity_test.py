"""
Stationarity and seasonality diagnostics for enrollment time series.
Uses Augmented Dickey-Fuller tests and seasonal decomposition to assess
whether course enrollment series are suitable for forecasting models.
"""

import logging
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.seasonal import seasonal_decompose

logger = logging.getLogger(__name__)

# Significance level for ADF test
ADF_SIGNIFICANCE_LEVEL = 0.05

# Minimum observations required for ADF test
MIN_OBSERVATIONS_ADF = 8

# Minimum observations required for seasonal decomposition (need at least 2 full cycles)
MIN_OBSERVATIONS_SEASONAL = 8


def test_stationarity(series: pd.Series, significance_level: float = ADF_SIGNIFICANCE_LEVEL) -> Dict:
    """
    Run Augmented Dickey-Fuller test on an enrollment time series.

    Args:
        series: Pandas Series of enrollment values ordered chronologically.
        significance_level: P-value threshold for stationarity (default 0.05).

    Returns:
        dict with keys:
            - test_statistic: ADF test statistic
            - p_value: p-value of the test
            - is_stationary: bool indicating stationarity at given significance level
            - critical_values: dict of critical values at 1%, 5%, 10%
            - n_observations: number of observations used
            - interpretation: human-readable summary string
    """
    series = series.dropna()

    if len(series) < MIN_OBSERVATIONS_ADF:
        return {
            "test_statistic": None,
            "p_value": None,
            "is_stationary": None,
            "critical_values": {},
            "n_observations": len(series),
            "interpretation": (
                f"Insufficient data: {len(series)} observations "
                f"(need at least {MIN_OBSERVATIONS_ADF} for ADF test)"
            ),
        }

    # Check for constant series (zero variance)
    if series.std() == 0:
        return {
            "test_statistic": None,
            "p_value": None,
            "is_stationary": True,
            "critical_values": {},
            "n_observations": len(series),
            "interpretation": "Constant series (zero variance) — trivially stationary",
        }

    try:
        result = adfuller(series.values, autolag="AIC")
    except Exception as e:
        logger.warning(f"ADF test failed: {e}")
        return {
            "test_statistic": None,
            "p_value": None,
            "is_stationary": None,
            "critical_values": {},
            "n_observations": len(series),
            "interpretation": f"ADF test failed: {e}",
        }

    adf_stat, p_value, used_lag, n_obs, critical_values, icbest = result
    is_stationary = p_value < significance_level

    if is_stationary:
        interpretation = (
            f"Stationary (ADF={adf_stat:.4f}, p={p_value:.4f}). "
            f"The series does not have a unit root at the {significance_level:.0%} level."
        )
    else:
        interpretation = (
            f"Non-stationary (ADF={adf_stat:.4f}, p={p_value:.4f}). "
            f"Cannot reject the unit root hypothesis at the {significance_level:.0%} level. "
            f"Differencing or detrending may be needed before modeling."
        )

    return {
        "test_statistic": float(adf_stat),
        "p_value": float(p_value),
        "is_stationary": is_stationary,
        "critical_values": {k: float(v) for k, v in critical_values.items()},
        "n_observations": int(n_obs),
        "interpretation": interpretation,
    }


def measure_seasonal_strength(
    series: pd.Series, period: int = 4
) -> Dict:
    """
    Measure the strength of seasonality using STL-style seasonal decomposition.

    Seasonal strength is calculated as 1 - Var(residual) / Var(seasonal + residual),
    following the approach from Hyndman & Athanasopoulos (2021). A value near 1
    indicates strong seasonality; near 0 indicates weak or no seasonality.

    Args:
        series: Pandas Series of enrollment values ordered chronologically.
        period: Seasonal period (default 4 for quarterly SCAD data).

    Returns:
        dict with keys:
            - strength: seasonal strength score (0.0 to 1.0)
            - seasonal_component: array of seasonal values
            - trend_component: array of trend values
            - residual_component: array of residual values
            - interpretation: human-readable summary string
    """
    series = series.dropna()

    if len(series) < MIN_OBSERVATIONS_SEASONAL:
        return {
            "strength": None,
            "seasonal_component": None,
            "trend_component": None,
            "residual_component": None,
            "interpretation": (
                f"Insufficient data: {len(series)} observations "
                f"(need at least {MIN_OBSERVATIONS_SEASONAL} for seasonal decomposition "
                f"with period={period})"
            ),
        }

    if len(series) < 2 * period:
        return {
            "strength": None,
            "seasonal_component": None,
            "trend_component": None,
            "residual_component": None,
            "interpretation": (
                f"Insufficient data: {len(series)} observations "
                f"(need at least {2 * period} for {period}-period seasonal decomposition)"
            ),
        }

    try:
        decomposition = seasonal_decompose(
            series.values, model="additive", period=period
        )
    except Exception as e:
        logger.warning(f"Seasonal decomposition failed: {e}")
        return {
            "strength": None,
            "seasonal_component": None,
            "trend_component": None,
            "residual_component": None,
            "interpretation": f"Seasonal decomposition failed: {e}",
        }

    seasonal = decomposition.seasonal
    residual = decomposition.resid

    # Drop NaN values from residual (decomposition produces NaNs at edges)
    valid_mask = ~np.isnan(residual)
    residual_valid = residual[valid_mask]
    seasonal_valid = seasonal[valid_mask]

    var_residual = np.var(residual_valid)
    var_seasonal_plus_residual = np.var(seasonal_valid + residual_valid)

    if var_seasonal_plus_residual == 0:
        strength = 0.0
    else:
        strength = max(0.0, 1.0 - var_residual / var_seasonal_plus_residual)

    if strength >= 0.6:
        level = "Strong"
    elif strength >= 0.3:
        level = "Moderate"
    else:
        level = "Weak"

    interpretation = (
        f"{level} seasonality (strength={strength:.4f}). "
        f"{'Seasonal models (e.g., Holt-Winters) are recommended.' if strength >= 0.3 else 'Non-seasonal models may suffice.'}"
    )

    return {
        "strength": float(strength),
        "seasonal_component": seasonal.tolist(),
        "trend_component": decomposition.trend.tolist(),
        "residual_component": residual.tolist(),
        "interpretation": interpretation,
    }


def analyze_all_courses(
    course_dict: Dict[str, pd.Series],
    significance_level: float = ADF_SIGNIFICANCE_LEVEL,
    seasonal_period: int = 4,
) -> Dict:
    """
    Run stationarity and seasonality diagnostics on all courses.

    Args:
        course_dict: Dictionary mapping course names to enrollment Series.
            Each Series should be chronologically ordered enrollment values.
        significance_level: P-value threshold for ADF stationarity test.
        seasonal_period: Period for seasonal decomposition (default 4 for quarterly).

    Returns:
        dict with keys:
            - results: dict mapping course name to per-course diagnostics
                (each containing 'stationarity' and 'seasonality' sub-dicts)
            - summary: dict with aggregate statistics:
                - total_courses: number of courses analyzed
                - stationary_count: courses found stationary
                - non_stationary_count: courses found non-stationary
                - insufficient_data_count: courses with too little data
                - non_stationary_courses: list of non-stationary course names
                - avg_seasonal_strength: mean seasonal strength across valid courses
                - strong_seasonality_courses: list of courses with strength >= 0.6
    """
    results = {}
    stationary_count = 0
    non_stationary_count = 0
    insufficient_data_count = 0
    non_stationary_courses = []
    seasonal_strengths = []
    strong_seasonality_courses = []

    for course_name, series in course_dict.items():
        stationarity = test_stationarity(series, significance_level)
        seasonality = measure_seasonal_strength(series, seasonal_period)

        results[course_name] = {
            "stationarity": stationarity,
            "seasonality": seasonality,
        }

        if stationarity["is_stationary"] is None:
            insufficient_data_count += 1
        elif stationarity["is_stationary"]:
            stationary_count += 1
        else:
            non_stationary_count += 1
            non_stationary_courses.append(course_name)

        if seasonality["strength"] is not None:
            seasonal_strengths.append(seasonality["strength"])
            if seasonality["strength"] >= 0.6:
                strong_seasonality_courses.append(course_name)

    avg_seasonal_strength = (
        float(np.mean(seasonal_strengths)) if seasonal_strengths else None
    )

    summary = {
        "total_courses": len(course_dict),
        "stationary_count": stationary_count,
        "non_stationary_count": non_stationary_count,
        "insufficient_data_count": insufficient_data_count,
        "non_stationary_courses": sorted(non_stationary_courses),
        "avg_seasonal_strength": avg_seasonal_strength,
        "strong_seasonality_courses": sorted(strong_seasonality_courses),
    }

    return {"results": results, "summary": summary}
