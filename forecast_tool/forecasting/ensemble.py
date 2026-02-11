"""
Ensemble forecasting methods and section calculations.
Extracted from app.py for modularity.
"""

import logging
from typing import Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Default weights for the 3-model ensemble
DEFAULT_WEIGHTS: Dict[str, float] = {
    "prophet": 0.40,
    "ets": 0.35,
    "arima": 0.25,
}


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


def ensemble_forecast(
    prophet_pred: Union[int, float],
    ets_pred: Union[int, float],
    weight_prophet: float = 0.6,
    arima_pred: Optional[Union[int, float]] = None,
    weight_arima: Optional[float] = None,
) -> float:
    """
    Combine forecasts using weighted ensemble.

    Backward compatible: calling with just (prophet_pred, ets_pred) or
    (prophet_pred, ets_pred, weight_prophet) works exactly as before.

    When arima_pred is provided, a 3-model blend is used. If weight_arima
    is not specified, default weights (40/35/25) are applied.

    NaN predictions are excluded and remaining weights are renormalized.

    Args:
        prophet_pred: Prophet forecast value
        ets_pred: ETS forecast value
        weight_prophet: Weight for Prophet (0.0 to 1.0)
        arima_pred: Optional ARIMA forecast value
        weight_arima: Optional weight for ARIMA

    Returns:
        Weighted ensemble prediction. Returns NaN only if all inputs are NaN.
    """
    if arima_pred is None:
        # Original 2-model path (backward compatible)
        preds = {"prophet": prophet_pred, "ets": ets_pred}
        weights = {"prophet": weight_prophet, "ets": 1.0 - weight_prophet}
    else:
        if weight_arima is None:
            weights = dict(DEFAULT_WEIGHTS)
        else:
            weight_ets = 1.0 - weight_prophet - weight_arima
            weights = {"prophet": weight_prophet, "ets": weight_ets, "arima": weight_arima}
        preds = {"prophet": prophet_pred, "ets": ets_pred, "arima": arima_pred}

    return _weighted_mean_with_nan(preds, weights)


