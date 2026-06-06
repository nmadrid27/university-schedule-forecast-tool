# Design: SCAD Forecast Tool as an Offline Cross-Platform Desktop App

- **Date:** 2026-06-06
- **Status:** Approved (design); pending implementation plan
- **Topic:** Package the existing three-tier forecasting tool into a double-click desktop installer for macOS and Windows.
- **Provenance:** Drafted collaboratively with Claude through the brainstorming process. All architectural and scope decisions are Nathan's; the four locked decisions below were made by explicit choice.

## 1. Goal

Ship the SCAD FOUN Enrollment Forecasting Tool as a desktop application a non-technical scheduling admin can install on either a Mac or a Windows PC, run fully offline, and use to forecast section needs each quarter. The admin should never touch Homebrew, Python, Node, or a terminal. Their data stays on their machine.

## 2. Locked decisions

1. **Delivery model: local desktop installer.** A double-click installer per OS (`.dmg` for Mac, `.exe` for Windows). Runs offline; data never leaves the machine.
2. **Forecasting stays deterministic.** The statistical and sequence-map engine produces all numbers. No LLM ever generates a forecast value. This is non-negotiable for auditability and defensibility.
3. **Chat input uses a rule-based parser.** The built-in parser handles the realistic commands. A Settings field lets an advanced user paste their own cloud API key to optionally enable free-form natural language. No model is bundled.
4. **Packaging: PyInstaller + pywebview.** One Python executable starts FastAPI (serving the API and the static UI on a single local port) and opens it in a native OS webview window. One language, smallest bundle, real app-window lifecycle.

### Recommended defaults (approved)

- **Windows build via GitHub Actions** Windows runner (no Windows machine required).
- **Manual re-install per update.** No auto-updater in v1.
- **Unsigned v1.** Document the Gatekeeper / SmartScreen workaround; signing is a v2 item.

## 3. Non-goals (explicitly deferred)

- Code signing and notarization (Apple Developer membership, Windows code-signing certificate).
- Auto-update.
- A bundled local LLM (e.g., Qwen/Llama via llama.cpp or Ollama).
- Intel-Mac / universal binary support, unless the admin is confirmed to be on an Intel Mac.
- Hosted/web-app delivery (rejected in favor of local install).

## 4. Current-state findings (verified 2026-06-06)

These motivate the pre-flight hardening in section 7.

- **Distribution is macOS-only.** `install.command`, `Forecast_Tool_Launcher.command`, `update.command`, `stop.command`, and `SCAD Forecast Tool.app` rely on Homebrew, `osascript`, `lsof`, and `open`. Nothing exists for Windows.
- **All write paths are anchored to the project/bundle root**, which is read-only once packaged:
  - `api/main.py:45-47` — `PROJECT_ROOT`, `CONFIG_PATH = PROJECT_ROOT/forecast_config.json`, `DATA_DIR = PROJECT_ROOT/Data`.
  - `api/main.py:275-278` — config writes to `CONFIG_PATH`.
  - `api/llm_service.py:18,41-54` — API key read from and written to `.env.local` at the project root.
- **Prophet is still a hard dependency** (`requirements.txt:10`, `forecast_tool/forecasting/prophet_forecast.py:8`, referenced by `ensemble.py`, `temporal_cv.py`, and tests) although the production forecaster does not use it. Prophet is the most common `pip install` failure on Windows (needs a C++/Stan toolchain) and bloats the bundle.
- **`plotly` (`requirements.txt:19`) is imported nowhere.**
- **2 failing tests, 528 passing** (`python -m pytest`), both in the Summer / ratio-fallback path of `/api/forecast`:
  - `test_forecast_falls_back_to_ratio_when_sequence_empty` — response is missing the `summary` key (`KeyError: 'summary'`).
  - `test_forecast_ratio_fallback_passes_target_term` — `target_term` is not threaded into `run_ratio_forecast` (asserts `None == 'Summer 2026'`).
