# Historical (Same-Season) Forecasting Method Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a course-level same-season historical forecast as the default `/api/forecast` method, decoupled from the sequencing guide, with the sequence-map engine kept as an opt-in.

**Architecture:** A new pure function `run_sameseason_forecast()` projects each FOUN course/campus from its own prior same-season enrollment (post-rollout terms only), reusing `load_term_enrollments` and the season-aware `forecast_ols` (with a level fallback for a single data point). `run_forecast` in `api/main.py` gains a `method` switch defaulting to `historical`; `sequence` selects the existing engine. A method-aware guardrail returns a clear 422 when the required prior same-season term is missing.

**Tech Stack:** Python, FastAPI, pandas/numpy (via `forecast_tool`), Next.js frontend.

**Conventions:** Run backend tests from the project root: `source .venv/bin/activate && python -m pytest -q`. Branch: `feat/historical-forecasting`. Spec: `docs/superpowers/specs/2026-06-08-historical-forecasting-method-design.md`. Commit per task (Conventional Commits).

---

## File Structure

- **Modify** `api/forecaster.py` — add `run_sameseason_forecast()` near `run_sequence_forecast` (reuses existing `resolve_term_info`, `_FOUN_CURRICULUM_START`, `load_term_enrollments`, `compute_sections`, `load_crosswalk`).
- **Create** `api/tests/test_sameseason_forecast.py` — unit tests for the new function.
- **Modify** `api/main.py` — `run_forecast` method switch + method-aware guardrail; `ForecastRequest.method` type; default in config read.
- **Modify** `api/tests/test_forecast_api.py` — method selection + historical guardrail tests.
- **Modify** `forecast_config.json` — add `"method": "historical"`.
- **Modify** `frontend/src/hooks/useChat.ts` and `frontend/src/lib/api.ts` — send/type `method: 'historical'`.
- **Modify** `CLAUDE.md`, `docs/HANDOFF_GUIDE.md` — document the historical method + data requirement.

---

## Task 1: `run_sameseason_forecast()` in the engine

**Files:**
- Modify: `api/forecaster.py` (add the function after `run_sequence_forecast`, before `_compute_historical_ratios`)
- Test: `api/tests/test_sameseason_forecast.py`

- [ ] **Step 1: Write the failing tests**

Create `api/tests/test_sameseason_forecast.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import forecaster as F


def _patch_terms(monkeypatch, by_code):
    """Make load_term_enrollments return canned {(campus,course): seats} per term code."""
    calls = []

    def fake(path, term_code, crosswalk=None):
        calls.append(term_code)
        return dict(by_code.get(term_code, {}))

    monkeypatch.setattr(F, "load_term_enrollments", fake)
    return calls


def test_level_single_point(monkeypatch):
    # Fall 2026 = 202710; only prior post-rollout same-season is Fall 2025 = 202610
    _patch_terms(monkeypatch, {"202610": {("SAVANNAH", "FOUN 110"): 1950}})
    rows = F.run_sameseason_forecast(Path("x.csv"), "Fall 2026", capacity=20, buffer_percent=0.0, crosswalk={})
    row = next(r for r in rows if r["course"] == "FOUN 110" and r["campus"] == "Savannah")
    assert round(row["projected_seats"]) == 1950
    assert row["method"] == "same_season"
    assert row["sections"] == 98  # ceil(1950/20)


def test_trend_two_points(monkeypatch):
    # Fall 2027 = 202810; priors Fall 2026 (202710) and Fall 2025 (202610)
    _patch_terms(monkeypatch, {
        "202610": {("SAVANNAH", "FOUN 110"): 100},
        "202710": {("SAVANNAH", "FOUN 110"): 120},
    })
    rows = F.run_sameseason_forecast(Path("x.csv"), "Fall 2027", capacity=20, buffer_percent=0.0, crosswalk={})
    row = next(r for r in rows if r["course"] == "FOUN 110")
    assert round(row["projected_seats"]) == 140  # linear trend 100->120 -> 140


def test_post_rollout_cutoff_only_queries_2026_plus(monkeypatch):
    # Fall 2026: must query 202610 (post-rollout) and NOT 202510 (old curriculum)
    calls = _patch_terms(monkeypatch, {"202610": {("SAVANNAH", "FOUN 110"): 60}})
    F.run_sameseason_forecast(Path("x.csv"), "Fall 2026", crosswalk={})
    assert "202610" in calls
    assert "202510" not in calls


def test_new_course_flagged(monkeypatch):
    # FOUN 999 appears in the target term but has no same-season history
    _patch_terms(monkeypatch, {
        "202610": {("SAVANNAH", "FOUN 110"): 60},
        "202710": {("SAVANNAH", "FOUN 110"): 5, ("SAVANNAH", "FOUN 999"): 12},
    })
    rows = F.run_sameseason_forecast(Path("x.csv"), "Fall 2026", crosswalk={})
    new = next(r for r in rows if r["course"] == "FOUN 999")
    assert new["projected_seats"] == 0.0
    assert new["method"] == "same_season_new_course"


def test_empty_when_no_history(monkeypatch):
    _patch_terms(monkeypatch, {})  # nothing for any term
    rows = F.run_sameseason_forecast(Path("x.csv"), "Fall 2026", crosswalk={})
    assert rows == []


def test_buffer_applied(monkeypatch):
    _patch_terms(monkeypatch, {"202610": {("SCADNOW", "FOUN 113"): 200}})
    rows = F.run_sameseason_forecast(Path("x.csv"), "Fall 2026", capacity=20, buffer_percent=10.0, crosswalk={})
    row = next(r for r in rows if r["course"] == "FOUN 113")
    assert round(row["projected_seats"]) == 220  # 200 * 1.10
    assert row["campus"] == "SCADnow"
```

