# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

SCAD FOUN Enrollment Forecasting Tool — forecasts foundation course section needs at Savannah College of Art and Design. Two main interfaces: a Next.js React frontend and production CLI Python scripts.

## Commands

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
NEXT_PRIVATE_WEBPACK=1 npm run dev
```

### FastAPI Backend

```bash
cd api
pip install -r requirements.txt
python main.py       # starts at http://localhost:8000
```

### Python CLI Forecasting

```bash
source .venv/bin/activate
pip install -r requirements.txt

# Primary production forecast
python3 forecast_spring26_from_sequence_guides.py --config forecast_config.json
```

### One-Click Launcher (non-technical users)

Double-click `Forecast_Tool_Launcher.command` — installs deps, starts Next.js, opens browser.

## Architecture

The system has three layers that can operate independently:

### 1. Next.js Frontend (`frontend/`)

Single-page app with a 3-panel layout defined in `frontend/src/app/page.tsx`:
- Left: `HistorySidebar` — conversation history
- Center (40%): `ChatWindow` — chat-based interaction with the forecasting engine
- Right (60%): `ResultsPanel` — forecast tables, metrics cards, charts
- Right overlay: `ConfigSidebar` — capacity, buffer, progression rate controls

Component domains: `components/chat/`, `components/results/`, `components/sidebar/`, `components/ui/` (Shadcn/ui primitives).

State management is in `hooks/useChat.ts` — currently returns **mock responses** when the backend is unavailable. The API client (`lib/api.ts`) targets `http://localhost:8000` (configurable via `NEXT_PUBLIC_API_URL`).

Stack: Next.js 16.1.6, React 19, Tailwind CSS 4, Radix UI, TypeScript 5.

### 2. FastAPI Backend (`api/main.py`)

Bridges the frontend to Python forecasting logic. Single-file API with:
- `POST /api/chat` — parses user messages via `SimpleCommandParser` (regex-based intent classification)
- `POST /api/forecast` — **currently returns mock data** (not yet wired to real forecasting)
- `GET/PUT /api/config` — in-memory config management
- `GET /api/data/files` — lists CSV/XLSX files in `Data/`

CORS configured for localhost:3000. The forecast endpoint needs to be connected to the actual Python forecasting modules in `forecast_tool/`.

### 3. Python Forecasting Engine

**Production CLI scripts** (standalone, don't require the frontend or API):
- `forecast_spring26_from_sequence_guides.py` — PRIMARY production script (326 lines)
- `forecast_fall26_from_sequence_guides.py` — Fall term variant
- `forecast_spring26_from_seat_projection.py` — alternate methodology
- `calculate_foun_demand.py` — FOUN demand calculator

**Reusable package** (`forecast_tool/`):
- `forecasting/prophet_forecast.py` — Prophet time series model
- `forecasting/ets_forecast.py` — Exponential Smoothing (statsmodels)
- `forecasting/ensemble.py` — weighted ensemble + `calculate_sections(enrollment, capacity, buffer_pct)`
- `data/loaders.py` — CSV/Excel loading, course mapping, term code parsing
- `data/transformers.py` — quarter/date conversions
- `config/settings.py` — default configuration values
- `chat/` and `ui/` — Streamlit-era modules (legacy, used by deprecated interfaces)

## Forecasting Logic

The primary methodology is **sequence-based forecasting** (not time series):

1. **Sequencing guide** (`Data/FOUN_sequencing_map_by_major.csv`) maps Fall/Winter prerequisite courses → target Spring FOUN courses, organized by major
2. **"CHOICE" entries** split demand evenly across listed course options
3. **Campus detection**: SCADnow = room `OLNOW` or section starts with `N`; Master Schedule uses `CAMPUS` column (`SAV`/`NOW`)
4. **Progression rate** applied per term gap: Fall→Spring = 0.95² (2 transitions), Winter→Spring = 0.95¹
5. **Section calculation**: `ceil(projected_seats / capacity)`, default capacity = 20

Configuration lives in `forecast_config.json`. SCAD term codes use `YYYYQQ` format: `202610`=Fall 2025, `202620`=Winter 2026, `202630`=Spring 2026, `202640`=Summer 2026.

The Prophet + ETS **ensemble methodology** (in `forecast_tool/forecasting/`) is a separate approach: 60% Prophet weight, 40% ETS weight, with confidence intervals. Requires 4+ quarters of historical data per course.

## Key Data Files

All in `Data/` directory:
- `FOUN_sequencing_map_by_major.csv` — **CRITICAL**: drives the primary forecasting methodology
- `Master Schedule of Classes.csv` (9.2MB) — complete term schedule with enrollment actuals
- `FAll25.csv`, `Winter26.csv` — current term enrollment snapshots
- `FOUN_Historical.csv` — multi-year historical data for time series models
- Output forecasts: `Spring_2026_FOUN_Forecast_*.csv`, `Summer_2026_FOUN_Forecast.csv`

## Current State & Known Gaps

- The FastAPI `/api/forecast` endpoint returns **mock data** — not yet connected to real forecasting logic
- `hooks/useChat.ts` has **comprehensive mock responses** as fallback when backend is unavailable
- No test suites exist (no test framework configured)
- No CI/CD pipeline
- Streamlit interfaces (`app_chat.py`, `app.py`) are deprecated and archived in `deprecated/`

## Code Standards

- **Python**: PEP 8, 4-space indentation
- **TypeScript/JS**: ESLint (Next.js core-web-vitals + TypeScript rules), 2-space indentation
- **Commits**: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`)
- **Path alias**: `@/*` maps to `frontend/src/*` in TypeScript
