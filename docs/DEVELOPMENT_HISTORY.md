# Development History

Complete build chronicle of the SCAD FOUN Enrollment Forecasting Tool, organized by development phase.

---

## Phase 1: Foundation — CLI Forecasting Engine

**Goal:** Build the core forecasting logic as standalone Python CLI scripts that SCAD staff can run from the terminal.

### Files Created

| File | Purpose |
|------|---------|
| `forecast_spring26_from_sequence_guides.py` | Primary production script (326 lines). Reads sequencing guides + enrollment CSVs, outputs Spring 2026 section forecasts. |
| `forecast_fall26_from_sequence_guides.py` | Fall 2026 variant of the sequence-based forecaster |
| `forecast_spring26_from_seat_projection.py` | Alternate methodology using seat projections instead of sequence guides |
| `calculate_foun_demand.py` | FOUN demand calculator for quick demand estimates |
| `forecast_config.json` | Externalized configuration (capacity, progression rate, data paths) |
| `Data/FOUN_sequencing_map_by_major.csv` | Core data: maps Fall/Winter prerequisites to target Spring FOUN courses, by major |
| `Data/Master Schedule of Classes.csv` | 9.2MB complete schedule with enrollment actuals across all terms |
| `Data/FAll25.csv`, `Data/Winter26.csv` | Current-term enrollment snapshots |
| `Data/FOUN_Historical.csv` | Multi-year historical enrollment data for time series models |

### Design Decisions

- **Sequence-based methodology** chosen as primary approach because SCAD's major sequencing guides provide direct prerequisite-to-FOUN mappings, making them more reliable than pure time series for course-level forecasts.
- **CHOICE handling**: When a sequencing guide lists multiple course options (e.g., "FOUN 110 OR FOUN 120"), demand splits evenly across options using `1/N` weighting.
- **Campus detection**: SCADnow sections identified by room `OLNOW` or section numbers starting with `N`; Master Schedule uses explicit `CAMPUS` column (`SAV`/`NOW`).
- **Progression rate**: Applied per term gap — Fall-to-Spring = `0.95^2` (two transitions), Winter-to-Spring = `0.95^1`.
- **Section calculation**: `ceil(projected_seats / capacity)`, default capacity = 20 students.
- **Term code format**: SCAD uses `YYYYQQ` where `10`=Fall, `20`=Winter, `30`=Spring, `40`=Summer. Academic year starts with Fall (Fall 2025 = `202610`).
- **Config externalization**: `forecast_config.json` keeps capacity, progression_rate, and data file paths outside code so users can adjust without editing Python.

### Reusable Package (`forecast_tool/`)

Extracted core logic into importable modules:

| Module | Purpose |
|--------|---------|
| `forecast_tool/data/loaders.py` | CSV/Excel loading, course mapping, term code parsing |
| `forecast_tool/data/transformers.py` | Quarter-to-date conversions |
| `forecast_tool/config/settings.py` | Default configuration values |
| `forecast_tool/forecasting/prophet_forecast.py` | Facebook Prophet time series model |
| `forecast_tool/forecasting/ets_forecast.py` | Exponential Smoothing (statsmodels) |
| `forecast_tool/forecasting/ensemble.py` | Weighted ensemble + section calculation |

---

## Phase 2: Frontend + API — Web Interface

**Goal:** Build a chat-based web UI so non-technical users can interact with the forecasting engine through natural language.

### Files Created

**FastAPI Backend (`api/`):**

| File | Purpose |
|------|---------|
| `api/main.py` | Single-file API server (770+ lines). Routes for chat, forecast, terms, config, ensemble, diagnostics |
| `api/forecaster.py` | Pure functions extracted from CLI scripts. Generalized to forecast any target quarter. Contains `run_sequence_forecast()`, `run_ratio_forecast()`, term resolution, and historical ratio computation |
| `api/requirements.txt` | Backend-specific Python dependencies |

