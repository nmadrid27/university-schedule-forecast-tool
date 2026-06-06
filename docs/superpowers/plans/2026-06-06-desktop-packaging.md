# Cross-Platform Desktop Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the SCAD FOUN Forecasting Tool as an offline, double-click desktop app for macOS and Windows, with all data stored in a user-writable folder.

**Architecture:** One PyInstaller executable starts FastAPI (serving both the API and the statically-exported Next.js UI on one local port) and opens it in a native pywebview window. All writable state (config, Data, adjustments, forecast outputs, optional API key) moves from the read-only bundle to an OS app-data folder. Pre-flight hardening removes Prophet (a Windows install blocker), fixes a real Summer-forecast bug, and leaves the test suite green before packaging starts.

**Tech Stack:** Python 3.12/3.13, FastAPI, uvicorn, pandas/numpy/statsmodels, pywebview, PyInstaller, Inno Setup (Windows), dmgbuild (macOS), Next.js 16 static export, GitHub Actions.

**Conventions:** Run backend tests from the project root with `source .venv/bin/activate && python -m pytest`. Commit after each task with Conventional Commits. Baseline before starting: 528 passing, 2 failing (the 2 failures are fixed in Task 1).

---

## Stage 0 — Pre-flight hardening

### Task 1: Fix the ratio-fallback `UnboundLocalError` (Summer forecasts)

A redundant `from forecaster import resolve_term_info` inside `run_forecast` (api/main.py:541) makes `resolve_term_info` a function-local name, so the earlier use at line 476 raises `UnboundLocalError` on the ratio-fallback path. This breaks every Summer forecast in production (swallowed into a generic 500) and is what the 2 failing tests catch.

**Files:**
- Modify: `api/main.py` (remove the redundant local import inside `run_forecast`)
- Test: `api/tests/test_forecast_api.py` (existing tests, already written)

- [ ] **Step 1: Run the two failing tests to confirm the failure**

Run: `source .venv/bin/activate && python -m pytest "api/tests/test_forecast_api.py::test_forecast_falls_back_to_ratio_when_sequence_empty" "api/tests/test_forecast_api.py::test_forecast_ratio_fallback_passes_target_term" -q`
Expected: FAIL — one `KeyError: 'summary'`, one `assert None == 'Summer 2026'`.

- [ ] **Step 2: Remove the redundant local import**

In `api/main.py`, inside `run_forecast`, find this block (around line 540):

```python
        try:
            from forecaster import resolve_term_info
            _info = resolve_term_info(target_term)
            _target_season = _info.get("target_quarter", "").capitalize()
        except Exception:
            pass
```

Delete the `from forecaster import resolve_term_info` line so it reads:

```python
        try:
            _info = resolve_term_info(target_term)
            _target_season = _info.get("target_quarter", "").capitalize()
        except Exception:
            pass
```

(`resolve_term_info` is already imported at module level, api/main.py:27.)

- [ ] **Step 3: Run the two tests to confirm they pass**

Run: `source .venv/bin/activate && python -m pytest "api/tests/test_forecast_api.py::test_forecast_falls_back_to_ratio_when_sequence_empty" "api/tests/test_forecast_api.py::test_forecast_ratio_fallback_passes_target_term" -q`
Expected: PASS (2 passed).

- [ ] **Step 4: Run the full backend suite to confirm no regressions**

Run: `source .venv/bin/activate && python -m pytest -q`
Expected: 530 passed (the 2 previously-failing now pass).

- [ ] **Step 5: Commit**

```bash
git add api/main.py
git commit -m "fix: remove redundant local import breaking Summer ratio-fallback forecasts"
```

---

### Task 2: Remove Prophet

Prophet is unused on the production path but is the most common `pip install` failure on Windows (needs a C++/Stan toolchain) and bloats the bundle. The only real dependency is `prophet_forecast.py`. The `"prophet"` strings in `ensemble.py`/`temporal_cv.py` are labels, not imports — leave them so `test_ensemble.py` and `test_temporal_cv.py` keep passing.

**Files:**
- Delete: `forecast_tool/forecasting/prophet_forecast.py`
- Modify: `forecast_tool/tests/test_forecasting_models.py` (remove the import and the `TestForecastProphet` class)
- Modify: `api/tests/test_advanced_api.py` (remove the 3 `forecast_prophet` patches)
- Modify: `requirements.txt` (remove `prophet`)

- [ ] **Step 1: Confirm Prophet is currently importable (baseline)**

Run: `source .venv/bin/activate && python -c "import forecast_tool.forecasting.prophet_forecast; print('prophet importable')"`
Expected: prints `prophet importable`.

- [ ] **Step 2: Delete the Prophet model module**

```bash
git rm forecast_tool/forecasting/prophet_forecast.py
```

- [ ] **Step 3: Remove the Prophet import and test class from `test_forecasting_models.py`**

In `forecast_tool/tests/test_forecasting_models.py`, delete line 21:

```python
from forecast_tool.forecasting.prophet_forecast import forecast_prophet
```

Then delete the entire `TestForecastProphet` class (the block starting at the `# ── forecast_prophet ──` comment near line 120 through the end of that class near line 178). Leave the ETS and ARIMA test classes intact.

- [ ] **Step 4: Remove the `forecast_prophet` patches from `test_advanced_api.py`**

In `api/tests/test_advanced_api.py`, remove all three occurrences of this 2-line patch (in `_patches()`, `test_returns_200`, and `test_response_has_results_and_summary`):