- [ ] **Step 2: Run to verify it fails**

Run: `source .venv/bin/activate && python -m pytest api/tests/test_sameseason_forecast.py -q`
Expected: FAIL with `AttributeError: module 'forecaster' has no attribute 'run_sameseason_forecast'`.

- [ ] **Step 3: Implement the function**

In `api/forecaster.py`, add immediately after `run_sequence_forecast` (it ends around line 1016, before `_compute_historical_ratios`):

```python
def run_sameseason_forecast(
    master_schedule_path: Path,
    target_term: str,
    capacity: int = 20,
    buffer_percent: float = 0.0,
    crosswalk: Optional[Dict[str, str]] = None,
) -> List[Dict]:
    """Forecast each FOUN course from its own prior same-season enrollment.

    Robust to sequencing-guide changes: it never reads the sequencing map.
    Uses only post-rollout terms (academic-year part of the code
    > _FOUN_CURRICULUM_START). With 2+ prior same-season points it fits the
    season-aware OLS trend; with one point it uses that value (level).
    Assumes the prior same-season terms are consecutive (no gap years), which
    holds for the post-rollout window. Courses offered in the target term but
    with no same-season history are returned with projected_seats=0 and method
    "same_season_new_course" so the admin can set a manual estimate.

    Returns rows shaped like run_sequence_forecast:
        {course, campus, projected_seats, sections, method}
    Returns [] when no same-season history (and no target-term courses) exist;
    the caller turns that into a clear guardrail error.
    """
    import pandas as pd
    from forecast_tool.forecasting.ols_forecast import forecast_ols

    if crosswalk is None:
        crosswalk = load_crosswalk(master_schedule_path.parent / "sequence_crosswalk_template.csv")

    info = resolve_term_info(target_term)
    target_code = info["target_term_code"]
    yyyy = int(target_code[:4])
    qq = target_code[4:]

    # Prior same-season term codes, post-rollout only, nearest year first.
    prior_codes: List[str] = []
    k = 1
    while (yyyy - k) > _FOUN_CURRICULUM_START:
        prior_codes.append(f"{yyyy - k}{qq}")
        k += 1

    # Build each (campus, course) same-season series {cal_year: enrollment}.
    series: DefaultDict[Tuple[str, str], Dict[int, float]] = defaultdict(dict)
    for code in prior_codes:
        for (campus, course), seats in load_term_enrollments(
            master_schedule_path, code, crosswalk=crosswalk
        ).items():
            if str(course).startswith("FOUN"):
                series[(campus, course)][int(code[:4])] = seats

    campus_label = {"SAVANNAH": "Savannah", "SCADNOW": "SCADnow", "ATLANTA": "Atlanta"}
    buffer_mult = 1.0 + (buffer_percent / 100.0)
    rows: List[Dict] = []

    for (campus, course), year_map in series.items():
        pts = sorted(year_map.items())  # [(year, enrollment), ...] ascending
        if len(pts) >= 2:
            df = pd.DataFrame({"ds": [str(y) for y, _ in pts], "y": [e for _, e in pts]})
            fc = forecast_ols(df, periods=1)
            value = float(fc.iloc[-1]["yhat"]) if not fc.empty else float(pts[-1][1])
        else:
            value = float(pts[-1][1])
        seats = value * buffer_mult
        rows.append({
            "course": course,
            "campus": campus_label.get(campus, campus),
            "projected_seats": seats,
            "sections": compute_sections(seats, capacity),
            "method": "same_season",
        })

    # Flag FOUN courses offered in the target term that have no history.
    for (campus, course), _seats in load_term_enrollments(
        master_schedule_path, target_code, crosswalk=crosswalk
    ).items():
        if str(course).startswith("FOUN") and (campus, course) not in series:
            rows.append({
                "course": course,
                "campus": campus_label.get(campus, campus),
                "projected_seats": 0.0,
                "sections": 0,
                "method": "same_season_new_course",
            })

    return rows
```

