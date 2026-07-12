"""Tests for GET /api/config and PUT /api/config endpoints."""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Point CONFIG_PATH at a temp file for every test."""
    cfg_file = tmp_path / "forecast_config.json"
    monkeypatch.setattr(main, "CONFIG_PATH", cfg_file)
    return cfg_file


# ─── GET /api/config ──────────────────────────────────────────────────────────

def test_get_config_returns_defaults_when_no_file_exists():
    r = client.get("/api/config")
    assert r.status_code == 200
    body = r.json()
    assert body["capacity"] == 20
    assert body["progressionRate"] == pytest.approx(0.95)
    assert body["bufferPercent"] == pytest.approx(10.0)
    assert body["quartersToForecast"] == 2


def test_get_config_reads_values_from_disk(isolated_config):
    isolated_config.write_text(json.dumps({
        "capacity": 25,
        "progression_rate": 0.9,
        "buffer_percent": 15.0,
        "quarters_to_forecast": 3,
        "default_term": "Fall 2026",
    }))
    r = client.get("/api/config")
    assert r.status_code == 200
    body = r.json()
    assert body["capacity"] == 25
    assert body["progressionRate"] == pytest.approx(0.9)
    assert body["bufferPercent"] == pytest.approx(15.0)
    assert body["quartersToForecast"] == 3
    assert body["defaultTerm"] == "Fall 2026"


def test_get_config_uses_camelcase_keys():
    r = client.get("/api/config")
    body = r.json()
    assert "progressionRate" in body
    assert "bufferPercent" in body
    assert "quartersToForecast" in body


# ─── PUT /api/config ──────────────────────────────────────────────────────────

def test_put_config_returns_success():
    r = client.put("/api/config", json={
        "capacity": 24, "progressionRate": 0.9,
        "bufferPercent": 12.0, "quartersToForecast": 2, "defaultTerm": "Spring 2026",
    })
    assert r.status_code == 200
    assert r.json()["success"] is True


def test_put_config_persists_all_fields_to_disk(isolated_config):
    client.put("/api/config", json={
        "capacity": 30, "progressionRate": 0.85,
        "bufferPercent": 20.0, "quartersToForecast": 4, "defaultTerm": "Fall 2026",
    })
    saved = json.loads(isolated_config.read_text())
    assert saved["capacity"] == 30
    assert saved["progression_rate"] == pytest.approx(0.85)
    assert saved["buffer_percent"] == pytest.approx(20.0)
    assert saved["quarters_to_forecast"] == 4
    assert saved["default_term"] == "Fall 2026"


def test_put_then_get_round_trip():
    payload = {
        "capacity": 18, "progressionRate": 0.88,
        "bufferPercent": 5.0, "quartersToForecast": 3, "defaultTerm": "Winter 2027",
    }
    client.put("/api/config", json=payload)
    r = client.get("/api/config")
    body = r.json()
    assert body["capacity"] == 18
    assert body["progressionRate"] == pytest.approx(0.88)
    assert body["bufferPercent"] == pytest.approx(5.0)
    assert body["quartersToForecast"] == 3
    assert body["defaultTerm"] == "Winter 2027"


# ─── Validation bounds ────────────────────────────────────────────────────────

@pytest.mark.parametrize("field,bad_value", [
    ("capacity", 0),          # ge=1
    ("capacity", 101),         # le=100
    ("progressionRate", -0.1), # ge=0.0
    ("progressionRate", 1.1),  # le=1.0
    ("bufferPercent", -1.0),   # ge=0.0
    ("bufferPercent", 101.0),  # le=100.0
    ("quartersToForecast", 0), # ge=1
    ("quartersToForecast", 9), # le=8
])
def test_put_config_rejects_out_of_range_values(field, bad_value):
    payload = {
        "capacity": 20, "progressionRate": 0.95,
        "bufferPercent": 10.0, "quartersToForecast": 2, "defaultTerm": "Spring 2026",
    }
    payload[field] = bad_value
    r = client.put("/api/config", json=payload)
    assert r.status_code == 422


def test_partial_config_put_preserves_method_and_metric(isolated_config):
    """A PUT that omits method/demandMetric must not clobber the values a user
    deliberately set on disk (stale clients send only the classic fields)."""
    isolated_config.write_text(json.dumps({
        "capacity": 20,
        "method": "sequence",
        "demand_metric": "max",
    }))
    r = client.put("/api/config", json={"capacity": 25})
    assert r.status_code == 200
    saved = json.loads(isolated_config.read_text())
    assert saved["capacity"] == 25
    assert saved["method"] == "sequence"
    assert saved["demand_metric"] == "max"