def ensemble_forecast_weighted(
    predictions: Dict[str, Union[int, float]],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Combine named model predictions using a weights dictionary.

    This is the preferred interface for 3+ model ensembles. Handles NaN
    predictions by redistributing weight to models that produced valid values.

    Args:
        predictions: Mapping of model name to prediction value.
                     e.g. {"prophet": 120.5, "ets": 118.0, "arima": 122.3}
        weights: Mapping of model name to weight.
                 Defaults to DEFAULT_WEIGHTS if not provided.
                 Weights should sum to 1.0 but will be renormalized if needed.

    Returns:
        Weighted ensemble prediction. Returns NaN only if all inputs are NaN.
    """
    if weights is None:
        weights = dict(DEFAULT_WEIGHTS)

    return _weighted_mean_with_nan(predictions, weights)


def _weighted_mean_with_nan(
    predictions: Dict[str, Union[int, float]],
    weights: Dict[str, float],
) -> float:
    """Compute weighted mean, redistributing weight from NaN predictions."""
    valid_preds = {}
    valid_weights = {}

    for name, pred in predictions.items():
        w = weights.get(name, 0.0)
        if w <= 0:
            continue
        if pred is not None and np.isfinite(pred):
            valid_preds[name] = float(pred)
            valid_weights[name] = w

    if not valid_preds:
        return float("nan")

    # Renormalize weights so they sum to 1.0
    total_w = sum(valid_weights.values())
    result = sum(
        valid_preds[name] * (valid_weights[name] / total_w)
        for name in valid_preds
    )
    return float(result)


def optimize_ensemble_weights(
    df_ts: pd.DataFrame,
    forecast_fns: Dict[str, Callable[[pd.DataFrame, int], Union[pd.DataFrame, np.ndarray]]],
    weight_step: float = 0.05,
    min_train_size: int = 8,
    horizon: int = 1,
    step: int = 1,
    metric: str = "rmse",
) -> Tuple[Dict[str, float], float]:
    """
    Find optimal ensemble weights via grid search over temporal cross-validation.

    Generates all weight combinations (summing to 1.0) at the given step size,
    evaluates each combination's CV error, and returns the best weights.

    Args:
        df_ts: DataFrame with 'ds' (datetime) and 'y' (values) columns.
        forecast_fns: Mapping of model name to forecast callable.
                      e.g. {"prophet": forecast_prophet, "ets": forecast_ets,
                             "arima": forecast_arima}
        weight_step: Granularity for weight grid (default 0.05 = 5% increments).
        min_train_size: Minimum training window for temporal CV.
        horizon: Forecast horizon for temporal CV.
        step: Step size between CV folds.
        metric: Error metric to minimize ("rmse", "mae", or "mape").

    Returns:
        Tuple of (best_weights_dict, best_metric_value).
        best_weights_dict maps model name -> optimal weight.

    Raises:
        ValueError: If df_ts has insufficient data for cross-validation.
    """
    from forecast_tool.validation.temporal_cv import (
        expanding_window_splits,
        _extract_predictions,
        _compute_rmse,
        _compute_mae,
        _compute_mape,
    )

    if len(df_ts) < min_train_size + horizon:
        raise ValueError(
            f"Insufficient data for weight optimization: {len(df_ts)} observations, "
            f"need at least {min_train_size + horizon}."
        )

    model_names = list(forecast_fns.keys())
    n_models = len(model_names)

    # Sort data
    df_sorted = df_ts.sort_values("ds").reset_index(drop=True)
    splits = expanding_window_splits(len(df_sorted), min_train_size, horizon, step)

    if not splits:
        raise ValueError("No valid CV splits could be generated.")

    # Pre-compute per-model predictions for each fold
    # fold_preds[model_name] = list of np.ndarray predictions per fold
    # fold_actuals = list of np.ndarray actuals per fold
    fold_preds: Dict[str, List[Optional[np.ndarray]]] = {name: [] for name in model_names}
    fold_actuals: List[np.ndarray] = []
    valid_fold_mask: List[bool] = []

    for train_idx, test_idx in splits:
        train_df = df_sorted.iloc[train_idx][["ds", "y"]].copy()
        test_df = df_sorted.iloc[test_idx]
        actuals = test_df["y"].values.astype(float)
        fold_actuals.append(actuals)

        any_valid = False
        for name in model_names:
            try:
                raw = forecast_fns[name](train_df, horizon)
                preds = _extract_predictions(raw, horizon)
                if np.all(np.isnan(preds)):
                    preds = None
                else:
                    any_valid = True
            except Exception:
                preds = None
            fold_preds[name].append(preds)

        valid_fold_mask.append(any_valid)

    valid_folds = [i for i, v in enumerate(valid_fold_mask) if v]
    if not valid_folds:
        raise ValueError("All models failed on all folds.")

    # Generate weight grid
    weight_combos = _generate_weight_grid(n_models, weight_step)

    best_weights = None
    best_error = float("inf")

    metric_fn = {
        "rmse": _compute_rmse,
        "mae": _compute_mae,
    }.get(metric)

    for combo in weight_combos:
        weights = {model_names[i]: combo[i] for i in range(n_models)}
        fold_errors = []

        for fold_i in valid_folds:
            actuals = fold_actuals[fold_i]

            # Build weighted prediction for this fold
            preds_dict = {}
            for name in model_names:
                fp = fold_preds[name][fold_i]
                if fp is not None:
                    preds_dict[name] = fp

            if not preds_dict:
                continue

            # Compute ensemble prediction (handle per-horizon-step)
            ensemble_preds = np.zeros(horizon)
            for h in range(horizon):
                point_preds = {}
                for name, arr in preds_dict.items():
                    if h < len(arr) and np.isfinite(arr[h]):
                        point_preds[name] = arr[h]

                if point_preds:
                    ensemble_preds[h] = _weighted_mean_with_nan(point_preds, weights)
                else:
                    ensemble_preds[h] = np.nan

            if np.all(np.isnan(ensemble_preds)):
                continue

            if metric == "mape":
                err = _compute_mape(actuals, ensemble_preds)
                if err is not None:
                    fold_errors.append(err)
            elif metric_fn is not None:
                fold_errors.append(metric_fn(actuals, ensemble_preds))

        if fold_errors:
            mean_error = float(np.mean(fold_errors))
            if mean_error < best_error:
                best_error = mean_error
                best_weights = weights

    if best_weights is None:
        logger.warning("Weight optimization failed; returning default weights.")
        best_weights = dict(DEFAULT_WEIGHTS)
        best_error = float("inf")

    return best_weights, best_error


def _generate_weight_grid(n_models: int, step: float) -> List[Tuple[float, ...]]:
    """Generate all weight combinations summing to 1.0 at the given step size."""
    n_steps = int(round(1.0 / step))
    combos = []
    _generate_recursive(n_models, n_steps, [], combos, step)
    return combos


def _generate_recursive(
    remaining: int,
    remaining_steps: int,
    current: List[float],
    results: List[Tuple[float, ...]],
    step: float,
) -> None:
    """Recursive helper for weight grid generation."""
    if remaining == 1:
        weight = round(remaining_steps * step, 10)
        results.append(tuple(current + [weight]))
        return
    for s in range(remaining_steps + 1):
        weight = round(s * step, 10)
        _generate_recursive(remaining - 1, remaining_steps - s, current + [weight], results, step)