- **Drifted CLI scripts** (`forecast_spring26_from_sequence_guides.py`, `forecast_fall26_from_sequence_guides.py`, `forecast_summer26_foun.py`) lag the API per project docs and should not ship.
- **Frontend is cleanly static-exportable:** App Router single-page app (`src/app/page.tsx`), 18 client components, no SSR data features, no `cookies()`/`headers()`, no Next route handlers. `next.config.ts` is empty (no `output` set). `src/lib/api.ts:3` reads `NEXT_PUBLIC_API_URL || 'http://localhost:8000'`. Dev script is `next dev -H 127.0.0.1` (`frontend/package.json`).

## 5. Target architecture

```
┌──────────────────────────────────────────────┐
│  PyInstaller executable (one process)          │
│                                                │
│   desktop/app.py  (entry point)                │
│     ├─ start uvicorn on 127.0.0.1:<port>       │
│     │    FastAPI serves:                       │
│     │      /api/*       → existing endpoints   │
│     │      /*           → static UI (out/)     │
│     └─ pywebview window → http://127.0.0.1:<port>/ │
│                                                │
│   App-data folder (user-writable, outside bundle) │
│     forecast_config.json, Data/, adjustments/, │
│     outputs, settings.json (optional key)      │
└──────────────────────────────────────────────┘
```

- **Single port, same origin.** FastAPI serves both the API and the static frontend, so the UI calls the API at a relative path. No CORS in packaged mode, no baked-in port. Port selection: try 8000, fall back to an OS-assigned free port if taken; pywebview is given the chosen port at runtime.
- **Lifecycle.** Closing the pywebview window stops uvicorn and exits the process. No stray servers, no `stop.command` needed.
- **No Node at runtime.** The frontend is pre-built to static files at package time.

## 6. Component design

### 6.1 `paths.py` (new) — writable data directory resolution

Single source of truth for where things live. Detects frozen (`getattr(sys, 'frozen', False)` / `sys._MEIPASS`) vs. dev.

- **Frozen:**
  - macOS: `~/Library/Application Support/SCAD Forecast Tool/`
  - Windows: `%APPDATA%\SCAD Forecast Tool\`
  - Exposes `APP_DATA`, `DATA_DIR = APP_DATA/Data`, `CONFIG_PATH = APP_DATA/forecast_config.json`, `SETTINGS_PATH = APP_DATA/settings.json`, and a `BUNDLE_DIR` for read-only resources (`sys._MEIPASS`).
- **Dev:** preserve today's project-root paths exactly, so tests and the existing dev workflow do not move.
- **First-run seeding:** copy bundled read-only seed files into `DATA_DIR` if absent: `FOUN_sequencing_map_by_major.csv`, `sequence_crosswalk_template.csv`, `FOUN_Historical.csv`, a default `forecast_config.json`, and an empty `adjustments/<term>.json` template. Never overwrite existing user data.

### 6.2 Backend refactor to consume `paths.py`

- `api/main.py`: replace the `PROJECT_ROOT`-relative `CONFIG_PATH` and `DATA_DIR` (`:45-47`) with values from `paths.py`. All existing `DATA_DIR` call sites stay as-is (they already take `DATA_DIR` explicitly).
- `api/llm_service.py`: move key persistence from `.env.local` (`:18,41-54`) to `SETTINGS_PATH` (`settings.json`) in app-data. Keep reading `LLM_API_KEY` from the environment as an override for dev. The key is never bundled.
- Add a static-file mount so FastAPI serves the built UI from `BUNDLE_DIR/web` (or `out/`) at `/`, after the API routes.

### 6.3 Frontend static export

- `frontend/next.config.ts`: add `output: 'export'`.
- Build with `NEXT_PUBLIC_API_URL=''` so `api.ts` issues same-origin relative requests in the packaged build. Dev keeps `http://localhost:8000`.
- Confirm no dynamic route or image-optimization feature blocks export (none found; verify after the config change).
- Package the resulting `out/` into the bundle.

### 6.4 `desktop/app.py` (new) — entry point

- Resolve a free port, start uvicorn in a background thread bound to `127.0.0.1`, wait for `/api/health` to pass, then open a pywebview window titled "SCAD Forecast Tool" at the local URL.
- On window close: signal uvicorn to stop, join the thread, exit.
- This module is the PyInstaller entry point.

### 6.5 In-app data import

- A native "Import Master Schedule…" action using pywebview's `create_file_dialog`. The chosen `.xlsx`/`.csv` is copied into `DATA_DIR` under the expected name. This is the primary, foolproof path for a non-technical user; the visible app-data folder is the fallback. Surfaced in the UI (e.g., Config sidebar or a header button) with a small backend endpoint to perform the copy and report the resolved data folder.