```python
            patch("forecast_tool.forecasting.prophet_forecast.forecast_prophet",
                  side_effect=self._mock_forecast_fn),
```

Leave the `load_historical_data`, `quarter_to_date`, `forecast_ets`, and `forecast_arima` patches in place (the ensemble endpoint uses OLS + ETS + ARIMA, not Prophet).

- [ ] **Step 5: Remove Prophet from requirements**

In `requirements.txt`, delete the line `prophet>=1.1.4`. The `# Forecasting models` section keeps `statsmodels>=0.14.0`.

- [ ] **Step 6: Verify the package imports without Prophet and the suite is green**

Run: `source .venv/bin/activate && python -c "import forecast_tool.forecasting.ensemble; import forecast_tool.validation.temporal_cv; print('ok')" && python -m pytest -q`
Expected: prints `ok`; full suite passes (count drops by the number of removed Prophet tests; 0 failures).

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: remove unused Prophet dependency (Windows install blocker)"
```

---

### Task 3: Remove the unused `plotly` dependency

`plotly` is in `requirements.txt` but imported nowhere.

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Confirm plotly is unused**

Run: `grep -rn "import plotly\|from plotly" --include="*.py" api forecast_tool | grep -v graphify-out || echo "plotly not imported"`
Expected: prints `plotly not imported`.

- [ ] **Step 2: Remove plotly from requirements**

In `requirements.txt`, delete the `# Visualization` comment and the `plotly>=5.18.0` line.

- [ ] **Step 3: Verify the suite still passes**

Run: `source .venv/bin/activate && python -m pytest -q`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: drop unused plotly dependency"
```

---

### Task 4: Retire drifted CLI scripts

The `forecast_*_from_sequence_guides.py` and `forecast_summer26_foun.py` scripts have drifted from the API and must not ship. Move them to the gitignored `deprecated/` folder (already in `.gitignore`).

**Files:**
- Move: `forecast_spring26_from_sequence_guides.py`, `forecast_fall26_from_sequence_guides.py`, `forecast_summer26_foun.py` → `deprecated/`

- [ ] **Step 1: Confirm nothing in the app imports these scripts**

Run: `grep -rn "forecast_spring26\|forecast_fall26\|forecast_summer26" --include="*.py" api forecast_tool | grep -v graphify-out || echo "no imports"`
Expected: prints `no imports`.

- [ ] **Step 2: Move the scripts into the gitignored deprecated folder**

```bash
mkdir -p deprecated
git mv forecast_spring26_from_sequence_guides.py deprecated/ 2>/dev/null || mv forecast_spring26_from_sequence_guides.py deprecated/
git mv forecast_fall26_from_sequence_guides.py deprecated/ 2>/dev/null || mv forecast_fall26_from_sequence_guides.py deprecated/
git mv forecast_summer26_foun.py deprecated/ 2>/dev/null || mv forecast_summer26_foun.py deprecated/
```

- [ ] **Step 3: Verify the suite still passes**

Run: `source .venv/bin/activate && python -m pytest -q`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: retire drifted CLI forecast scripts to deprecated/"
```

---

### Task 5: Pin runtime versions for reproducible builds

PyInstaller and the scientific stack are most reliable on Python 3.12/3.13, and the build must be deterministic. Pin the validated versions and add the desktop build tools.

**Files:**
- Modify: `requirements.txt`
- Create: `requirements-desktop.txt`

- [ ] **Step 1: Create a clean build venv on Python 3.13 and install current deps**

```bash
python3.13 -m venv .venv-build && source .venv-build/bin/activate && pip install --upgrade pip && pip install -r requirements.txt
```
Expected: installs cleanly (no Prophet, no Stan build).

- [ ] **Step 2: Pin the installed versions of the core libraries**

Capture the resolved versions:

```bash
source .venv-build/bin/activate && pip freeze | grep -iE "^(fastapi|uvicorn|pydantic|pandas|numpy|statsmodels|openpyxl|anthropic|openai|httpx)==" 
```
Edit `requirements.txt` to pin each of those to the exact `==` version printed. Keep `pytest`, `pytest-asyncio`, `httpx` for tests.

- [ ] **Step 3: Create the desktop build requirements**

Create `requirements-desktop.txt`:

```
# Desktop packaging toolchain (not needed to run the dev servers)
-r requirements.txt
pywebview==5.3.2
pyinstaller==6.11.1
```
(Use the latest stable `pywebview` and `pyinstaller` resolved by `pip install pywebview pyinstaller`; record the exact `==` versions from `pip freeze`.)

- [ ] **Step 4: Verify install and suite on the pinned set**

```bash
source .venv-build/bin/activate && pip install -r requirements-desktop.txt && python -m pytest -q
```
Expected: installs and all tests pass.

- [ ] **Step 5: Ignore build artifacts**

Append to `.gitignore` (the committed `build/seed` and `build/seed_config` stay tracked; only generated output is ignored):

```
# Desktop build artifacts
.venv-build/
.pyi-build/
dist/
/web/
frontend/out/
```

- [ ] **Step 6: Commit**

```bash
git add requirements.txt requirements-desktop.txt .gitignore
git commit -m "chore: pin runtime versions and add desktop build toolchain"
```

---

## Stage 1 — Writable data directory and same-origin serving

### Task 6: Create `api/paths.py`

Single source of truth for where files live, with frozen (packaged) vs. dev resolution.

**Files:**
- Create: `api/paths.py`
- Test: `api/tests/test_paths.py`

- [ ] **Step 1: Write the failing test**

