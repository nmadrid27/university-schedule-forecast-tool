# Design: Course-Level Same-Season Historical Forecasting

- **Date:** 2026-06-08
- **Status:** Approved (design); pending implementation plan
- **Topic:** Add a course-level same-season historical forecast as the primary method, decoupled from the sequencing guide. Demote the sequence-map method to an optional cross-check.
- **Provenance:** Drafted collaboratively with Claude through the brainstorming process. Decisions are Nathan's, made by explicit choice.

## 1. Why

The current primary method (`run_sequence_forecast`) hard-codes major-to-course routing in `FOUN_sequencing_map_by_major.csv`. The curriculum committee is about to rewrite the sequencing guide for all majors, which would make that map stale, require constant re-authoring, and swing the forecast on every edit. A course-level historical method forecasts each course from its own enrollment history, so it is immune to sequencing-guide changes.

Evidence it works: the April 7 same-season Fall 2026 forecast (`Data/Fall_2026_FOUN_Forecast.xlsx`) matched the seats the department actually scheduled within ~4% in aggregate. The sequence engine, by contrast, under-forecasts and has been hard to calibrate (`docs/SPRING_2026_CALIBRATION.md`).

## 2. Approved decisions

1. **Primary method = course-level same-season historical.** Default for `/api/forecast`.
2. **Sequence map = optional**, selectable via `method: sequence`. Kept in the codebase, not deleted, as a cross-check.
3. **Post-rollout history only.** Same-season history is drawn from terms at or after the FOUN curriculum rollout (Fall 2025, term code `202610` = `_FOUN_CURRICULUM_START`). Earlier terms are the old curriculum and are excluded.
4. **Flat base + existing scenario bands.** The point forecast is last year's same term (a fitted trend once 2+ post-rollout same-season points exist). No built-in haircut. The existing scenario layer supplies ±% bands per run.
5. **New courses flagged for manual estimate**, not silently dropped.

## 3. The forecast rule

For target term T (e.g., Fall 2026 = `202710`):

1. Determine the season (quarter digits) and the **prior same-season term codes**: decrement the year by 1 each step (`202610`, `202510`, …), keeping only those `>= 202610`. For Fall 2026 that is `[202610]` (Fall 2025) — one point today. For Fall 2027 it would be `[202710, 202610]` — two points, enabling a trend.
2. For each FOUN `(campus, course)` with enrollment in those terms, build its same-season series (year → enrollment) from the imported Master Schedule via `load_term_enrollments`.
3. Project:
   - **2+ points** → fit the season-aware OLS trend (`forecast_tool/forecasting/ols_forecast.py`) and evaluate at T's year.
   - **1 point** → level: forecast = that enrollment.
4. `seats = forecast * (1 + buffer_percent/100)`; `sections = ceil(seats / capacity)`.
5. Scenarios are applied downstream by the existing scenario layer in `run_forecast` (unchanged).

## 4. Components (reusing existing code)

- **New `run_sameseason_forecast(master_schedule_path, target_term, capacity, buffer_percent, crosswalk=None)` in `api/forecaster.py`.** Returns the same row shape as `run_sequence_forecast` (`course, campus, projected_seats, sections, method`). Built on `load_term_enrollments` (per-term course enrollment, already campus-aware) and `forecast_ols` (season-aware trend; level fallback for a single point). Uses `_FOUN_CURRICULUM_START` for the post-rollout cutoff and `resolve_term_info`/term-code helpers for the season math.
- **`api/main.py` `run_forecast` method switch.** Resolve the method from `request.method` or the config `method` key, defaulting to `historical`. `historical` → `run_sameseason_forecast`; `sequence` → the existing `run_sequence_forecast` (+ ratio fallback). Adjustments, anomaly flags, the scenario layer, the buffer, and the previous-forecast delta all continue to apply to the chosen method's rows.
- **Config:** add `"method": "historical"` to `forecast_config.json`. `ForecastRequest.method` becomes `'historical' | 'sequence'` (default `historical`).
- **Frontend:** `useChat` (the Run Forecast button and chat path) sends `method: 'historical'` (or omits it to take the backend default) instead of the current `'sequence'`. An optional sidebar toggle to pick the method is a nice-to-have, not required for v1.

## 5. Data requirement + guardrail

The historical method needs the **prior year's same quarter** in the imported Master Schedule (to forecast Fall 2026, include Fall 2025). If no FOUN enrollment is found for any prior same-season term, return a 422 naming the missing term, mirroring the existing no-feeder guardrail: *"No same-season history found to forecast {target}. Import a Master Schedule that includes {prior same-season term, e.g. Fall 2025}."* This replaces the "two prior quarters" requirement when the historical method is active.

## 6. New courses

A FOUN `(course, campus)` offered in the target term but with no post-rollout same-season history (e.g., one the committee just added) cannot be projected from data. When the target term's schedule is present in the imported file, such courses are returned with `projected_seats = 0` and a flag ("new course — no history; set a manual estimate"); the admin supplies a value through the existing adjustment mechanism. When the target schedule is not in the import, new courses simply do not appear, which is acceptable until they have a year of data.

## 7. Non-goals

- Do not delete the sequence map or its engine; keep it selectable.
- No built-in decline/haircut (scenarios cover that).
- No full OLS/ETS/ARIMA ensemble for the primary path; the season-aware OLS (with level fallback) is sufficient for the current one-year-of-data reality and grows into a trend automatically.
- No multi-year trend before the data exists; the rule auto-upgrades from level to trend as post-rollout same-season terms accumulate.

## 8. Testing

- `run_sameseason_forecast` unit tests: level case (one same-season point), trend case (two points), post-rollout cutoff excludes old-curriculum terms, new-course flag, and empty/missing same-season history.
- API test: `method` selection (default historical, explicit sequence) and the missing-same-season 422 guardrail.
- Keep the existing sequence and ratio tests green (sequence remains a supported method).

## 9. Risks and open items

- **`forecast_ols` interface.** Confirm its exact input/return and that a single point yields a level (not an error); the plan will pin this against the real function before relying on it.
- **New-course detection** depends on whether the target term's schedule is in the import; the plan will define exactly how the candidate course set is derived (target-term FOUN courses present in the file vs. those with history).
- **Term-code/season math** must handle the Fall academic-year offset (Fall 2026 = `202710`, prior Fall 2025 = `202610`); reuse existing helpers and cover with tests.

## 10. Rough sequencing

1. `run_sameseason_forecast` + unit tests (level, trend, cutoff, new-course, guardrail).
2. Wire the method switch into `run_forecast` (default historical) + config key + API test.
3. Point the frontend (`useChat`) at the historical method; optional sidebar toggle.
4. Update the guardrail and docs (data requirement: prior-year same quarter); refresh `CLAUDE.md`/handoff.