**API Endpoints:**

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/chat` | Parse natural language via `SimpleCommandParser` (regex-based intent classification) |
| `POST` | `/api/forecast` | Run real sequence-based forecast for any term, with ratio-based fallback |
| `GET` | `/api/terms` | List available + forecastable terms from Master Schedule |
| `GET/PUT` | `/api/config` | Read/write `forecast_config.json` |
| `GET` | `/api/data/files` | List CSV/XLSX files in `Data/` |
| `POST` | `/api/forecast/ensemble` | Run 3-model ensemble (Prophet+ETS+ARIMA) on historical data |
| `GET` | `/api/diagnostics` | Stationarity + seasonality diagnostics for all FOUN courses |

**Next.js Frontend (`frontend/`):**

| File | Purpose |
|------|---------|
| `frontend/src/app/page.tsx` | 3-panel layout: HistorySidebar (left), ChatWindow (40% center), ResultsPanel (60% right) |
| `frontend/src/app/layout.tsx` | Root layout with dark theme |
| `frontend/src/hooks/useChat.ts` | State management with mock response fallback when backend unavailable |
| `frontend/src/lib/api.ts` | API client targeting `localhost:8000` (configurable via `NEXT_PUBLIC_API_URL`) |
| `frontend/src/lib/types.ts` | TypeScript types for forecasts, config, messages |
| `frontend/src/components/chat/ChatWindow.tsx` | Chat message display area |
| `frontend/src/components/chat/ChatInput.tsx` | Message input with send button |
| `frontend/src/components/chat/MessageBubble.tsx` | Individual message rendering |
| `frontend/src/components/results/ResultsPanel.tsx` | Forecast results display with download/compare actions |
| `frontend/src/components/results/DataTable.tsx` | Tabular forecast data display |
| `frontend/src/components/results/MetricsCards.tsx` | Summary metric cards (total students, sections, courses) |
| `frontend/src/components/sidebar/HistorySidebar.tsx` | Conversation history panel |
| `frontend/src/components/sidebar/ConfigSidebar.tsx` | Capacity, buffer, progression rate controls |
| `frontend/src/components/ui/*.tsx` | Shadcn/ui primitives (button, card, table, input, etc.) |

### Design Decisions

- **Chat-based interface**: Chose conversational UI over traditional forms to make the tool approachable for non-technical users.
- **3-panel layout**: Mirrors analytics dashboards — history on left, conversation in center, results on right. Config sidebar overlays the right panel.
- **`SimpleCommandParser`**: Regex-based intent classification (forecast, help, settings, upload, compare) instead of LLM-based parsing, keeping the tool self-contained without AI API dependencies.
- **Mock fallback**: `useChat.ts` returns comprehensive mock responses when the backend is unavailable, enabling frontend development independent of the backend.
- **Single-file API**: `api/main.py` keeps all routes in one file for simplicity. The backend is thin — it delegates to `forecaster.py` and `forecast_tool/` for actual computation.
- **CORS**: Configured for `localhost:3000` to allow frontend development.
- **Stack**: Next.js 16.1.6, React 19, Tailwind CSS 4, Radix UI, TypeScript 5.

---

## Phase 3: Summer 2026 Fix — Ratio-Based Fallback

**Goal:** Handle terms where the sequencing map has no data (Summer has no sequencing guide entries) by computing historical enrollment ratios.

### Files Created/Modified

| File | Change |
|------|--------|
| `api/forecaster.py` | Added `run_ratio_forecast()`, `_compute_historical_ratios()`, `load_previous_forecast()` |
| `api/main.py` | Added fallback logic in `/api/forecast`: when sequence-based returns empty, tries ratio-based using feeder quarter's forecast CSV |
| `forecast_summer26_foun.py` | Standalone Summer 2026 CLI forecaster |

### Design Decisions

- **Ratio method**: Computes `target_enrollment / feeder_enrollment` ratios from historical data, then applies to the feeder quarter's existing forecast. For example, Summer 2026 uses Spring 2026 forecast scaled by the historical Spring-to-Summer ratio.
- **Feeder CSV discovery**: Automatically finds the closest feeder quarter's forecast CSV using glob patterns (e.g., `Spring_2026_FOUN_Forecast*.csv`). Prefers "Sequence_Guides" output as most reliable.
- **Default ratio fallback**: Uses `0.12` when historical data is insufficient for a course (Summer enrollment is typically ~12% of Spring).
- **Change delta comparison**: `load_previous_forecast()` reads existing forecast CSVs to compute change percentages for the results panel.
- **Term auto-detection**: `/api/terms` now identifies forecastable terms by checking whether feeder data exists, including ratio-forecastable terms.

---

## Phase 4: Time-Series Enhancements — ARIMA, Cross-Validation, Diagnostics

**Goal:** Add a third forecasting model (ARIMA), temporal cross-validation for model evaluation, stationarity diagnostics, and expose these through the API.

### Files Created

| File | Purpose |
|------|---------|
| `forecast_tool/forecasting/arima_forecast.py` | ARIMA(1,1,1) with cascading fallbacks: ARIMA(1,1,0) then ARIMA(0,1,1) then naive mean |
| `forecast_tool/validation/temporal_cv.py` | Expanding-window temporal cross-validation. Generates train/test splits respecting chronological order, evaluates MAPE/RMSE/MAE per fold |
| `forecast_tool/diagnostics/stationarity_test.py` | Augmented Dickey-Fuller stationarity tests + seasonal decomposition (Hyndman & Athanasopoulos seasonal strength metric) |

### Files Modified

| File | Change |
|------|--------|
| `forecast_tool/forecasting/ensemble.py` | Upgraded from 2-model (60/40 Prophet/ETS) to 3-model ensemble. Added `DEFAULT_WEIGHTS` (40/35/25), `ensemble_forecast_weighted()`, `optimize_ensemble_weights()` via grid search over temporal CV, `_generate_weight_grid()`, NaN-safe weight redistribution |
| `api/main.py` | Added `POST /api/forecast/ensemble` and `GET /api/diagnostics` endpoints |

### Design Decisions

- **ARIMA cascading fallback**: ARIMA(1,1,1) is the default, falling back to simpler orders when convergence fails. Avoids crashing on short or noisy series.
- **3-model ensemble weights**: Default 40% Prophet, 35% ETS, 25% ARIMA. Prophet gets highest weight as it handles trends and seasonality best with limited data. ARIMA gets lowest as it's most sensitive to non-stationarity.
- **Weight optimization**: Grid search at 5% increments over all weight combinations summing to 1.0. Pre-computes per-model predictions for each CV fold, then evaluates ensemble combinations. Only runs when `optimize_weights=True` and sufficient data (10+ observations).
- **Temporal CV**: Expanding window (not sliding) to maximize training data. Default `min_train_size=8` (2 full cycles of quarterly data). Skips folds with all-NaN predictions rather than failing.
- **Stationarity diagnostics**: ADF test with 5% significance level. Seasonal strength via `1 - Var(residual) / Var(seasonal + residual)`. Helps users understand which courses are suitable for time series modeling.
- **API response sanitization**: Converts numpy types to Python natives for JSON serialization. Strips large array fields (seasonal components) from diagnostics API response to keep payloads manageable.

---

## Architecture Summary

```
                    User
                      |
              +-------+-------+
              |               |
         CLI Scripts     Web Browser
              |               |
              |        Next.js Frontend
              |         (localhost:3000)
              |               |
              |        FastAPI Backend
              |         (localhost:8000)
              |               |
              +-------+-------+
                      |
              Python Forecasting Engine
              (forecast_tool/ package)
                      |
              +-------+-------+
              |       |       |
           Prophet   ETS   ARIMA
              |       |       |
              +---+---+---+---+
                  |       |
             Ensemble  Diagnostics
                  |
              Data Layer
           (CSV files in Data/)
```

---

## Git History

| Commit | Description |
|--------|-------------|
| `4261e73` | Initial commit: University Schedule Forecast Tool |
| `e080e90` | fix: comprehensive code review fixes across backend, frontend, and CLI |
| `4bbf93e` | feat: add ratio-based forecasting fallback for Summer 2026 |
| `ad7e2dd` | fix: remove duplicate import and clean up ratio forecast logic |
| `7c0150d` | feat: add ARIMA model, temporal CV, diagnostics, and ensemble API endpoints |