Create `api/tests/test_paths.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import paths


def test_dev_mode_uses_project_root():
    # In dev (not frozen) app data is the project root, Data/ beneath it.
    assert paths.is_frozen() is False
    assert paths.data_dir() == paths.app_data_dir() / "Data"
    assert paths.config_path() == paths.app_data_dir() / "forecast_config.json"
    assert paths.settings_path() == paths.app_data_dir() / "settings.json"


def test_app_data_dir_is_project_root_in_dev():
    assert paths.app_data_dir() == Path(__file__).resolve().parent.parent


def test_bundle_dir_is_project_root_in_dev():
    assert paths.bundle_dir() == Path(__file__).resolve().parent.parent
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest api/tests/test_paths.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'paths'`.

- [ ] **Step 3: Implement `api/paths.py`**

```python
"""Filesystem path resolution for dev and packaged (frozen) runs.

In dev, everything resolves under the project root so tests and the existing
workflow are unchanged. When frozen by PyInstaller, writable state lives in an
OS-specific user app-data folder, and read-only seed files live in the bundle.
"""

import os
import shutil
import sys
from pathlib import Path

APP_NAME = "SCAD Forecast Tool"

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundle_dir() -> Path:
    """Read-only resources. In frozen mode this is the PyInstaller temp dir."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return _PROJECT_ROOT


def app_data_dir() -> Path:
    """Writable base directory. Project root in dev; OS app-data when frozen."""
    if not is_frozen():
        return _PROJECT_ROOT
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    target = base / APP_NAME
    target.mkdir(parents=True, exist_ok=True)
    return target


def data_dir() -> Path:
    return app_data_dir() / "Data"


def config_path() -> Path:
    return app_data_dir() / "forecast_config.json"


def settings_path() -> Path:
    return app_data_dir() / "settings.json"


def ensure_seeded() -> None:
    """Copy bundled read-only seed files into the writable data dir on first run.

    No-op in dev (the repo files are used directly). Never overwrites existing
    user data.
    """
    if not is_frozen():
        return
    dst = data_dir()
    dst.mkdir(parents=True, exist_ok=True)
    seed_root = bundle_dir() / "seed"
    if seed_root.is_dir():
        for src in seed_root.rglob("*"):
            if src.is_file():
                rel = src.relative_to(seed_root)
                out = dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                if not out.exists():
                    shutil.copy2(src, out)
    cfg = config_path()
    seed_cfg = bundle_dir() / "seed_config" / "forecast_config.json"
    if not cfg.exists() and seed_cfg.is_file():
        shutil.copy2(seed_cfg, cfg)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `source .venv/bin/activate && python -m pytest api/tests/test_paths.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add api/paths.py api/tests/test_paths.py
git commit -m "feat: add paths module for dev/frozen data directory resolution"
```

---

### Task 7: Route `main.py` paths through `paths.py`

Replace the project-root-anchored `PROJECT_ROOT`/`CONFIG_PATH`/`DATA_DIR` and the hardcoded `Data` path in `list_data_files` with `paths.py` values, and seed on startup. Keep the module-level attribute names so existing tests (which monkeypatch `main.DATA_DIR`, `main.CONFIG_PATH`, `main.PROJECT_ROOT`) still work.

**Files:**
- Modify: `api/main.py:45-47` and `api/main.py:843`

- [ ] **Step 1: Confirm the existing forecast-API tests pass (baseline)**

Run: `source .venv/bin/activate && python -m pytest api/tests/test_forecast_api.py -q`
Expected: all pass.

- [ ] **Step 2: Wire `paths.py` into `main.py`**

Add to the imports block in `api/main.py` (after the `from llm_service import (...)` block, around line 43):

```python
import paths
```

Replace lines 45-47:

```python
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "forecast_config.json"
DATA_DIR = PROJECT_ROOT / "Data"
```

with:

```python
paths.ensure_seeded()
PROJECT_ROOT = paths.app_data_dir()
CONFIG_PATH = paths.config_path()
DATA_DIR = paths.data_dir()
```

- [ ] **Step 3: Fix the hardcoded path in `list_data_files`**

In `api/main.py`, in `list_data_files` (around line 843), replace:

```python
        data_dir = Path(__file__).parent.parent / "Data"
```

with:

```python
        data_dir = DATA_DIR
```

- [ ] **Step 4: Run the full backend suite**

Run: `source .venv/bin/activate && python -m pytest -q`
Expected: all pass (tests monkeypatch `main.DATA_DIR`/`CONFIG_PATH`/`PROJECT_ROOT`, which still exist as module attributes).

- [ ] **Step 5: Commit**

```bash
git add api/main.py
git commit -m "refactor: resolve config and data paths via paths module"
```

---

### Task 8: Move the optional API key from `.env.local` to app-data `settings.json`

A read-only bundle cannot write `.env.local`. Persist the optional key in `settings.json` under the writable app-data folder.

**Files:**
- Modify: `api/llm_service.py:18,28-54`
- Test: `api/tests/test_llm_key_storage.py`

- [ ] **Step 1: Write the failing test**

Create `api/tests/test_llm_key_storage.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import llm_service


def test_save_and_load_key_roundtrip(monkeypatch, tmp_path):
    settings = tmp_path / "settings.json"
    monkeypatch.setattr(llm_service, "settings_path", lambda: settings)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    assert llm_service.load_api_key() is None
    llm_service.save_api_key("sk-test-123")
    assert llm_service.load_api_key() == "sk-test-123"


