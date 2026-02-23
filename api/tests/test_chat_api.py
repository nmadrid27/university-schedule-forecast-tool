"""Tests for POST /api/chat endpoint.

Covers both the regex fallback path (no LLM) and the LLM path (mocked).
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main
from adjustments import TermAdjustments

client = TestClient(main.app)


def _empty_adjustments(data_dir, term):
    return TermAdjustments(term=term, adjustments=[])


@pytest.fixture(autouse=True)
def no_llm(monkeypatch, tmp_path):
    """Default: no LLM configured, isolated data dir."""
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "CONFIG_PATH", tmp_path / "forecast_config.json")
    monkeypatch.setattr(main, "create_llm_service", lambda cfg: None)
    monkeypatch.setattr(main, "load_adjustments", _empty_adjustments)


# ─── Regex path ──────────────────────────────────────────────────────────────

def test_chat_returns_200():
    r = client.post("/api/chat", json={"message": "help"})
    assert r.status_code == 200


def test_chat_response_shape():
    body = client.post("/api/chat", json={"message": "help"}).json()
    assert "message" in body
    assert "parsedCommand" in body
    assert body["llm_used"] is False


def test_chat_parsed_command_has_required_keys():
    body = client.post("/api/chat", json={"message": "forecast"}).json()
    pc = body["parsedCommand"]
    assert "intent" in pc
    assert "parameters" in pc
    assert "confidence" in pc


def test_chat_detects_forecast_intent():
    body = client.post("/api/chat", json={"message": "forecast spring 2026"}).json()
    assert body["parsedCommand"]["intent"] == "forecast"


def test_chat_detects_help_intent():
    body = client.post("/api/chat", json={"message": "help"}).json()
    assert body["parsedCommand"]["intent"] == "help"


def test_chat_detects_settings_intent():
    body = client.post("/api/chat", json={"message": "change capacity"}).json()
    assert body["parsedCommand"]["intent"] == "settings"


def test_chat_unknown_intent_for_gibberish():
    body = client.post("/api/chat", json={"message": "asdfghjkl xyz"}).json()
    assert body["parsedCommand"]["intent"] == "unknown"


def test_chat_no_adjustments_in_regex_response():
    body = client.post("/api/chat", json={"message": "forecast"}).json()
    # Regex path never returns adjustments
    assert body.get("adjustments") is None


# ─── LLM path ────────────────────────────────────────────────────────────────

def _make_mock_llm(intent, response_text, adjustments=None, confidence=0.9):
    mock = MagicMock()
    mock.is_configured.return_value = True
    mock.parse_message = AsyncMock(return_value={
        "intent": intent,
        "parameters": {},
        "confidence": confidence,
        "response_text": response_text,
        "adjustments": adjustments or [],
    })
    return mock


def test_chat_llm_used_is_true_when_llm_configured(monkeypatch):
    monkeypatch.setattr(main, "create_llm_service",
                        lambda cfg: _make_mock_llm("forecast", "I'll run the forecast."))
    body = client.post("/api/chat", json={"message": "forecast spring 2026"}).json()
    assert body["llm_used"] is True


def test_chat_llm_intent_forwarded_to_response(monkeypatch):
    monkeypatch.setattr(main, "create_llm_service",
                        lambda cfg: _make_mock_llm("forecast", "Here are the results."))
    body = client.post("/api/chat", json={"message": "forecast"}).json()
    assert body["parsedCommand"]["intent"] == "forecast"


def test_chat_llm_response_text_in_message(monkeypatch):
    monkeypatch.setattr(main, "create_llm_service",
                        lambda cfg: _make_mock_llm("help", "I can help you forecast."))
    body = client.post("/api/chat", json={"message": "help"}).json()
    assert body["message"] == "I can help you forecast."


def test_chat_llm_adjustments_returned_and_persisted(monkeypatch):
    monkeypatch.setattr(
        main, "create_llm_service",
        lambda cfg: _make_mock_llm(
            intent="adjust",
            response_text="Added buffer.",
            adjustments=[{"type": "output", "operation": "multiply",
                          "value": 1.1, "reason": "buffer", "scope": {}}],
        ),
    )
    saved = []
    monkeypatch.setattr(main, "add_adjustment", lambda data_dir, term, adj: saved.append(adj))

    body = client.post("/api/chat", json={"message": "add 10% buffer"}).json()
    assert len(body["adjustments"]) == 1
    assert len(saved) == 1


def test_chat_llm_unknown_intent_with_adjustments_promoted_to_adjust(monkeypatch):
    """When LLM returns 'unknown' but extracted adjustments, intent → 'adjust'."""
    monkeypatch.setattr(
        main, "create_llm_service",
        lambda cfg: _make_mock_llm(
            intent="unknown",
            response_text="Applied adjustment.",
            adjustments=[{"type": "output", "operation": "add",
                          "value": 5, "reason": "extra", "scope": {}}],
            confidence=0.3,
        ),
    )
    monkeypatch.setattr(main, "add_adjustment", lambda *a: None)

    body = client.post("/api/chat", json={"message": "add 5 seats"}).json()
    assert body["parsedCommand"]["intent"] == "adjust"
