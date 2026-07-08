# Forecast Tool Memory

## 2026-07-08 review/fix pass

- Default forecast method is now `auto`: same-season historical first, sequence-map fallback when same-season history is unavailable.
- API request `method` is optional and no longer masks `forecast_config.json`; config persists `method` and `demand_metric`.
- Planning metric support added: `actual`, `max`, and `actual_plus_waitlist` for PZSMSCP CSV/xlsx loaders.
- CSV Master Schedule loading now dedupes duplicate CRN rows like the xlsx loader.
- `/api/terms` returns `forecastable_by_method`; frontend uses method-specific term lists.
- `/api/backtest` compares forecast rows to PZSMSCP ground truth and reports MAE/MAPE/bias/capture overall and by campus.
- Admits-file maturity diagnostics warn when sequence-based intro-course demand is likely low because few admits have registered for FOUN courses.
- Anomaly detection now builds campus-aware historical series from the active Master Schedule.
- Frontend config sidebar now exposes Method and Planning Metric selectors and loads saved default term/method/metric from the API.
- `api.main` can be imported package-style (`import api.main`) and script-style; Next `turbopack.root` is pinned.
- Validation after changes: backend `556 passed`; frontend `145 passed`; lint clean; production build succeeds.