def test_env_var_overrides_settings(monkeypatch, tmp_path):
    settings = tmp_path / "settings.json"
    monkeypatch.setattr(llm_service, "settings_path", lambda: settings)
    llm_service.save_api_key("sk-from-file")
    monkeypatch.setenv("LLM_API_KEY", "sk-from-env")
    assert llm_service.load_api_key() == "sk-from-env"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest api/tests/test_llm_key_storage.py -q`
Expected: FAIL (`settings_path` not defined on `llm_service`, or key persisted to `.env.local`).

- [ ] **Step 3: Replace the `.env.local` key functions in `llm_service.py`**

In `api/llm_service.py`, add to the imports (after line 13):

```python
from paths import settings_path
```

Remove the `ENV_FILE = ...` line (18) and replace `load_api_key`, `save_api_key`, and `save_env_var` (lines 28-70) with:

```python
def _read_settings() -> Dict[str, Any]:
    sp = settings_path()
    if sp.is_file():
        try:
            return json.loads(sp.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _write_settings(data: Dict[str, Any]) -> None:
    sp = settings_path()
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(data, indent=2))


def load_api_key() -> Optional[str]:
    """Load LLM API key from the environment or app-data settings.json."""
    key = os.environ.get("LLM_API_KEY")
    if key:
        return key
    return _read_settings().get("LLM_API_KEY")


def save_api_key(key: str) -> None:
    """Persist the LLM API key to app-data settings.json."""
    data = _read_settings()
    data["LLM_API_KEY"] = key
    _write_settings(data)


def save_env_var(name: str, value: str) -> None:
    """Persist an arbitrary setting to app-data settings.json."""
    data = _read_settings()
    data[name] = value
    _write_settings(data)
```

- [ ] **Step 4: Run the new test and the full suite**

Run: `source .venv/bin/activate && python -m pytest api/tests/test_llm_key_storage.py -q && python -m pytest -q`
Expected: new tests pass; full suite passes. If any existing `llm_service` test referenced `ENV_FILE`, update it to monkeypatch `llm_service.settings_path` instead, then re-run.

- [ ] **Step 5: Commit**

```bash
git add api/llm_service.py api/tests/test_llm_key_storage.py
git commit -m "feat: store optional LLM key in app-data settings.json instead of .env.local"
```

---

### Task 9: Bundle seed files and verify first-run seeding

Provide the read-only seed files that `ensure_seeded()` copies into app-data on first run.

**Files:**
- Create: `build/seed/` (copies of the read-only data inputs)
- Create: `build/seed_config/forecast_config.json`
- Test: `api/tests/test_seeding.py`

- [ ] **Step 1: Write the failing test (simulates frozen seeding into a temp dir)**

Create `api/tests/test_seeding.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import paths


def test_ensure_seeded_copies_missing_files(monkeypatch, tmp_path):
    bundle = tmp_path / "bundle"
    appdata = tmp_path / "appdata"
    (bundle / "seed").mkdir(parents=True)
    (bundle / "seed" / "FOUN_sequencing_map_by_major.csv").write_text("col\n1\n")
    (bundle / "seed_config").mkdir(parents=True)
    (bundle / "seed_config" / "forecast_config.json").write_text("{}")

    monkeypatch.setattr(paths, "is_frozen", lambda: True)
    monkeypatch.setattr(paths, "bundle_dir", lambda: bundle)
    monkeypatch.setattr(paths, "app_data_dir", lambda: appdata)

    paths.ensure_seeded()
    assert (appdata / "Data" / "FOUN_sequencing_map_by_major.csv").is_file()
    assert (appdata / "forecast_config.json").is_file()


def test_ensure_seeded_does_not_overwrite(monkeypatch, tmp_path):
    bundle = tmp_path / "bundle"
    appdata = tmp_path / "appdata"
    (bundle / "seed").mkdir(parents=True)
    (bundle / "seed" / "x.csv").write_text("new\n")
    (appdata / "Data").mkdir(parents=True)
    (appdata / "Data" / "x.csv").write_text("user-edited\n")

    monkeypatch.setattr(paths, "is_frozen", lambda: True)
    monkeypatch.setattr(paths, "bundle_dir", lambda: bundle)
    monkeypatch.setattr(paths, "app_data_dir", lambda: appdata)

    paths.ensure_seeded()
    assert (appdata / "Data" / "x.csv").read_text() == "user-edited\n"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest api/tests/test_seeding.py -q`
Expected: FAIL (no seed dirs / behavior not yet exercised). If `ensure_seeded` already satisfies these, the test passes immediately — that is acceptable since Task 6 implemented the logic; this task adds the real seed files and a regression test.

- [ ] **Step 3: Populate the seed files**

```bash
mkdir -p build/seed build/seed_config
cp "Data/FOUN_sequencing_map_by_major.csv" build/seed/
cp "Data/sequence_crosswalk_template.csv" build/seed/
cp "Data/FOUN_Historical.csv" build/seed/
mkdir -p build/seed/adjustments
cp forecast_config.json build/seed_config/forecast_config.json
```
Create an empty adjustments template `build/seed/adjustments/spring_2026.json`:

```json
{ "term": "Spring 2026", "adjustments": [] }
```

- [ ] **Step 4: Run the tests**

Run: `source .venv/bin/activate && python -m pytest api/tests/test_seeding.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add build/seed build/seed_config api/tests/test_seeding.py
git commit -m "feat: bundle seed data and verify first-run seeding"
```

---

### Task 10: Serve the static frontend from FastAPI (same origin)

Mount the built UI at `/` so one port serves both the API and the UI. Guard the mount so dev/test (no `web/` build present) is unaffected.

**Files:**
- Modify: `api/main.py` (add a static mount after all routes are defined, near the bottom before `if __name__ == "__main__":`)
- Test: `api/tests/test_static_mount.py`

- [ ] **Step 1: Write the failing test**

Create `api/tests/test_static_mount.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main


