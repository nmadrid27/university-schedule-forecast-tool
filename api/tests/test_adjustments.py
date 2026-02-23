"""Tests for adjustment CRUD endpoints and application functions."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402
from adjustments import (  # noqa: E402
    Adjustment,
    apply_config_adjustments,
    apply_output_adjustments,
)

client = TestClient(main.app)

TERM = "Spring 2026"
TERM_ENCODED = "Spring%202026"


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Redirect DATA_DIR to a temp directory for every test."""
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    return tmp_path


# ─── GET /api/adjustments/{term} ──────────────────────────────────────────────

def test_get_adjustments_returns_empty_list_for_new_term():
    r = client.get(f"/api/adjustments/{TERM_ENCODED}")
    assert r.status_code == 200
    assert r.json()["adjustments"] == []
    assert r.json()["term"] == TERM


# ─── POST /api/adjustments/{term} ─────────────────────────────────────────────

def test_post_creates_adjustment_and_returns_it():
    r = client.post(f"/api/adjustments/{TERM_ENCODED}", json={
        "type": "output",
        "operation": "multiply",
        "value": 1.1,
        "reason": "More retakes expected",
    })
    assert r.status_code == 200
    adj = r.json()["adjustment"]
    assert adj["type"] == "output"
    assert adj["operation"] == "multiply"
    assert adj["value"] == pytest.approx(1.1)
    assert adj["enabled"] is True
    assert adj["source"] == "manual"
    assert "id" in adj


def test_post_persists_adjustment_visible_on_get():
    client.post(f"/api/adjustments/{TERM_ENCODED}", json={
        "type": "output", "operation": "add", "value": 5, "reason": "Extra demand",
    })
    r = client.get(f"/api/adjustments/{TERM_ENCODED}")
    assert len(r.json()["adjustments"]) == 1
    assert r.json()["adjustments"][0]["value"] == pytest.approx(5)


def test_post_multiple_adjustments_all_appear_on_get():
    client.post(f"/api/adjustments/{TERM_ENCODED}", json={
        "type": "output", "operation": "multiply", "value": 1.1, "reason": "A",
    })
    client.post(f"/api/adjustments/{TERM_ENCODED}", json={
        "type": "config", "parameter": "capacity", "value": 25, "reason": "B",
    })
    r = client.get(f"/api/adjustments/{TERM_ENCODED}")
    assert len(r.json()["adjustments"]) == 2


# ─── PUT /api/adjustments/{term}/{id}/toggle ──────────────────────────────────

def test_toggle_flips_adjustment_from_enabled_to_disabled():
    r = client.post(f"/api/adjustments/{TERM_ENCODED}", json={
        "type": "output", "operation": "multiply", "value": 1.2, "reason": "Bump",
    })
    adj_id = r.json()["adjustment"]["id"]

    r2 = client.put(f"/api/adjustments/{TERM_ENCODED}/{adj_id}/toggle")
    assert r2.status_code == 200
    toggled = next(a for a in r2.json()["adjustments"] if a["id"] == adj_id)
    assert toggled["enabled"] is False


def test_toggle_twice_restores_original_state():
    r = client.post(f"/api/adjustments/{TERM_ENCODED}", json={
        "type": "output", "operation": "add", "value": 3, "reason": "Test",
    })
    adj_id = r.json()["adjustment"]["id"]

    client.put(f"/api/adjustments/{TERM_ENCODED}/{adj_id}/toggle")
    r2 = client.put(f"/api/adjustments/{TERM_ENCODED}/{adj_id}/toggle")
    toggled = next(a for a in r2.json()["adjustments"] if a["id"] == adj_id)
    assert toggled["enabled"] is True


# ─── DELETE /api/adjustments/{term}/{id} ──────────────────────────────────────

def test_delete_removes_adjustment_from_list():
    r = client.post(f"/api/adjustments/{TERM_ENCODED}", json={
        "type": "output", "operation": "set", "value": 40, "reason": "Cap",
    })
    adj_id = r.json()["adjustment"]["id"]

    r2 = client.delete(f"/api/adjustments/{TERM_ENCODED}/{adj_id}")
    assert r2.status_code == 200
    assert r2.json()["adjustments"] == []


def test_delete_only_removes_targeted_adjustment():
    r1 = client.post(f"/api/adjustments/{TERM_ENCODED}", json={
        "type": "output", "operation": "multiply", "value": 1.1, "reason": "A",
    })
    client.post(f"/api/adjustments/{TERM_ENCODED}", json={
        "type": "output", "operation": "add", "value": 2, "reason": "B",
    })
    adj_id = r1.json()["adjustment"]["id"]

    r2 = client.delete(f"/api/adjustments/{TERM_ENCODED}/{adj_id}")
    remaining = r2.json()["adjustments"]
    assert len(remaining) == 1
    assert remaining[0]["id"] != adj_id


# ─── apply_config_adjustments ─────────────────────────────────────────────────

