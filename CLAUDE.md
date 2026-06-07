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
6. **Cohort year filter** (`_active_curriculum_years` in `api/forecaster.py`): for any term at or after Fall 2025 (term code 202610), all four cohort labels (`First Year`, `Second Year`, `Third Year`, `Fourth Year`) are active simultaneously. The FOUN curriculum was a simultaneous-rollout, not phased — confirmed by PZSMSCP Spring 2026 ACT actuals showing FOUN 250/251/260 enrollment that cannot exist under a phased First-Year-only model. Pre-curriculum terms (before Fall 2025) return `None` to disable the filter for historical backtests.

### Legacy Code Crosswalk

Historical data uses old course codes (DRAW, DSGN) that map to current FOUN codes. The crosswalk CSV (`Data/sequence_crosswalk_template.csv`) handles `DSGN 100 → FOUN 110`, `DRAW 200 → FOUN 230`, etc. Applied in both sequence and ratio forecasting via `load_crosswalk()`.

### Ratio-Based Forecasting (Fallback)

Used when sequencing map has no data for a target quarter (Summer):
- Computes historical `target_enrollment / feeder_enrollment` ratios per course
- Applies ratios to closest feeder quarter's forecast CSV
- Default ratio: `0.12` when insufficient data

### Campus Detection

- **Sequencing map**: `campus` column; `"GENERAL"` applies to all campuses. Multi-campus rows use `|` as separator (e.g., `Savannah | Atlanta | SCADnow`). The forecaster groups by `(program, degree, campus, year)` per row independently — different year rows for the same program may carry different campus tags without affecting consistency.
- **Enrollment data**: Campus resolved via `_normalize_campus_label()` (free-text: "SCADnow online", "scadnow", "online", "now" → SCADNOW) or `_normalize_campus_code()` (Master Schedule CAMPUS column: SAV/NOW/ATL). Both helpers defined in `api/forecaster.py`. Room `OLNOW` and section prefix `N` remain as fallback when no Campus column is present.
- **Open issue (May 5, 2026 mechanical-fix sprint)**: campus expansion from `Savannah` to `Savannah | SCADnow` on First-Year seq-map rows produces only ~10 students of NOW demand for the newly-tagged target courses (FOUN 230 NOW = 10.5 vs ACT 37; FOUN 240 NOW = 10.5 vs ACT 64). Root cause unconfirmed — may be a disconnect between the seq-map campus tag and the CRN-level Master Schedule lookup that excludes programs not historically tagged for that campus. Worth a future-sprint diagnostic.

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

Provider: **Anthropic** (`claude-haiku-4-5-20251001`), optional (the regex `SimpleCommandParser` runs when no key is set). The key is stored in `settings.json` under the app-data directory resolved by `api/paths.py` (the project root in dev, the OS app-data folder when packaged), not in `.env.local`. Configure via the AI Assistant section in the Config sidebar, never via the terminal (would expose the key in shell history). To rotate: revoke at console.anthropic.com, then re-enter through the UI.

`GET /api/llm/status` returns `configured: true/false` and `has_key: bool` — never the key itself.

## Data Access Constraints

The end user has **read access to one Cognos report only**: the **PZSMSCP — Flexible Master Schedule of Classes with Power Prompts** export. This is the sole institutional data source the production tool consumes.

- **Master Schedule (PZSMSCP)** — drop the xlsx export at `Data/Master Schedule of Classes.xlsx`. The loader (`load_term_enrollments` in `api/forecaster.py`) auto-dispatches by file extension and handles the Cognos quirks: 16 rows of metadata before the header, multiple rows per CRN (one per instructor) which the loader dedupes by CRN before summing `ACT ENR`. CSV exports of the same report continue to work.
- **By-major weighting (DISABLED in production)** — the prior `enrollment_by_major.xlsx` weighting feature requires student-level enrollment-by-major data the end user does not have access to (FERPA / role constraint). `forecast_config.json` ships with `"enrollmentByMajorFile": null`. The loader (`load_enrollment_by_major`) and crosswalk (`_COGNOS_TO_SEQ_PROGRAMS`) are preserved for development / testing and may be re-enabled if/when an aggregated by-major report becomes available.
- **Admits demand (PZSAAPF-SL31)** — accepted-applicants report. Already wired via `admitsFile`. Loaded by `load_admits_foun_demand`.
- **Manual adjustments** — per-term `set` adjustments in `Data/adjustments/<term>.json` are reserved for overriding model output against **measured ground truth (ACT enrollment from PZSMSCP)**, not against another forecaster's planning projection. Calibrating to a projection propagates that projection's error and masks model bias; see `Data/adjustments/README.md` for the policy. Directory is gitignored; commit a template into `Data/adjustments/` only as a reference copy. As of 2026-05-05 the Spring 2026 template is empty (prior overrides removed after PZSMSCP backtest — see `docs/SPRING_2026_BACKTEST.md`).
- **`Data/clon_sav_atl_seat_projection_202630_20260107.xlsx`** — Jan 2026 SCAD planning **projection**, NOT actual demand. Useful as a "what was originally projected" reference when comparing the model to historical planning numbers. For backtesting accuracy, always use PZSMSCP `ACT ENR` counts as ground truth instead.