- [ ] **Step 4: Run to verify it passes**

Run: `source .venv/bin/activate && python -m pytest api/tests/test_sameseason_forecast.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Full suite + commit**

Run: `python -m pytest -q` (expected: all pass).
```bash
git add api/forecaster.py api/tests/test_sameseason_forecast.py
git commit -m "feat: add course-level same-season historical forecaster"
```

---

## Task 2: Method switch + guardrail in the API

**Files:**
- Modify: `api/main.py` (`ForecastRequest`, `run_forecast`, imports)
- Modify: `forecast_config.json`
- Test: `api/tests/test_forecast_api.py`

- [ ] **Step 1: Update the autouse fixture and sequence-specific tests, then add method tests**

Because the default becomes `historical`, every test that posts without a `method` now hits `run_sameseason_forecast`. Update `api/tests/test_forecast_api.py` so the suite stays valid:

1. In the autouse `patch_forecast` fixture, add a default stub for the new function right after the `run_sequence_forecast` stub:

```python
    monkeypatch.setattr(main, "run_sameseason_forecast", lambda **kw: [_FAKE_ROW])
```

2. The tests that specifically exercise the **sequence/ratio** path must opt into it. In `test_forecast_falls_back_to_ratio_when_sequence_empty`, `test_forecast_ratio_fallback_passes_target_term`, and `test_forecast_all_zero_returns_422_with_feeder_message`, change each `client.post("/api/forecast", json={"term": ...})` to include `"method": "sequence"`, e.g.:

```python
    client.post("/api/forecast", json={"term": "Summer 2026", "method": "sequence"})
```

Then append these new method-selection tests (after the no-feeder guardrail test):

```python
# --------------- Method selection (historical default) ---------------------

def test_forecast_defaults_to_historical(monkeypatch):
    called = {}
    monkeypatch.setattr(main, "run_sameseason_forecast",
                        lambda **kw: (called.setdefault("ss", True), [_FAKE_ROW])[1])
    monkeypatch.setattr(main, "run_sequence_forecast",
                        lambda **kw: (called.setdefault("seq", True), [_FAKE_ROW])[1])
    body = client.post("/api/forecast", json={"term": "Fall 2026"}).json()
    assert called.get("ss") is True
    assert called.get("seq") is None
    assert body["summary"]["method"] == "Same-season historical"


def test_forecast_method_sequence_uses_sequence_engine(monkeypatch):
    called = {}
    monkeypatch.setattr(main, "run_sameseason_forecast",
                        lambda **kw: (called.setdefault("ss", True), [_FAKE_ROW])[1])
    monkeypatch.setattr(main, "run_sequence_forecast",
                        lambda **kw: (called.setdefault("seq", True), [_FAKE_ROW])[1])
    client.post("/api/forecast", json={"term": "Spring 2026", "method": "sequence"})
    assert called.get("seq") is True
    assert called.get("ss") is None


def test_historical_no_history_returns_422(monkeypatch):
    monkeypatch.setattr(main, "run_sameseason_forecast", lambda **kw: [])
    r = client.post("/api/forecast", json={"term": "Fall 2026"})
    assert r.status_code == 422
    assert "same-season" in r.json()["detail"].lower()