def test_health_still_works():
    from fastapi.testclient import TestClient
    client = TestClient(main.app)
    r = client.get("/api/health")
    assert r.status_code == 200


def test_mount_helper_exists():
    # The helper that mounts the static UI must exist and be safe to call
    # when no web build is present.
    assert hasattr(main, "mount_static_ui")
    main.mount_static_ui()  # no-op when build dir is absent; must not raise
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest api/tests/test_static_mount.py -q`
Expected: FAIL (`main` has no attribute `mount_static_ui`).

- [ ] **Step 3: Add the static mount helper**

In `api/main.py`, just before the `if __name__ == "__main__":` block (around line 1118), add:

```python
def mount_static_ui() -> None:
    """Serve the statically-exported Next.js UI at / when present.

    No-op in dev/test where the web build is absent. Mounted last so it does
    not shadow /api routes.
    """
    from fastapi.staticfiles import StaticFiles

    web_dir = paths.bundle_dir() / "web"
    if web_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="ui")


mount_static_ui()
```

- [ ] **Step 4: Run the test and the full suite**

Run: `source .venv/bin/activate && python -m pytest api/tests/test_static_mount.py -q && python -m pytest -q`
Expected: pass; full suite green (mount is a no-op without a `web/` dir).

- [ ] **Step 5: Commit**

```bash
git add api/main.py api/tests/test_static_mount.py
git commit -m "feat: serve static UI from FastAPI on the same origin"
```

---

### Task 11: Configure the frontend for static export

Make `api.ts` treat an empty `NEXT_PUBLIC_API_URL` as same-origin, and enable static export.

**Files:**
- Modify: `frontend/src/lib/api.ts:3`
- Modify: `frontend/next.config.ts`

- [ ] **Step 1: Make the API base same-origin when the env var is empty**

In `frontend/src/lib/api.ts`, change line 3 from:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

to:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
```

(With `??`, an explicitly-empty `NEXT_PUBLIC_API_URL=''` yields `''`, so requests go to relative `/api/...` same-origin paths. Unset in dev keeps `http://localhost:8000`.)

- [ ] **Step 2: Enable static export in `next.config.ts`**

Replace `frontend/next.config.ts` with:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
```

- [ ] **Step 3: Build the static export and verify output**

Run: `cd frontend && NEXT_PUBLIC_API_URL='' npm run build`
Expected: build succeeds and produces `frontend/out/index.html`.
Verify: `test -f out/index.html && echo "static export ok"` prints `static export ok`.

- [ ] **Step 4: Run the frontend tests**

Run: `cd frontend && npm run test:run`
Expected: tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/next.config.ts
git commit -m "feat: enable Next.js static export with same-origin API base"
```

---

## Stage 2 — Desktop entry point

### Task 12: Create the pywebview launcher `desktop/app.py`

Starts the server in a background thread, waits for health, opens a native window, and shuts down cleanly on window close.

**Files:**
- Create: `desktop/app.py`
- Create: `desktop/__init__.py` (empty)

- [ ] **Step 1: Create the launcher**

Create `desktop/__init__.py` (empty file). Create `desktop/app.py`:

```python
"""Desktop entry point: run FastAPI locally and show it in a native window."""

import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

# Make the api/ package importable both in dev and when frozen.
APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT / "api"))

import uvicorn
import webview  # pywebview

import main as api_main


def _free_port(preferred: int = 8000) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


class _Server:
    def __init__(self, port: int):
        config = uvicorn.Config(api_main.app, host="127.0.0.1", port=port, log_level="warning")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._server.should_exit = True


def _wait_for_health(port: int, timeout: float = 30.0) -> bool:
    url = f"http://127.0.0.1:{port}/api/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def run() -> int:
    port = _free_port(8000)
    server = _Server(port)
    server.start()
    if not _wait_for_health(port):
        server.stop()
        sys.stderr.write("Backend failed to start.\n")
        return 1
    window = webview.create_window(
        "SCAD Forecast Tool",
        f"http://127.0.0.1:{port}/",
        width=1400,
        height=900,
    )
    webview.start()  # blocks until the window is closed
    server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
```

- [ ] **Step 2: Install desktop deps and smoke-test the launcher manually**

