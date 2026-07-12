"""Tests for POST /api/backtest calibration integrity.

Backtest measures MODEL accuracy against actuals, so the inner forecast must
exclude the planning buffer and manual adjustments, and the demand metric must
resolve identically for the forecast side and the actuals side.
"""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main
from adjustments import Adjustment, TermAdjustments

client = TestClient(main.app)

_ROW = dict(course="FOUN 110", campus="Savannah", projected_seats=100, sections=5, adjusted=False)


@pytest.fixture(autouse=True)
def patch_backtest(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "CONFIG_PATH", tmp_path / "forecast_config.json")
    monkeypatch.setattr(main, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(main, "get_available_terms", lambda *a, **k: [])
    monkeypatch.setattr(main, "load_adjustments",
                        lambda data_dir, term: TermAdjustments(term=term, adjustments=[]))

    calls = {"forecast": [], "enrollments": []}

    def fake_sameseason(**kw):
        calls["forecast"].append(kw)
        return [dict(_ROW)]

    def fake_enrollments(path, term_code=None, crosswalk=None, demand_metric=None, **kw):
        calls["enrollments"].append(dict(term_code=term_code, demand_metric=demand_metric))
        return {("SAVANNAH", "FOUN 110"): 90}

    monkeypatch.setattr(main, "run_sameseason_forecast", fake_sameseason)
    monkeypatch.setattr(main, "run_sequence_forecast", lambda **kw: [dict(_ROW)])
    monkeypatch.setattr(main, "load_term_enrollments", fake_enrollments)
    return calls


def test_backtest_inner_forecast_uses_zero_buffer(patch_backtest):
    r = client.post("/api/backtest", json={"term": "Fall 2026", "method": "historical"})
    assert r.status_code == 200
    assert patch_backtest["forecast"], "forecast was not invoked"
    assert patch_backtest["forecast"][0]["buffer_percent"] == 0


def test_backtest_excludes_output_adjustments(monkeypatch, patch_backtest):
    adj = Adjustment(id="a1", type="output", operation="multiply", value=1.5,
                     reason="planning bump", enabled=True, source="manual")
    monkeypatch.setattr(
        main, "load_adjustments",
        lambda data_dir, term: TermAdjustments(term=term, adjustments=[adj]),
    )
    body = client.post("/api/backtest", json={"term": "Fall 2026", "method": "historical"}).json()
    row = next(r for r in body["rows"] if r["course"] == "FOUN 110")
    assert row["forecast"] == pytest.approx(100.0), (
        "backtest must score the raw model output, not the adjusted forecast"
    )


def test_backtest_demand_metric_falls_back_to_disk_config(patch_backtest, tmp_path):
    (tmp_path / "forecast_config.json").write_text(json.dumps({"demand_metric": "max"}))
    body = client.post("/api/backtest", json={"term": "Fall 2026", "method": "historical"}).json()
    assert body["demandMetric"] == "max"
    # Forecast side and actuals side must both use the resolved metric.
    assert patch_backtest["forecast"][0]["demand_metric"] == "max"
    assert patch_backtest["enrollments"][-1]["demand_metric"] == "max"
