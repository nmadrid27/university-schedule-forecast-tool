# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**UPDATE RULE**: Always update this file and `MEMORY.md` at the end of every interaction to reflect any changes made to the project (new files, modified architecture, resolved issues, new decisions, etc.). Keep both in sync with reality.

## Overview

SCAD FOUN Enrollment Forecasting Tool — forecasts foundation course section needs at Savannah College of Art and Design. Three-tier architecture: Next.js React frontend, FastAPI backend, and Python forecasting engine. Packaged for delivery to non-technical macOS users with double-clickable launcher scripts.

## Commands

### Full-Stack Launch (recommended)

```bash
# One-time setup (installs Homebrew, Python, Node, venv, npm deps)
./install.command

# Start both backend + frontend, opens browser (auto-checks for updates)
./Forecast_Tool_Launcher.command

# Start without auto-update check
./Forecast_Tool_Launcher.command --no-update

# Pull latest code + update dependencies
./update.command

# Stop both servers
./stop.command
```

### Frontend (Next.js)

```bash
cd frontend
npm install          # install dependencies
npm run dev          # dev server at http://localhost:3000
npm run build        # production build
npm run lint         # ESLint
```

If Turbopack corrupts the build cache ("Failed to open database"):
```bash
rm -rf frontend/.next
npm run dev
```

### FastAPI Backend

```bash
source .venv/bin/activate
cd api
python3 main.py       # starts at http://localhost:8000
```

### Python CLI Forecasting

```bash
source .venv/bin/activate
python3 forecast_spring26_from_sequence_guides.py --config forecast_config.json
```

## Architecture

The system has three layers that can operate independently:

### 1. Next.js Frontend (`frontend/`)

Single-page app with a 3-panel layout defined in `frontend/src/app/page.tsx`:
- Left: `HistorySidebar` — conversation history
- Center (40%): `ChatWindow` — chat-based interaction with the forecasting engine
- Right (60%): `ResultsPanel` — forecast tables, metrics cards, charts
- Right overlay: `ConfigSidebar` — capacity, buffer, progression rate controls

Component domains: `components/chat/`, `components/results/`, `components/sidebar/`, `components/ui/` (Shadcn/ui primitives).

State management is in `hooks/useChat.ts` — returns **mock responses** when the backend is unavailable. The API client (`lib/api.ts`) targets `http://localhost:8000` (configurable via `NEXT_PUBLIC_API_URL`).

Stack: Next.js 16.1.6, React 19, Tailwind CSS 4, Radix UI, TypeScript 5.

### 2. FastAPI Backend (`api/main.py`)

Bridges the frontend to Python forecasting logic. Single-file API (770+ lines) with real forecasting wired in via `api/forecaster.py`:

- `GET /api/health` — health check
- `POST /api/chat` — parses user messages via `SimpleCommandParser` (regex-based intent classification)
- `POST /api/forecast` — runs real sequence-based forecast with ratio-based fallback for terms without sequencing data (e.g., Summer)
- `GET /api/terms` — lists available + forecastable terms from Master Schedule
- `GET/PUT /api/config` — reads/writes `forecast_config.json`
- `GET /api/data/files` — lists CSV/XLSX files in `Data/`
- `POST /api/forecast/ensemble` — runs 3-model ensemble (Prophet+ETS+ARIMA) on historical data with optional weight optimization
- `GET /api/diagnostics` — ADF stationarity tests + seasonal strength diagnostics

CORS configured for localhost:3000.

### 3. Python Forecasting Engine

**`api/forecaster.py`** — Pure functions for any-term forecasting (generalized from CLI scripts):
- `run_sequence_forecast()` — primary method using sequencing guides
- `run_ratio_forecast()` — fallback using historical enrollment ratios
- `resolve_term_info()` — parses term strings, resolves feeder term codes
- `load_previous_forecast()` — reads existing CSVs for change delta comparison

**Production CLI scripts** (standalone, argparse-based):
- `forecast_spring26_from_sequence_guides.py` — PRIMARY production script
- `forecast_fall26_from_sequence_guides.py` — Fall term variant
- `forecast_spring26_from_seat_projection.py` — alternate methodology
- `calculate_foun_demand.py` — FOUN demand calculator
- `forecast_summer26_foun.py` — Summer term forecaster