```

- [ ] **Step 2: Run to verify it fails**

Run: `source .venv/bin/activate && python -m pytest api/tests/test_forecast_api.py -q`
Expected: FAIL (`run_sameseason_forecast` not importable in `main`; method not wired).

- [ ] **Step 3: Wire the method switch**

In `api/main.py`, add `run_sameseason_forecast` to the `from forecaster import (...)` block (line 21-28):

```python
from forecaster import (
    run_sequence_forecast,
    run_sameseason_forecast,
    run_ratio_forecast,
    load_previous_forecast,
    get_available_terms,
    term_code_to_label,
    resolve_term_info,
)
```

Change `ForecastRequest.method` (around line 188) to:

```python
    method: Optional[str] = "historical"
```

In `run_forecast`, replace the sequence call + ratio fallback block (the lines from `# Run the real forecast` / `rows = run_sequence_forecast(...)` through the ratio-fallback loop that sets `method_label`) with a method switch. The block currently begins at `rows = run_sequence_forecast(` (around line 460) and ends after the ratio-fallback `for csv_path in candidates:` loop (around line 507, just before `# Apply output-level adjustments`). Replace it with:

```python
        method = (request.method or disk_cfg.get("method") or "historical").lower()

        if method == "sequence":
            rows = run_sequence_forecast(
                sequence_map_path=sequence_map_path,
                enrollment_source_path=enrollment_source_path,
                target_term=target_term,
                capacity=capacity,
                progression_rate=progression_rate,
                buffer_percent=buffer_percent,
                admits_path=admits_path,
                enrollment_by_major_path=enrollment_by_major_path,
            )
            method_label = "Sequence-based"
            # Fallback: ratio-based when sequencing has no data (e.g. Summer)
            if not rows:
                info = resolve_term_info(target_term)
                feeder_quarter = info["closer_feeder"]["quarter"].capitalize()
                feeder_tc = info["closer_feeder"]["term_code"]
                feeder_label = term_code_to_label(feeder_tc)
                feeder_year = feeder_label.split()[1] if " " in feeder_label else feeder_tc[:4]
                feeder_pattern = f"{feeder_quarter}_{feeder_year}_FOUN_Forecast*.csv"
                feeder_csvs = sorted(DATA_DIR.glob(feeder_pattern))
                historical_path = DATA_DIR / "FOUN_Historical.csv"
                if feeder_csvs:
                    preferred = [p for p in feeder_csvs
                                 if "Sequence_Guides" in p.name or "sequence_guides" in p.name]
                    candidates = preferred + [p for p in reversed(feeder_csvs) if p not in preferred]
                    for csv_path in candidates:
                        rows = run_ratio_forecast(
                            feeder_forecast_path=csv_path,
                            historical_data_path=historical_path,
                            target_term=target_term,
                            capacity=capacity,
                            buffer_percent=buffer_percent,
                        )
                        if rows:
                            method_label = "Ratio-based"
                            break
        else:
            rows = run_sameseason_forecast(
                master_schedule_path=enrollment_source_path,
                target_term=target_term,
                capacity=capacity,
                buffer_percent=buffer_percent,
            )
            method_label = "Same-season historical"
```

(Preserve the existing `def resolve(...)`/`resolve_optional(...)` and the `sequence_map_path`/`enrollment_source_path`/`admits_path`/`enrollment_by_major_path` assignments that come before this block.)

- [ ] **Step 4: Make the guardrail method-aware**

Find the no-feeder guardrail added earlier (the block `if rows and sum((r.get("projected_seats") or 0) for r in rows) == 0:` right after `apply_output_adjustments`). Replace it with a version that also catches the historical empty case and tailors the message:

```python
        # Guardrail: nothing to forecast means the Master Schedule lacks the
        # data this method needs. Explain it instead of returning zeros.
        no_data = (not rows) or sum((r.get("projected_seats") or 0) for r in rows) == 0
        if no_data:
            _g = resolve_term_info(target_term)
            if method == "sequence":
                _closer = term_code_to_label(_g.get("closer_feeder", {}).get("term_code", ""))
                _farther = term_code_to_label(_g.get("farther_feeder", {}).get("term_code", ""))
                _detail = (
                    f"No feeder enrollment found to forecast {target_term}. The imported "
                    f"Master Schedule must include the prior quarters ({_farther} and "
                    f"{_closer}). Import the PZSMSCP export covering those terms."
                )
            else:
                _yy = int(_g["target_term_code"][:4]) - 1
                _prior = term_code_to_label(f"{_yy}{_g['target_term_code'][4:]}")
                _detail = (
                    f"No same-season history found to forecast {target_term}. Import a "
                    f"Master Schedule that includes the prior year's same quarter ({_prior})."
                )
            raise HTTPException(status_code=422, detail=_detail)
```

