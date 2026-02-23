"""Tests for build_system_prompt — config and adjustment injection into LLM prompt."""

from api.llm_service import build_system_prompt


def test_injects_config_values_into_prompt():
    config = {
        "capacity": 25,
        "progression_rate": 0.90,
        "buffer_percent": 15.0,
        "default_term": "Fall 2026",
    }

    prompt = build_system_prompt(config, active_adjustments=[])

    assert "25 students/section" in prompt
    assert "0.9" in prompt
    assert "15.0%" in prompt
    assert "Fall 2026" in prompt


def test_uses_defaults_when_config_keys_missing():
    prompt = build_system_prompt({}, active_adjustments=[])

    assert "20 students/section" in prompt
    assert "0.95" in prompt
    assert "10.0%" in prompt
    assert "Spring 2026" in prompt


def test_shows_none_active_when_no_adjustments():
    prompt = build_system_prompt({"capacity": 20}, active_adjustments=[])

    assert "None currently active." in prompt


def test_formats_config_adjustment_with_full_scope():
    adjustment = {
        "type": "config",
        "parameter": "capacity",
        "value": 25,
        "scope": {"course": "FOUN 110", "campus": "Savannah"},
        "reason": "Larger room available",
    }

    prompt = build_system_prompt({}, active_adjustments=[adjustment])

    assert "capacity = 25 [FOUN 110, Savannah]: Larger room available" in prompt


def test_formats_output_adjustment_with_operation():
    adjustment = {
        "type": "output",
        "operation": "multiply",
        "value": 1.1,
        "scope": {"course": "FOUN 230"},
        "reason": "Expecting more retakes",
    }

    prompt = build_system_prompt({}, active_adjustments=[adjustment])

    assert "multiply 1.1 [FOUN 230]: Expecting more retakes" in prompt


def test_scope_with_campus_only():
    adjustment = {
        "type": "output",
        "operation": "add",
        "value": 10,
        "scope": {"campus": "SCADnow"},
        "reason": "Online surge",
    }

    prompt = build_system_prompt({}, active_adjustments=[adjustment])

    assert "[SCADnow]" in prompt


def test_scope_omitted_when_empty():
    adjustment = {
        "type": "config",
        "parameter": "buffer_percent",
        "value": 20,
        "scope": {},
        "reason": "Global buffer increase",
    }

    prompt = build_system_prompt({}, active_adjustments=[adjustment])

    # No bracket notation should appear for this adjustment
    assert "buffer_percent = 20: Global buffer increase" in prompt
    assert "[]" not in prompt


def test_multiple_adjustments_all_appear_in_prompt():
    adjustments = [
        {"type": "config", "parameter": "capacity", "value": 22, "scope": {}, "reason": ""},
        {"type": "output", "operation": "multiply", "value": 1.05, "scope": {}, "reason": ""},
    ]

    prompt = build_system_prompt({}, active_adjustments=adjustments)

    assert "capacity = 22" in prompt
    assert "multiply 1.05" in prompt
