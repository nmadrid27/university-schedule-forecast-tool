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
    body = client.post("/api/forecast", json={"term": "Spring 2026"}).json()
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
    client.post("/api/forecast", json={"term": "Spring 2026", "config": {"capacity": 30}})
    assert calls[0]["capacity"] == 30


def test_forecast_respects_progression_rate_override(monkeypatch):
    calls = []

    def capture(**kw):
        calls.append(kw)
        return [_FAKE_ROW]

    monkeypatch.setattr(main, "run_sequence_forecast", capture)
    client.post("/api/forecast", json={
        "term": "Spring 2026",
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
    r = client.post("/api/forecast", json={"term": "Spring 2026"})
    assert r.status_code == 404


def test_forecast_returns_400_on_value_error(monkeypatch):
    monkeypatch.setattr(
        main, "run_sequence_forecast",
        lambda **kw: (_ for _ in ()).throw(ValueError("bad value")),
    )
    r = client.post("/api/forecast", json={"term": "Spring 2026"})
    assert r.status_code == 400


def test_forecast_returns_500_on_unexpected_error(monkeypatch):
    monkeypatch.setattr(
        main, "run_sequence_forecast",
        lambda **kw: (_ for _ in ()).throw(RuntimeError("unexpected")),
    )
    r = client.post("/api/forecast", json={"term": "Spring 2026"})
    assert r.status_code == 500
