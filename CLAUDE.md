# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**UPDATE RULE**: Always update this file and `MEMORY.md` at the end of every interaction to reflect any changes made to the project (new files, modified architecture, resolved issues, new decisions, etc.). Keep both in sync with reality.

## Overview

SCAD FOUN Enrollment Forecasting Tool — forecasts foundation course section needs at Savannah College of Art and Design. Three-tier architecture: Next.js frontend, FastAPI backend, and Python forecasting engine. Packaged for non-technical macOS users with double-clickable launcher scripts.

## Commands

### Full-Stack (recommended)

```bash
./install.command                           # one-time setup (Homebrew, Python, Node, venv, npm)
./Forecast_Tool_Launcher.command            # start backend + frontend, auto-update, open browser
./Forecast_Tool_Launcher.command --no-update  # skip auto-update check
./update.command                            # pull latest code + update deps
./stop.command                              # kill servers on ports 3000/8000
```

### Frontend Only

```bash
cd frontend && npm install && npm run dev   # dev server at localhost:3000
npm run build                               # production build
npm run lint                                # ESLint
```

Turbopack cache corruption ("Failed to open database"): `rm -rf frontend/.next` then restart.

### Backend Only

```bash
source .venv/bin/activate && python3 api/main.py   # starts at localhost:8000
```

### CLI Forecasting

```bash
source .venv/bin/activate
python3 forecast_spring26_from_sequence_guides.py --config forecast_config.json
```

## Architecture

Three independent layers — each can run standalone:

### Data Flow: Frontend → Backend → Forecaster

1. User types a message in the chat UI (`frontend/src/components/chat/ChatWindow.tsx`)
2. `hooks/useChat.ts` sends it via `lib/api.ts` to `POST /api/chat` (with last 20 messages as history + current term)
3. `api/main.py`: if LLM configured → `llm_service.parse_message()` extracts intent + adjustments; else → `SimpleCommandParser` (regex fallback)
4. If LLM extracts adjustments → persisted to `Data/adjustments/{term}.json`
5. If intent is `forecast` or `adjust`, the frontend calls `POST /api/forecast`
6. `api/main.py` loads term adjustments → applies config-level before forecast → delegates to `api/forecaster.py` → applies output-level adjustments after
7. Results flow back with `adjusted` flags → `ResultsPanel` renders table + metrics + `AdjustmentBadges`

When the backend is unavailable, `useChat.ts` falls back to **mock responses** (hardcoded data).
When no LLM is configured, the regex `SimpleCommandParser` handles intent parsing (existing behavior preserved).

### Frontend (`frontend/`)

Single-page app: 3-panel layout in `frontend/src/app/page.tsx`:
- Left: `HistorySidebar` — conversation history
- Center (40%): `ChatWindow` — chat interface
- Right (60%): `ResultsPanel` — forecast tables, metrics cards
- Right overlay: `ConfigSidebar` — capacity, buffer, progression rate

Component barrel exports: `components/chat/index.ts`, `components/results/index.ts`, `components/sidebar/index.ts`. UI primitives in `components/ui/` (Shadcn/ui + Radix).

State: `hooks/useChat.ts` (messages, loading, forecast results), `hooks/useAdjustments.ts` (per-term adjustment CRUD). API client: `lib/api.ts` (targets `NEXT_PUBLIC_API_URL` or `localhost:8000`). Types: `lib/types.ts`, `lib/adjustments.ts`.

Stack: Next.js 16.1.6, React 19, Tailwind CSS 4, Radix UI, TypeScript 5. Path alias: `@/*` → `frontend/src/*`.

### Backend (`api/main.py`)