## 7. Pre-flight hardening

- **Remove Prophet.** Drop `prophet` from `requirements.txt`; retire `forecast_tool/forecasting/prophet_forecast.py` and its references in `ensemble.py`, `temporal_cv.py`, and the tests that import it. Risk: it is woven into the legacy ensemble interface and several tests, so this is careful surgery, not a blind delete. The plan must keep the ensemble/diagnostics endpoints working (they already use OLS/ETS/ARIMA) and keep the suite green.
- **Remove `plotly`** from `requirements.txt`.
- **Fix the 2 ratio-fallback failures** so Summer forecasts return a proper `summary` and `target_term` is threaded through `run_ratio_forecast`. These are real gaps on a path the quarterly tool uses.
- **Retire drifted CLI scripts** into the gitignored `deprecated/` folder so they neither ship nor mislead.
- **Pin versions** for reproducible builds: pin Python (target a stable 3.12 or 3.13 for PyInstaller compatibility rather than 3.14) and the core scientific libraries. Document the exact build interpreter.

## 8. Build pipeline

- **Mac (local, Apple Silicon):** `build/build_mac.sh` runs the frontend export, then PyInstaller via a checked-in `.spec`, producing `SCAD Forecast Tool.app`, packaged to `.dmg` with `dmgbuild`. Output is arm64-only for v1.
- **Windows (CI):** `.github/workflows/build-windows.yml` on a `windows-latest` runner builds the frontend, runs PyInstaller, and wraps the result with Inno Setup into a `.exe` installer published as a workflow artifact. No local Windows machine needed.
- **Shared `.spec`** parameterized per OS where practical; document the hidden-imports and data-file includes needed for pandas/numpy/statsmodels and the seed files.

## 9. Signing and first-run UX (deferred, documented)

v1 ships unsigned. The handoff guide gains exact steps: macOS "right-click → Open" to clear Gatekeeper once; Windows "More info → Run anyway" to clear SmartScreen once. Note signing as the v2 fix (Apple Developer at $99/yr, a Windows code-signing cert) because unsigned warnings cost adoption with non-technical users.

## 10. Testing and verification

- Keep `pytest` and Vitest green, including the two newly fixed tests and confirmation that Prophet removal breaks nothing.
- **Launch smoke test:** built app starts, `/api/health` passes, a Spring (sequence) and a Summer (ratio) forecast each return rows, and an import writes into the app-data folder.
- **Manual matrix:** a clean Mac and a clean Windows VM with no Python/Node preinstalled; run the installer, import a PZSMSCP export, run a forecast for the next quarter.

## 11. Risks and open questions

- **PyInstaller + scientific stack** (pandas/numpy/statsmodels) hidden imports can be fiddly. Mitigation: pin versions, use known PyInstaller hooks, and test the frozen build early in the plan, not at the end.
- **Windows WebView2 runtime** is present on Win11 and most updated Win10, but not guaranteed. Mitigation: the Inno Setup installer should detect and, if absent, install the WebView2 bootstrapper.
- **Prophet removal scope** could ripple into ensemble/CV tests. Mitigation: do it as an isolated, test-driven step.
- **Intel Mac:** v1 is arm64-only. Confirm the admin's Mac architecture; a universal2 build is possible later if needed.
- **Python version:** the live machine runs 3.14.4, but PyInstaller and the scientific stack are most reliable on 3.12/3.13. The build interpreter likely differs from the dev machine's default; pin it explicitly.

## 12. Rough sequencing

1. Pre-flight hardening (Prophet, plotly, the 2 tests, CLI retirement, version pinning) — leaves the suite green and the dependency set lean.
2. `paths.py` + backend refactor + static-export config + same-origin serving — app runs from a writable data dir in dev.
3. `desktop/app.py` + pywebview + first-run seeding + in-app import — app runs as a window.
4. PyInstaller `.spec` + `build_mac.sh` → working `.dmg`.
5. Windows CI workflow → working `.exe`.
6. Smoke tests, manual matrix, handoff-guide updates (install steps, Gatekeeper/SmartScreen, where data lives).
