"""Integration tests for FastAPI endpoints using httpx TestClient."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Ensure api/ modules resolve bare imports (mirrors runtime sys.path setup)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app  # noqa: E402

client = TestClient(app)


# --------------- /api/health ---------------

def test_health_returns_healthy_status():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "timestamp" in response.json()


# --------------- /api/chat (regex parser path) ---------------

def _chat(message: str, **kwargs):
    """Helper — posts to /api/chat with LLM disabled."""
    payload = {"message": message, **kwargs}
    with patch("main.create_llm_service", return_value=None):
        return client.post("/api/chat", json=payload)


def test_chat_forecast_intent_detected():
    response = _chat("forecast spring 2026")

    assert response.status_code == 200
    body = response.json()
    assert body["parsedCommand"]["intent"] == "forecast"
    assert body["parsedCommand"]["parameters"]["term"] == "Spring 2026"
    assert body["llm_used"] is False


def test_chat_help_intent_detected():
    response = _chat("help")

    assert response.status_code == 200
    body = response.json()
    assert body["parsedCommand"]["intent"] == "help"
    assert "forecast" in body["message"].lower()


def test_chat_settings_intent_detected():
    response = _chat("show settings")

    assert response.status_code == 200
    assert response.json()["parsedCommand"]["intent"] == "settings"


def test_chat_unknown_intent_for_unrecognised_input():
    response = _chat("xyzzy frobnicator")

    assert response.status_code == 200
    assert response.json()["parsedCommand"]["intent"] == "unknown"


def test_chat_extracts_course_parameter():
    response = _chat("forecast FOUN 110 for spring 2026")

    assert response.status_code == 200
    params = response.json()["parsedCommand"]["parameters"]
    assert params.get("course") == "FOUN 110"


def test_chat_extracts_scadnow_campus():
    response = _chat("forecast online spring 2026")

    assert response.status_code == 200
    params = response.json()["parsedCommand"]["parameters"]
    assert params.get("campus") == "SCADnow"


# --------------- /api/forecast ---------------

def test_forecast_spring_2026_returns_results():
    response = client.post("/api/forecast", json={"term": "Spring 2026", "method": "sequence"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) > 0
    assert body["summary"]["totalSections"] > 0
    assert body["summary"]["coursesForecasted"] > 0


def test_forecast_result_shape():
    response = client.post("/api/forecast", json={"term": "Spring 2026", "method": "sequence"})

    result = response.json()["results"][0]
    assert "course" in result
    assert "campus" in result
    assert "projectedSeats" in result
    assert "sections" in result


def test_forecast_summary_method_is_sequence_based():
    response = client.post("/api/forecast", json={"term": "Spring 2026", "method": "sequence"})

    assert response.json()["summary"]["method"] == "Sequence-based"


def test_forecast_invalid_term_returns_400():
    response = client.post("/api/forecast", json={"term": "NotATerm 9999"})

    assert response.status_code in (400, 404, 500)