## Current State & Known Gaps

- Test framework in place (pytest + Vitest). Windows installer CI added (`.github/workflows/build-windows.yml`); no test-running CI yet.
- Backend suite green: **535 passing, 0 failing** (frontend 144). The former 2 ratio-fallback failures were a real production bug, fixed 2026-06-06: a redundant local `resolve_term_info` import in `run_forecast` caused `UnboundLocalError` on the Summer ratio-fallback path (swallowed into a 500, so every Summer forecast failed).
- `prophet` and `plotly` removed from `requirements.txt`; `forecast_tool/forecasting/prophet_forecast.py` deleted (Prophet was unused on the production path and blocked Windows installs). The ensemble's `"prophet"` dict keys are retained as labels only.
- `.venv/` may have broken symlinks after Python upgrades; recreate with `python3 -m venv .venv`
- `Data/adjustments/` is gitignored — fresh worktrees show raw forecast numbers (no manual `set` overrides applied)
- Per-term CLI scripts (`forecast_spring26_from_sequence_guides.py`, `forecast_fall26_from_sequence_guides.py`, `forecast_summer26_foun.py`) retired to the gitignored `deprecated/` folder (drifted from `api/forecaster.py`: missing year filter, enrollment weights, legacy crosswalk, ATLANTA, admits demand). Forecast via the desktop app or `POST /api/forecast`.
- `_COGNOS_TO_SEQ_PROGRAMS` maps 34 of 46 Cognos codes; 12 unmapped codes are now logged via `logging.warning` (was silent). Mapping decisions moot in production (Cognos by-major weighting disabled — see "Data Access Constraints" above).
- PZSMSCP xlsx loader added to `load_term_enrollments` / `get_available_terms` (auto-dispatch on file extension; dedupes co-taught rows by CRN). End-user input is now exclusively the PZSMSCP Cognos export.

## Desktop App Packaging (v1)

Packaged as an offline double-click desktop app for macOS (`.dmg`) and Windows (`.exe`) via **PyInstaller + pywebview**. One Python process starts FastAPI on a local port, serves the static Next.js export and the API same-origin, and opens a native webview window (`desktop/app.py`).

- **`api/paths.py`** resolves writable vs. read-only locations. In dev everything is under the project root (tests unchanged). When frozen, writable state (config, `Data/`, adjustments, outputs, the `settings.json` key store) lives in the OS app-data folder (`~/Library/Application Support/SCAD Forecast Tool/` on macOS, `%APPDATA%\SCAD Forecast Tool\` on Windows), and read-only seed files live in the bundle. `ensure_seeded()` copies bundled seeds (`build/seed/`, `build/seed_config/`) into app-data on first run.
- **Frontend** builds with `output: 'export'` and `NEXT_PUBLIC_API_URL=''` (same-origin relative calls; `lib/api.ts` uses `??` not `||`). No Node at runtime. The frontend uses **pnpm** (`package-lock.json` removed).
- **In-app import**: `POST /api/data/import` plus an "Import Master Schedule…" button copy the chosen PZSMSCP export into `DATA_DIR` through the pywebview native file dialog (`_Bridge` in `desktop/app.py`).
- **Build pipeline**: `build/forecast_tool.spec` (PyInstaller), `build/build_mac.sh` to `.dmg` via dmgbuild, `.github/workflows/build-windows.yml` to `.exe` via Inno Setup (`build/installer.iss`). Desktop toolchain in `requirements-desktop.txt` (pywebview, pyinstaller).
- **Not in v1**: code signing (Gatekeeper/SmartScreen show a one-time unsigned warning, documented in `docs/HANDOFF_GUIDE.md`), auto-update, bundled local LLM, Intel-Mac build (arm64 only).
- **Status**: code complete on branch `feat/desktop-packaging` (535 backend / 144 frontend green). The installer builds (PyInstaller, dmg, Windows CI) and the GUI smoke test still need to run on real Mac and Windows machines. Design and plan: `docs/superpowers/specs/2026-06-06-desktop-packaging-design.md`, `docs/superpowers/plans/2026-06-06-desktop-packaging.md`.

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

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