- [ ] **Step 5: Add the config default**

In `forecast_config.json`, add `"method": "historical",` (e.g., after `"default_term"`).

- [ ] **Step 6: Run tests + commit**

Run: `source .venv/bin/activate && python -m pytest api/tests/test_forecast_api.py -q && python -m pytest -q`
Expected: all pass. (Step 1 already updated the autouse fixture and the three sequence-specific tests; if any other pre-existing test still fails because it assumed the sequence path, give it `"method": "sequence"`.)
```bash
git add api/main.py api/tests/test_forecast_api.py forecast_config.json
git commit -m "feat: default /api/forecast to historical method, sequence opt-in, method-aware guardrail"
```

---

## Task 3: Point the frontend at the historical method

**Files:**
- Modify: `frontend/src/lib/api.ts` (the `ForecastRequest` interface and any default)
- Modify: `frontend/src/hooks/useChat.ts` (both forecast calls send `method: 'historical'`)

- [ ] **Step 1: Update the request type**

In `frontend/src/lib/api.ts`, change the `ForecastRequest.method` union (around line 14) to:

```typescript
    method?: 'historical' | 'sequence';
```

- [ ] **Step 2: Send historical from both call sites**

In `frontend/src/hooks/useChat.ts`, in BOTH `runForecast` and `sendMessage`, change `method: 'sequence'` to `method: 'historical'` in the `api.runForecast({ ... })` call.

- [ ] **Step 3: Verify build + tests**

Run: `cd frontend && pnpm run lint && NEXT_PUBLIC_API_URL='' pnpm run build && pnpm run test:run`
Expected: lint clean, `out/index.html` produced, tests pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/hooks/useChat.ts
git commit -m "feat: frontend runs the historical forecast method by default"
```

---

## Task 4: Documentation

**Files:**
- Modify: `CLAUDE.md`, `docs/HANDOFF_GUIDE.md`

- [ ] **Step 1: Update CLAUDE.md**

In `CLAUDE.md`, under the forecasting/architecture section, add that `/api/forecast` defaults to the **historical (same-season) method** (`run_sameseason_forecast`): each FOUN course is projected from its own prior same-season enrollment (post-rollout terms only; trend with 2+ years, else level), independent of the sequencing map. The sequence-map engine remains available via `method: sequence`. Data requirement for historical: the Master Schedule must include the **prior year's same quarter**.

- [ ] **Step 2: Update HANDOFF_GUIDE.md**

In the "Loading Data Each Quarter" section, add: the tool now forecasts each course from last year's same term, so the imported Master Schedule should include **the prior year's same quarter** (to forecast Fall 2026, include Fall 2025). If it's missing, the app says so. Brand-new courses with no history are flagged for a manual estimate.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md docs/HANDOFF_GUIDE.md
git commit -m "docs: document the default historical forecasting method and its data requirement"
```

---

## Self-Review notes

- **Spec coverage:** §3 rule → Task 1 (level/trend/cutoff/buffer); §4 components → Tasks 1-2; §5 guardrail → Task 2 Step 4; §6 new courses → Task 1 (`same_season_new_course`); §2 default historical + sequence opt-in → Task 2; frontend → Task 3; docs → Task 4. All covered.
- **Single-point fallback:** `forecast_ols` returns empty for <2 rows, so Task 1 uses the level branch for 1 point and only calls `forecast_ols` for 2+ — correct.
- **Consecutive-years assumption** is documented in the function docstring (holds for the post-rollout window; revisit if a gap year appears).
- **Pre-existing sequence/ratio tests:** Task 2 Step 1 updates the autouse fixture (adds a `run_sameseason_forecast` stub so default-historical tests stay green) and gives the three sequence-specific tests an explicit `"method": "sequence"`. This is the main breakage risk from flipping the default and is handled head-on.