Multi-file FastAPI backend. Main server in `api/main.py` (~900 lines). CORS configured for `localhost:3000`.

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health` | Health check |
| `POST /api/chat` | LLM-powered parse (with regex fallback) — accepts `{message, history[], term}` |
| `POST /api/forecast` | Run sequence-based forecast (ratio fallback) with auto-applied adjustments |
| `GET /api/terms` | Available + forecastable terms from Master Schedule |
| `GET/PUT /api/config` | Read/write `forecast_config.json` |
| `GET /api/data/files` | List CSVs in `Data/` |
| `GET /api/adjustments/{term}` | List adjustments for a term |
| `POST /api/adjustments/{term}` | Add adjustment |
| `PUT /api/adjustments/{term}/{id}/toggle` | Toggle adjustment on/off |
| `DELETE /api/adjustments/{term}/{id}` | Remove adjustment |
| `GET /api/llm/status` | Check LLM configuration (never exposes API key) |
| `PUT /api/llm/config` | Update LLM provider/model/key |
| `POST /api/forecast/ensemble` | 3-model ensemble on historical data |
| `GET /api/diagnostics` | ADF stationarity + seasonal strength |

Supporting modules:
- `api/adjustments.py` — Pydantic adjustment models, JSON persistence (`Data/adjustments/`), config-level and output-level application
- `api/llm_service.py` — Provider-agnostic LLM client (OpenAI, Anthropic, Ollama, custom), system prompt builder, structured output parsing

### Forecasting Engine (`api/forecaster.py`)

Pure functions — no argparse, no sys.exit. Entry points:
- `run_sequence_forecast()` — primary method
- `run_ratio_forecast()` — fallback for terms without sequencing data (e.g., Summer)
- `resolve_term_info()` — parses "Spring 2026" into term codes + feeder terms
- `load_previous_forecast()` — reads existing CSVs for change delta comparison

The `forecast_tool/` package contains reusable time-series models (OLS, ETS, ARIMA), data loaders, and diagnostics. `forecast_tool/data/loaders.py` accepts an optional `data_dir` absolute path — callers in `api/main.py` pass `DATA_DIR` explicitly so no `os.chdir()` is needed.

## Domain Logic (SCAD-Specific)

### SCAD Term Codes

Format: `YYYYQQ` where QQ is `10`=Fall, `20`=Winter, `30`=Spring, `40`=Summer.

**Critical**: Fall uses `calendar_year + 1` for the academic year. Fall 2025 → term code `202610`. All other quarters: academic year = calendar year.

### Sequence-Based Forecasting (Primary)

1. `FOUN_sequencing_map_by_major.csv` maps prerequisite courses → target FOUN courses by major and campus
2. "CHOICE" entries split demand evenly (`1/N` weighting) across listed course options
3. Concurrent courses (co-requisites) use anchor selection to avoid double-counting
4. Progression rate `0.95` applied per term gap: Fall→Spring = `0.95²`, Winter→Spring = `0.95¹`
5. Section calculation: `ceil(projected_seats / capacity)`, default capacity = 20

### Legacy Code Crosswalk

Historical data uses old course codes (DRAW, DSGN) that map to current FOUN codes. The crosswalk CSV (`Data/sequence_crosswalk_template.csv`) handles `DSGN 100 → FOUN 110`, `DRAW 200 → FOUN 230`, etc. Applied in both sequence and ratio forecasting via `load_crosswalk()`.

### Ratio-Based Forecasting (Fallback)

Used when sequencing map has no data for a target quarter (Summer):
- Computes historical `target_enrollment / feeder_enrollment` ratios per course
- Applies ratios to closest feeder quarter's forecast CSV
- Default ratio: `0.12` when insufficient data

### Campus Detection

- **Sequencing map**: `campus` column; `"GENERAL"` applies to all campuses
- **Enrollment data**: Campus resolved via `_normalize_campus_label()` (free-text: "SCADnow online", "scadnow", "online", "now" → SCADNOW) or `_normalize_campus_code()` (Master Schedule CAMPUS column: SAV/NOW/ATL). Both helpers defined in `api/forecaster.py`. Room `OLNOW` and section prefix `N` remain as fallback when no Campus column is present.

### 3-Model Ensemble (Alternative)

OLS (40%), ETS (35%), ARIMA (25%) with NaN-safe weight redistribution. Optional weight optimization via grid search (5% increments) over temporal CV. Requires 4+ quarters of history. ARIMA fallback chain: `(1,1,1)` → `(1,1,0)` → `(0,1,1)` → naive mean. OLS replaced Prophet — no C-library dependencies, interpretable slope output, season-aware (trains only on same-season points).

### Anomaly Detection

`forecast_tool/forecasting/ols_forecast.py` — `detect_anomaly()` flags courses where the latest actual deviates >25% from the OLS trend. Uses leave-one-out validation when no `latest_actual` is supplied. Returns `flagged`, `deviation_pct`, `trend_yhat`, `actual`, and a human-readable `message`. Injected into `/api/forecast` response as `anomalyFlag` (only when `flagged=True`).

### Scenario Layer

`ForecastRequest` accepts `scenarios: List[{label, pct}]` (e.g. `[{"label":"conservative","pct":-9}]`). Each scenario result (`projectedSeats`, `sections`) is appended to the `ForecastResult` as `scenarios`. Computed after base forecast, before returning response.

## Key Data Files

All in `Data/`:
- `FOUN_sequencing_map_by_major.csv` — **drives primary forecasting**
- `Master Schedule of Classes.csv` (9.2MB) — all terms, enrollment actuals
- `FAll25.csv`, `Winter26.csv` — current term snapshots
- `FOUN_Historical.csv` — multi-year data for ensemble models
- `sequence_crosswalk_template.csv` — legacy→FOUN code mapping
- Output forecasts: `*_FOUN_Forecast_*.csv`

## Launcher & Distribution

| Script | Purpose |
|--------|---------|
| `install.command` | One-time: Homebrew, Python 3.11+, Node 18+, `.venv`, `npm install` |
| `Forecast_Tool_Launcher.command` | Full-stack launch with auto-update, health checks, browser open, cleanup trap. `--no-update` flag available. |
| `update.command` | `git pull` + `pip install` + `npm install`, osascript dialog on completion |
| `stop.command` | Kills ports 3000/8000 |
| `SCAD Forecast Tool.app` | macOS app bundle (thin shell wrapper) — must stay inside repo folder |

Distribution: Git repo with `.git/` for updates, or plain ZIP (update features degrade gracefully). Recipient: unzip → `install.command` → launch.

## Python Environment

- Python 3.14.2 via Homebrew (Apple Silicon)
- Virtual env: `.venv/` at project root
- Unified `requirements.txt` at root (includes `openai`, `anthropic` for LLM support); `api/requirements.txt` → `-r ../requirements.txt`

## LLM Configuration

Provider: **Anthropic** (`claude-haiku-4-5-20251001`). API key stored in `.env.local` (gitignored). Configure via the AI Assistant section in the Config sidebar — never via the terminal (would expose the key in shell history). To rotate: revoke at console.anthropic.com, then re-enter through the UI.

`GET /api/llm/status` returns `configured: true/false` and `has_key: bool` — never the key itself.

## Current State & Known Gaps

- No test suites or test framework
- No CI/CD pipeline
- `.venv/` may have broken symlinks after Python upgrades; recreate with `python3 -m venv .venv`

## Code Standards

- **Python**: PEP 8, 4-space indentation
- **TypeScript/JS**: ESLint (Next.js core-web-vitals + TypeScript), 2-space indentation
- **Commits**: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`)

## Documentation

| File | Audience |
|------|----------|
| `README.md` | Quick start + features |
| `docs/HANDOFF_GUIDE.md` | Non-technical user guide |
| `docs/DEVELOPMENT_HISTORY.md` | Technical build chronicle |
| `docs/PRD.md` | Product requirements (local only, not in git) |
| `AGENTS.md` | CLI production runbook |