def _adj(**kwargs) -> Adjustment:
    defaults = dict(type="config", value=20, enabled=True, source="manual", reason="")
    defaults.update(kwargs)
    return Adjustment(**defaults)


def test_config_no_adjustments_returns_original_values():
    result = apply_config_adjustments([], capacity=20, progression_rate=0.95, buffer_percent=10)
    assert result == {"capacity": 20, "progression_rate": 0.95, "buffer_percent": 10.0}


def test_config_capacity_adjustment_is_applied():
    adjs = [_adj(parameter="capacity", value=30)]
    result = apply_config_adjustments(adjs, capacity=20, progression_rate=0.95, buffer_percent=10)
    assert result["capacity"] == 30


def test_config_progression_rate_adjustment_is_applied():
    adjs = [_adj(parameter="progression_rate", value=0.8)]
    result = apply_config_adjustments(adjs, capacity=20, progression_rate=0.95, buffer_percent=10)
    assert result["progression_rate"] == pytest.approx(0.8)


def test_config_disabled_adjustment_is_skipped():
    adjs = [_adj(parameter="capacity", value=99, enabled=False)]
    result = apply_config_adjustments(adjs, capacity=20, progression_rate=0.95, buffer_percent=10)
    assert result["capacity"] == 20


def test_config_scoped_adjustment_is_not_applied_globally():
    """Scoped config adjustments are reserved for output-level processing."""
    from adjustments import AdjustmentScope
    adjs = [_adj(parameter="capacity", value=40, scope=AdjustmentScope(course="FOUN 110"))]
    result = apply_config_adjustments(adjs, capacity=20, progression_rate=0.95, buffer_percent=10)
    assert result["capacity"] == 20


def test_config_capacity_clamped_to_max_100():
    adjs = [_adj(parameter="capacity", value=999)]
    result = apply_config_adjustments(adjs, capacity=20, progression_rate=0.95, buffer_percent=10)
    assert result["capacity"] == 100


# ─── apply_output_adjustments ─────────────────────────────────────────────────

def _row(course="FOUN 110", campus="SAV", seats=100, sections=5):
    return {"course": course, "campus": campus, "projected_seats": seats, "sections": sections}


def _out_adj(**kwargs) -> Adjustment:
    defaults = dict(type="output", operation="multiply", value=1.0, enabled=True,
                    source="manual", reason="")
    defaults.update(kwargs)
    return Adjustment(**defaults)


def test_output_no_adjustments_rows_unchanged_with_adjusted_false():
    rows = [_row()]
    result = apply_output_adjustments([], rows, capacity=20)
    assert result[0]["projected_seats"] == 100
    assert result[0]["adjusted"] is False


def test_output_multiply_scales_seats_and_recalculates_sections():
    rows = [_row(seats=100, sections=5)]
    adjs = [_out_adj(operation="multiply", value=1.2)]
    result = apply_output_adjustments(adjs, rows, capacity=20)
    assert result[0]["projected_seats"] == pytest.approx(120)
    assert result[0]["sections"] == 6   # ceil(120/20)
    assert result[0]["adjusted"] is True


def test_output_add_increases_seats():
    rows = [_row(seats=100)]
    adjs = [_out_adj(operation="add", value=10)]
    result = apply_output_adjustments(adjs, rows, capacity=20)
    assert result[0]["projected_seats"] == pytest.approx(110)


def test_output_set_overrides_seats():
    rows = [_row(seats=100)]
    adjs = [_out_adj(operation="set", value=40)]
    result = apply_output_adjustments(adjs, rows, capacity=20)
    assert result[0]["projected_seats"] == pytest.approx(40)
    assert result[0]["sections"] == 2   # ceil(40/20)


def test_output_disabled_adjustment_not_applied():
    rows = [_row(seats=100)]
    adjs = [_out_adj(operation="multiply", value=2.0, enabled=False)]
    result = apply_output_adjustments(adjs, rows, capacity=20)
    assert result[0]["projected_seats"] == 100
    assert result[0]["adjusted"] is False


def test_output_course_scoped_only_matches_correct_course():
    from adjustments import AdjustmentScope
    rows = [_row(course="FOUN 110", seats=100), _row(course="FOUN 120", seats=80)]
    adjs = [_out_adj(operation="multiply", value=1.5,
                     scope=AdjustmentScope(course="FOUN 110"))]
    result = apply_output_adjustments(adjs, rows, capacity=20)
    assert result[0]["projected_seats"] == pytest.approx(150)
    assert result[0]["adjusted"] is True
    assert result[1]["projected_seats"] == 80
    assert result[1]["adjusted"] is False


def test_output_campus_scoped_only_matches_correct_campus():
    from adjustments import AdjustmentScope
    rows = [_row(campus="SAV", seats=100), _row(campus="NOW", seats=60)]
    adjs = [_out_adj(operation="add", value=20, scope=AdjustmentScope(campus="NOW"))]
    result = apply_output_adjustments(adjs, rows, capacity=20)
    assert result[0]["projected_seats"] == 100
    assert result[1]["projected_seats"] == pytest.approx(80)