Run: `source .venv-build/bin/activate && (cd frontend && NEXT_PUBLIC_API_URL='' npm run build) && cp -R frontend/out web 2>/dev/null; python desktop/app.py`
Expected: a native window opens showing the forecasting UI. Close the window; the process exits 0. (In dev, `bundle_dir()` is the project root, so `mount_static_ui` looks for `web/` there; copying `frontend/out` to the project-root `web/` lets it find the UI. The packaged build wires this via the spec's `("../frontend/out", "web")` data entry in Task 14.)

- [ ] **Step 3: Clean up the dev copy**

Run: `rm -rf web`

- [ ] **Step 4: Commit**

```bash
git add desktop/app.py desktop/__init__.py
git commit -m "feat: add pywebview desktop launcher with clean server lifecycle"
```

---

### Task 13: In-app "Import Master Schedule" endpoint and button

Let the admin pick their PZSMSCP export from a native file dialog; the backend copies it into `DATA_DIR` as the configured `enrollment_source`.

**Files:**
- Modify: `api/main.py` (add `POST /api/data/import`)
- Modify: `frontend/src/components/sidebar/ConfigSidebar.tsx` (add an Import button) and `frontend/src/lib/api.ts` (add `importDataFile`)
- Test: `api/tests/test_data_import.py`

- [ ] **Step 1: Write the failing test for the import endpoint**

Create `api/tests/test_data_import.py`:

```python
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _tmp_data(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "CONFIG_PATH", tmp_path / "forecast_config.json")


def test_import_copies_source_file(tmp_path):
    src = tmp_path / "PZSMSCP_export.xlsx"
    src.write_bytes(b"fake-xlsx-bytes")
    r = client.post("/api/data/import", json={"source_path": str(src)})
    assert r.status_code == 200
    dest = main.DATA_DIR / "Master Schedule of Classes.xlsx"
    assert dest.is_file()
    assert dest.read_bytes() == b"fake-xlsx-bytes"


def test_import_rejects_missing_file():
    r = client.post("/api/data/import", json={"source_path": "/no/such/file.xlsx"})
    assert r.status_code == 400
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest api/tests/test_data_import.py -q`
Expected: FAIL (404, endpoint not defined).

- [ ] **Step 3: Add the import endpoint**

In `api/main.py`, near the other `/api/data` routes (after `list_data_files`), add:

```python
class DataImportRequest(BaseModel):
    source_path: str


@app.post("/api/data/import")
def import_data_file(request: DataImportRequest):
    """Copy a user-selected schedule export into the Data directory."""
    import shutil

    src = Path(request.source_path)
    if not src.is_file():
        raise HTTPException(status_code=400, detail="Selected file does not exist")
    if src.suffix.lower() not in (".xlsx", ".xlsm", ".xls", ".csv"):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest_name = "Master Schedule of Classes" + src.suffix.lower()
    dest = DATA_DIR / dest_name
    shutil.copy2(src, dest)
    return {"success": True, "stored_as": dest.name, "data_dir": str(DATA_DIR)}
```

- [ ] **Step 4: Run the test and full suite**

Run: `source .venv/bin/activate && python -m pytest api/tests/test_data_import.py -q && python -m pytest -q`
Expected: pass.

- [ ] **Step 5: Add the API client method**

In `frontend/src/lib/api.ts`, add to the `ApiClient` class:

```typescript
    async importDataFile(sourcePath: string) {
        return this.request<{ success: boolean; stored_as: string; data_dir: string }>(
            '/api/data/import',
            { method: 'POST', body: JSON.stringify({ source_path: sourcePath }) }
        );
    }
```

- [ ] **Step 6: Add the Import button wired to the native file dialog**

In `frontend/src/components/sidebar/ConfigSidebar.tsx`, add a button that, when pywebview is present, opens the native file dialog and posts the chosen path. Add near the top of the component body:

```tsx
  const handleImport = async () => {
    const w = window as unknown as {
      pywebview?: { api?: { create_file_dialog?: () => Promise<string[] | null> } };
    };
    if (!w.pywebview?.api?.create_file_dialog) {
      alert("Import is available in the desktop app.");
      return;
    }
    const chosen = await w.pywebview.api.create_file_dialog();
    if (chosen && chosen.length > 0) {
      const res = await api.importDataFile(chosen[0]);
      alert(`Imported. Stored as ${res.stored_as}`);
    }
  };
```

and render a button in the sidebar JSX:

```tsx
        <button
          type="button"
          onClick={handleImport}
          className="w-full rounded-md border px-3 py-2 text-sm font-medium hover:bg-accent"
        >
          Import Master Schedule…
        </button>
```

- [ ] **Step 7: Expose the file dialog to the webview**

In `desktop/app.py`, define a JS-API object and pass it to `create_window`. Add this class above `run()`:

```python
class _Bridge:
    def create_file_dialog(self):
        result = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=("Schedule exports (*.xlsx;*.xls;*.csv)", "All files (*.*)"),
        )
        return list(result) if result else None
```

and change the `create_window` call to:

```python
    window = webview.create_window(
        "SCAD Forecast Tool",
        f"http://127.0.0.1:{port}/",
        width=1400,
        height=900,
        js_api=_Bridge(),
    )
```

- [ ] **Step 8: Run frontend tests**

Run: `cd frontend && npm run test:run`
Expected: pass. If `ConfigSidebar` has a snapshot/render test, update it to account for the new button.

- [ ] **Step 9: Commit**

```bash
git add api/main.py api/tests/test_data_import.py frontend/src/lib/api.ts frontend/src/components/sidebar/ConfigSidebar.tsx desktop/app.py
git commit -m "feat: in-app Master Schedule import via native file dialog"
```

---

## Stage 3 — macOS packaging

### Task 14: PyInstaller spec, build script, and .dmg

Produce a working `.app` and `.dmg` on Apple Silicon. PyInstaller hidden-import discovery for pandas/numpy/statsmodels is empirical: the build script runs the app and you add named `--collect`/`hiddenimport` entries for any `ModuleNotFoundError` until it launches clean.

**Files:**
- Create: `build/forecast_tool.spec`
- Create: `build/build_mac.sh`

- [ ] **Step 1: Create the PyInstaller spec**

Create `build/forecast_tool.spec`:

```python
# PyInstaller spec for the SCAD Forecast Tool desktop app.
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

hiddenimports = (
    collect_submodules("statsmodels")
    + collect_submodules("pandas")
    + collect_submodules("uvicorn")
)
datas = (
    [("../frontend/out", "web")]
    + [("../build/seed", "seed")]
    + [("../build/seed_config", "seed_config")]
    + collect_data_files("statsmodels")
)

a = Analysis(
    ["../desktop/app.py"],
    pathex=["../api"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["prophet", "cmdstanpy", "tkinter", "matplotlib"],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="SCAD Forecast Tool",
          console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="SCAD Forecast Tool")
app = BUNDLE(coll, name="SCAD Forecast Tool.app",
             bundle_identifier="edu.scad.forecasttool")
```

- [ ] **Step 2: Create the macOS build script**

Create `build/build_mac.sh`:

```bash
#!/bin/bash
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[1/4] Building frontend (static export)..."
(cd frontend && NEXT_PUBLIC_API_URL='' npm ci && npm run build)

echo "[2/4] Installing desktop build deps..."
python3.13 -m venv .venv-build 2>/dev/null || true
source .venv-build/bin/activate
pip install --upgrade pip
pip install -r requirements-desktop.txt

echo "[3/4] Running PyInstaller..."
pyinstaller --noconfirm --clean --workpath .pyi-build --distpath dist build/forecast_tool.spec

echo "[4/4] Building .dmg..."
pip install dmgbuild
dmgbuild -s build/dmg_settings.py "SCAD Forecast Tool" "dist/SCAD Forecast Tool.dmg" || \
  echo "dmgbuild config missing — see Step 4."

echo "Done. App at dist/SCAD Forecast Tool.app"
```

Make it executable: `chmod +x build/build_mac.sh`.

- [ ] **Step 3: Run the build and iterate on hidden imports**

Run: `bash build/build_mac.sh`
Then launch: `open "dist/SCAD Forecast Tool.app"` (or run the inner binary from a terminal to see logs: `"dist/SCAD Forecast Tool.app/Contents/MacOS/SCAD Forecast Tool"`).
Expected: the window opens and a Spring 2026 forecast runs. If it exits with `ModuleNotFoundError: X`, add `X` (or `collect_submodules("X")`) to `hiddenimports` in the spec and rebuild. Repeat until clean. Record each addition.

- [ ] **Step 4: Add the dmgbuild settings**

Create `build/dmg_settings.py`:

```python
import os
app = os.path.join("dist", "SCAD Forecast Tool.app")
files = [app]
symlinks = {"Applications": "/Applications"}
icon_locations = {"SCAD Forecast Tool.app": (140, 120), "Applications": (500, 120)}
window_rect = ((100, 100), (640, 280))
```
Re-run `bash build/build_mac.sh` and confirm `dist/SCAD Forecast Tool.dmg` exists and, when opened, installs by drag-to-Applications.

- [ ] **Step 5: Verify a clean launch from /Applications**

Drag the app to /Applications, then launch via right-click → Open (unsigned). Import a real PZSMSCP export and run a forecast for the next quarter.
Expected: forecast renders; data is written under `~/Library/Application Support/SCAD Forecast Tool/`.

- [ ] **Step 6: Commit**

```bash
git add build/forecast_tool.spec build/build_mac.sh build/dmg_settings.py
git commit -m "build: macOS PyInstaller spec, build script, and dmg packaging"
```

---

## Stage 4 — Windows packaging (CI)

### Task 15: GitHub Actions Windows build → .exe installer

Build the Windows installer on a `windows-latest` runner (no local Windows machine needed).

**Files:**
- Create: `.github/workflows/build-windows.yml`
- Create: `build/installer.iss` (Inno Setup script)

- [ ] **Step 1: Create the Inno Setup script**

Create `build/installer.iss`:

```ini
[Setup]
AppName=SCAD Forecast Tool
AppVersion=1.0.0
DefaultDirName={autopf}\SCAD Forecast Tool
DefaultGroupName=SCAD Forecast Tool
OutputBaseFilename=SCAD-Forecast-Tool-Setup
OutputDir=dist
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "dist\SCAD Forecast Tool\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\SCAD Forecast Tool"; Filename: "{app}\SCAD Forecast Tool.exe"
Name: "{commondesktop}\SCAD Forecast Tool"; Filename: "{app}\SCAD Forecast Tool.exe"

[Run]
Filename: "{app}\SCAD Forecast Tool.exe"; Description: "Launch SCAD Forecast Tool"; Flags: nowait postinstall skipifsilent
```

- [ ] **Step 2: Create the Windows build workflow**

Create `.github/workflows/build-windows.yml`:

```yaml
name: Build Windows Installer

on:
  workflow_dispatch:
  push:
    tags: ["v*"]

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Build frontend (static export)
        working-directory: frontend
        env:
          NEXT_PUBLIC_API_URL: ""
        run: |
          npm ci
          npm run build

      - name: Install Python build deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-desktop.txt

      - name: Run PyInstaller
        run: pyinstaller --noconfirm --clean --workpath .pyi-build --distpath dist build/forecast_tool.spec

      - name: Install Inno Setup
        run: choco install innosetup --no-progress -y

      - name: Build installer
        run: '& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build\installer.iss'

      - name: Upload installer artifact
        uses: actions/upload-artifact@v4
        with:
          name: SCAD-Forecast-Tool-Windows
          path: dist/SCAD-Forecast-Tool-Setup.exe
```

- [ ] **Step 3: Trigger the workflow and download the artifact**

Push the branch, then run the workflow: `gh workflow run "Build Windows Installer" --ref feat/desktop-packaging`. Watch: `gh run watch`.
Expected: the run succeeds and produces the `SCAD-Forecast-Tool-Windows` artifact. If PyInstaller fails on a Windows-only hidden import, add it to the spec (same loop as Task 14, Step 3) and re-run.

- [ ] **Step 4: Verify on Windows**

On a clean Windows 10/11 machine or VM with no Python/Node, download the artifact, run `SCAD-Forecast-Tool-Setup.exe` (clear SmartScreen via More info → Run anyway), launch, import a PZSMSCP export, and run a forecast.
Expected: forecast renders; data is written under `%APPDATA%\SCAD Forecast Tool\`. If the window is blank, confirm the WebView2 runtime is present (see Task 17 note).

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/build-windows.yml build/installer.iss
git commit -m "build: Windows installer via GitHub Actions and Inno Setup"
```

---

## Stage 5 — Smoke tests and documentation

### Task 16: Add a launch smoke test

A scripted check that the app's server starts, health passes, and both a sequence and a ratio forecast return rows.

**Files:**
- Create: `api/tests/test_smoke_forecast.py`

- [ ] **Step 1: Write the smoke test**

Create `api/tests/test_smoke_forecast.py`:

```python
"""End-to-end-ish smoke test against the real engine and bundled seed data."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main

client = TestClient(main.app)

DATA_PRESENT = (main.DATA_DIR / "FOUN_sequencing_map_by_major.csv").is_file()


@pytest.mark.skipif(not DATA_PRESENT, reason="requires real seq map in Data/")
def test_health():
    assert client.get("/api/health").json()["status"] in ("ok", "healthy")


@pytest.mark.skipif(not DATA_PRESENT, reason="requires real seq map in Data/")
def test_spring_forecast_returns_rows():
    body = client.post("/api/forecast", json={"term": "Spring 2026"}).json()
    assert "summary" in body
    assert len(body["results"]) > 0
```

- [ ] **Step 2: Run it**

Run: `source .venv/bin/activate && python -m pytest api/tests/test_smoke_forecast.py -q`
Expected: PASS (or SKIP if the seq map is absent in this checkout). Confirm it PASSES on a checkout that has `Data/FOUN_sequencing_map_by_major.csv`.

- [ ] **Step 3: Commit**

```bash
git add api/tests/test_smoke_forecast.py
git commit -m "test: add launch smoke test for sequence forecast"
```

---

### Task 17: Update the handoff guide for desktop install

Document install, first-run security warnings, where data lives, and how to import the Cognos export.

**Files:**
- Modify: `docs/HANDOFF_GUIDE.md`
- Modify: `README.md`

- [ ] **Step 1: Rewrite the install section of `docs/HANDOFF_GUIDE.md`**

Add a "Installing the Desktop App" section covering:
- macOS: open the `.dmg`, drag to Applications, first launch via right-click → Open (one-time Gatekeeper bypass for the unsigned v1).
- Windows: run `SCAD-Forecast-Tool-Setup.exe`, click More info → Run anyway (one-time SmartScreen bypass). If the window is blank, install the Microsoft Edge WebView2 Runtime (link), though it is preinstalled on Windows 11 and most Windows 10.
- Where data lives: macOS `~/Library/Application Support/SCAD Forecast Tool/`, Windows `%APPDATA%\SCAD Forecast Tool\`.
- Updating each quarter: use the in-app "Import Master Schedule…" button to load the latest PZSMSCP export; no need to touch the data folder by hand.
- Updating the app: download and run the new installer (no auto-update in v1).

- [ ] **Step 2: Update `README.md`**

Add a short "Desktop App" subsection pointing to the handoff guide and noting the build commands (`build/build_mac.sh` and the GitHub Actions Windows workflow).

- [ ] **Step 3: Update project memory docs**

Update `CLAUDE.md` and `MEMORY.md` per the repo's UPDATE RULE: note the desktop-packaging architecture, the writable app-data directory, the Prophet removal, the Summer ratio-fallback fix, and the new build pipeline.

- [ ] **Step 4: Commit**

```bash
git add docs/HANDOFF_GUIDE.md README.md CLAUDE.md "$(python -c "import os;print(os.path.expanduser('~/.claude/projects/-Users-nathanmadrid-projects-forecast-tool/memory/MEMORY.md'))")" 2>/dev/null || git add docs/HANDOFF_GUIDE.md README.md CLAUDE.md
git commit -m "docs: desktop install guide, data locations, and memory updates"
```

---

## Notes and known iteration points

- **PyInstaller hidden imports (Tasks 14-15)** are discovered empirically. The spec excludes `prophet`/`cmdstanpy` deliberately; if a `ModuleNotFoundError` appears at launch, add the named module to `hiddenimports` and rebuild. This is expected, not a failure.
- **WebView2 on Windows (Task 15/17):** present on Win11 and most updated Win10. If a blank window appears, the runtime is missing; the v1 mitigation is documentation, and a v2 improvement is bundling the WebView2 bootstrapper in the Inno Setup `[Run]` section.
- **Intel Macs:** the Task 14 build is arm64-only. A universal2 build is possible later if the admin is on Intel.
- **Signing (deferred):** v1 ships unsigned; Tasks 14-15 produce installers that trigger one-time Gatekeeper/SmartScreen prompts, documented in Task 17.
- **Stage boundaries are natural checkpoints.** Stage 0 leaves a green, lean codebase; Stage 1-2 a working dev desktop app; Stage 3-4 the installers. Review between stages.
