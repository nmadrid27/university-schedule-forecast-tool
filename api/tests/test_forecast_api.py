"""Tests for POST /api/forecast endpoint.

Heavy forecasting functions are stubbed at the main-module level so tests
run without real data files and complete in milliseconds.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main
from adjustments import Adjustment, TermAdjustments

client = TestClient(main.app)

# --------------- Fixtures -----------------------------------------------

_FAKE_ROW = dict(
    course="FOUN 110",
    campus="SAV",
    projected_seats=100,
    sections=5,
    adjusted=False,
)


def _empty_adjustments(data_dir, term):
    return TermAdjustments(term=term, adjustments=[])


@pytest.fixture(autouse=True)
def patch_forecast(monkeypatch, tmp_path):
    """Stub heavy I/O for every test in this module."""
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "CONFIG_PATH", tmp_path / "forecast_config.json")
    monkeypatch.setattr(main, "PROJECT_ROOT", tmp_path)
    # Default stubs — individual tests may override
    monkeypatch.setattr(main, "run_sequence_forecast", lambda **kw: [_FAKE_ROW])
    monkeypatch.setattr(main, "run_sameseason_forecast", lambda **kw: [_FAKE_ROW])
    monkeypatch.setattr(main, "load_adjustments", _empty_adjustments)


# --------------- Happy path -----------------------------------------------

def test_forecast_returns_200():
    r = client.post("/api/forecast", json={"term": "Spring 2026"})
    assert r.status_code == 200


def test_forecast_response_has_results_and_summary():
    body = client.post("/api/forecast", json={"term": "Spring 2026"}).json()
    assert "results" in body
    assert "summary" in body


def test_forecast_result_shape():
    body = client.post("/api/forecast", json={"term": "Spring 2026"}).json()
    row = body["results"][0]
    assert row["course"] == "FOUN 110"
    assert row["campus"] == "SAV"
    assert row["projectedSeats"] == 100
    assert row["sections"] == 5


def test_forecast_summary_method_is_sequence_based():
    body = client.post("/api/forecast", json={"term": "Spring 2026", "method": "sequence"}).json()
    assert body["summary"]["method"] == "Sequence-based"


def test_forecast_summary_totals():
    body = client.post("/api/forecast", json={"term": "Spring 2026"}).json()
    s = body["summary"]
    assert s["totalStudents"] == 100
    assert s["totalSections"] == 5
    assert s["coursesForecasted"] == 1


def test_forecast_adjustments_applied_absent_when_none():
    body = client.post("/api/forecast", json={"term": "Spring 2026"}).json()
    # No active adjustments → field should be null/absent
    assert body["summary"].get("adjustmentsApplied") is None


# --------------- Config override ------------------------------------------

def test_forecast_respects_capacity_override(monkeypatch):
    calls = []

    def capture(**kw):
        calls.append(kw)
        return [_FAKE_ROW]

    monkeypatch.setattr(main, "run_sequence_forecast", capture)
    client.post("/api/forecast", json={"term": "Spring 2026", "method": "sequence", "config": {"capacity": 30}})
    assert calls[0]["capacity"] == 30


def test_forecast_respects_progression_rate_override(monkeypatch):
    calls = []

    def capture(**kw):
        calls.append(kw)
        return [_FAKE_ROW]

    monkeypatch.setattr(main, "run_sequence_forecast", capture)
    client.post("/api/forecast", json={
        "term": "Spring 2026",
        "method": "sequence",
        "config": {"progressionRate": 0.80},
    })
    assert abs(calls[0]["progression_rate"] - 0.80) < 1e-9


# --------------- Active adjustments ---------------------------------------

def test_forecast_adjustments_applied_count_in_summary(monkeypatch):
    active_adj = Adjustment(
        id="x1", type="output", operation="multiply", value=1.1,
        reason="buffer up", enabled=True, source="manual",
    )
    monkeypatch.setattr(
        main,
        "load_adjustments",
        lambda data_dir, term: TermAdjustments(term=term, adjustments=[active_adj]),
    )
    body = client.post("/api/forecast", json={"term": "Spring 2026"}).json()
    assert body["summary"]["adjustmentsApplied"] == 1


# --------------- Error handling -------------------------------------------

def test_forecast_returns_404_on_file_not_found(monkeypatch):
    monkeypatch.setattr(
        main, "run_sequence_forecast",
        lambda **kw: (_ for _ in ()).throw(FileNotFoundError("missing file")),
    )
    r = client.post("/api/forecast", json={"term": "Spring 2026", "method": "sequence"})
    assert r.status_code == 404


def test_forecast_returns_400_on_value_error(monkeypatch):
    monkeypatch.setattr(
        main, "run_sequence_forecast",
        lambda **kw: (_ for _ in ()).throw(ValueError("bad value")),
    )
    r = client.post("/api/forecast", json={"term": "Spring 2026", "method": "sequence"})
    assert r.status_code == 400


def test_forecast_returns_500_on_unexpected_error(monkeypatch):
    monkeypatch.setattr(
        main, "run_sequence_forecast",
        lambda **kw: (_ for _ in ()).throw(RuntimeError("unexpected")),
    )
    r = client.post("/api/forecast", json={"term": "Spring 2026", "method": "sequence"})
    assert r.status_code == 500


# --------------- Ratio fallback -------------------------------------------

def test_forecast_falls_back_to_ratio_when_sequence_empty(monkeypatch, tmp_path):
    """When run_sequence_forecast returns [], the endpoint calls run_ratio_forecast
    and reports method='Ratio-based'."""
    monkeypatch.setattr(main, "run_sequence_forecast", lambda **kw: [])
    # Control term resolution so the feeder glob pattern is deterministic
    monkeypatch.setattr(main, "resolve_term_info", lambda term: {
        "closer_feeder": {"quarter": "spring", "term_code": "202630"},
    })
    monkeypatch.setattr(main, "term_code_to_label", lambda tc: "Spring 2026")
    # Feeder CSV must exist in DATA_DIR (= tmp_path) to satisfy the glob
    (tmp_path / "Spring_2026_FOUN_Forecast_Sequence_Guides.csv").touch()
    monkeypatch.setattr(main, "run_ratio_forecast", lambda **kw: [_FAKE_ROW])

    body = client.post("/api/forecast", json={"term": "Summer 2026", "method": "sequence"}).json()
    assert body["summary"]["method"] == "Ratio-based"


def test_forecast_ratio_fallback_passes_target_term(monkeypatch, tmp_path):
    """run_ratio_forecast receives the correct target_term."""
    captured: dict = {}
    monkeypatch.setattr(main, "run_sequence_forecast", lambda **kw: [])
    monkeypatch.setattr(main, "resolve_term_info", lambda term: {
        "closer_feeder": {"quarter": "spring", "term_code": "202630"},
    })
    monkeypatch.setattr(main, "term_code_to_label", lambda tc: "Spring 2026")
    (tmp_path / "Spring_2026_FOUN_Forecast_Sequence_Guides.csv").touch()

    def capture_ratio(**kw):
        captured.update(kw)
        return [_FAKE_ROW]

    monkeypatch.setattr(main, "run_ratio_forecast", capture_ratio)
    client.post("/api/forecast", json={"term": "Summer 2026", "method": "sequence"})
    assert captured.get("target_term") == "Summer 2026"


# --------------- No-feeder guardrail ---------------------------------------

def test_forecast_all_zero_returns_422_with_feeder_message(monkeypatch):
    """An all-zero forecast (no feeder enrollment) returns a clear 422, not zeros."""
    zero_row = dict(course="FOUN 113", campus="SAV", projected_seats=0, sections=0, adjusted=False)
    monkeypatch.setattr(main, "run_sequence_forecast", lambda **kw: [zero_row])
    r = client.post("/api/forecast", json={"term": "Spring 2026", "method": "sequence"})
    assert r.status_code == 422
    assert "feeder" in r.json()["detail"].lower()


# --------------- Change delta ---------------------------------------------

def test_forecast_change_delta_when_previous_forecast_exists(monkeypatch, tmp_path):
    """Results include change and changePercent when a prior forecast CSV exists."""
    # The endpoint globs PROJECT_ROOT / "Data/{term}_FOUN_Forecast*.csv"
    # (PROJECT_ROOT is tmp_path, set by the autouse fixture)
    data_subdir = tmp_path / "Data"
    data_subdir.mkdir()
    (data_subdir / "Spring_2026_FOUN_Forecast_prior.csv").touch()
    # Previous run had 80 students for FOUN 110 / SAV
    monkeypatch.setattr(
        main, "load_previous_forecast",
        lambda path: {("FOUN 110", "SAV"): 80},
    )

    body = client.post("/api/forecast", json={"term": "Spring 2026"}).json()
    result = body["results"][0]
    # _FAKE_ROW projected_seats=100; prev=80 → change=20, changePercent=25.0
    assert result["change"] == 20
    assert result["changePercent"] == pytest.approx(25.0)


def test_forecast_no_change_delta_without_previous_forecast():
    """change and changePercent are null when no prior forecast CSV exists."""
    # No Data/Spring_2026_FOUN_Forecast*.csv in PROJECT_ROOT (tmp_path)
    body = client.post("/api/forecast", json={"term": "Spring 2026"}).json()
    result = body["results"][0]
    assert result.get("change") is None
    assert result.get("changePercent") is None


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


def test_historical_first_post_rollout_season_message(monkeypatch):
    """First post-rollout instance of a season (Spring 2026): the 422 must not
    tell the user to import a pre-rollout term the filter would discard."""
    monkeypatch.setattr(main, "run_sameseason_forecast", lambda **kw: [])
    r = client.post("/api/forecast", json={"term": "Spring 2026"})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "Spring 2025" not in detail            # pre-rollout; would be discarded
    assert "first post-rollout" in detail.lower()
    assert "sequence" in detail.lower()


def test_historical_missing_prior_year_names_importable_term(monkeypatch):
    """When a post-rollout prior exists but is absent from the file (Spring 2027),
    the 422 names the importable prior-year same quarter (Spring 2026)."""
    monkeypatch.setattr(main, "run_sameseason_forecast", lambda **kw: [])
    r = client.post("/api/forecast", json={"term": "Spring 2027"})
    assert r.status_code == 422
    assert "Spring 2026" in r.json()["detail"]