**Reusable package** (`forecast_tool/`):
- `forecasting/prophet_forecast.py` — Facebook Prophet time series model
- `forecasting/ets_forecast.py` — Exponential Smoothing (statsmodels)
- `forecasting/arima_forecast.py` — ARIMA with cascading fallbacks: (1,1,1) → (1,1,0) → (0,1,1) → naive mean
- `forecasting/ensemble.py` — 3-model weighted ensemble (40/35/25 default), `optimize_ensemble_weights()` via grid search + temporal CV, `calculate_sections()`
- `validation/temporal_cv.py` — expanding-window temporal cross-validation (MAPE, RMSE, MAE)
- `diagnostics/stationarity_test.py` — ADF stationarity test + seasonal strength measurement
- `data/loaders.py` — CSV/Excel loading, course mapping, term code parsing
- `data/transformers.py` — quarter/date conversions
- `config/settings.py` — default configuration values
- `chat/` and `ui/` — Streamlit-era modules (legacy)

## Forecasting Logic

### Primary: Sequence-Based

1. **Sequencing guide** (`Data/FOUN_sequencing_map_by_major.csv`) maps prerequisite courses → target FOUN courses, organized by major and campus
2. **"CHOICE" entries** split demand evenly across listed course options (`1/N` weighting)
3. **Campus detection**: SCADnow = room `OLNOW` or section starts with `N`; Master Schedule uses `CAMPUS` column (`SAV`/`NOW`)
4. **Progression rate** applied per term gap: e.g., Fall→Spring = 0.95² (2 transitions), Winter→Spring = 0.95¹
5. **Section calculation**: `ceil(projected_seats / capacity)`, default capacity = 20

### Fallback: Ratio-Based

When the sequencing map has no data for a target quarter (e.g., Summer):
- Computes historical `target_enrollment / feeder_enrollment` ratios per course
- Applies ratios to the closest feeder quarter's existing forecast CSV
- Default ratio: 0.12 when insufficient historical data

### Alternative: 3-Model Ensemble

For time-series-based forecasting on historical data:
- Prophet (40%), ETS (35%), ARIMA (25%) default weights
- NaN-safe weight redistribution when a model fails
- Optional weight optimization via grid search (5% increments) over temporal CV
- Requires 4+ quarters of historical data per course

Configuration lives in `forecast_config.json`. SCAD term codes use `YYYYQQ` format: `202610`=Fall 2025, `202620`=Winter 2026, `202630`=Spring 2026, `202640`=Summer 2026.

## Key Data Files

All in `Data/` directory:
- `FOUN_sequencing_map_by_major.csv` — **CRITICAL**: drives the primary forecasting methodology
- `Master Schedule of Classes.csv` (9.2MB) — complete term schedule with enrollment actuals
- `FAll25.csv`, `Winter26.csv` — current term enrollment snapshots
- `FOUN_Historical.csv` — multi-year historical data for time series models
- Output forecasts: `Spring_2026_FOUN_Forecast_*.csv`, `Summer_2026_FOUN_Forecast.csv`, `Fall_2026_FOUN_Forecast_*.csv`

## Launcher Scripts

| Script | Purpose |
|--------|---------|
| `install.command` | One-time setup: Homebrew, Python 3.11+, Node 18+, `.venv`, `npm install` |
| `Forecast_Tool_Launcher.command` | Starts backend (port 8000) + frontend (port 3000), auto-update check, health checks, opens browser, cleanup on exit. Pass `--no-update` to skip update check. |
| `update.command` | Pulls latest code from GitHub, updates Python and Node dependencies. Safe to run anytime. |
| `stop.command` | Kills processes on ports 3000 and 8000 |
| `SCAD Forecast Tool.app` | Minimal macOS app bundle — runs the launcher. Drag to Dock for one-click access. |

## Documentation

| File | Audience |
|------|----------|
| `README.md` | Quick start + feature overview |
| `docs/HANDOFF_GUIDE.md` | Non-technical user guide (setup, usage, troubleshooting, FAQ) |
| `docs/DEVELOPMENT_HISTORY.md` | Technical build chronicle (4 phases) |

## Python Environment

- Python 3.14.2 via Homebrew (Apple Silicon)
- Virtual env: `.venv/` at project root
- All deps in unified `requirements.txt` (fastapi, uvicorn, pydantic, prophet, statsmodels, pandas, numpy, openpyxl, plotly)
- `api/requirements.txt` references root via `-r ../requirements.txt`
- Streamlit removed; deprecated interfaces archived in `deprecated/`

## Current State & Known Gaps

- `/api/forecast` is wired to real forecasting logic (sequence-based + ratio fallback)
- `hooks/useChat.ts` has mock responses as fallback when backend is unavailable
- No test suites (no test framework configured)
- No CI/CD pipeline
- Streamlit interfaces archived in `deprecated/`

## Code Standards

- **Python**: PEP 8, 4-space indentation
- **TypeScript/JS**: ESLint (Next.js core-web-vitals + TypeScript rules), 2-space indentation
- **Commits**: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`)
- **Path alias**: `@/*` maps to `frontend/src/*` in TypeScript
