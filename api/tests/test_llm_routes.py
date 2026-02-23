"""Tests for GET /api/llm/status and PUT /api/llm/config routes."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    """Redirect CONFIG_PATH and ENV_FILE for every test."""
    monkeypatch.setattr(main, "CONFIG_PATH", tmp_path / "forecast_config.json")
    # Patch the ENV_FILE in llm_service so key lookups don't hit the real file
    import llm_service
    monkeypatch.setattr(llm_service, "ENV_FILE", tmp_path / ".env.local")
    # Clear LLM_API_KEY env var so tests are deterministic
    monkeypatch.delenv("LLM_API_KEY", raising=False)


# ─── GET /api/llm/status ─────────────────────────────────────────────────

def test_llm_status_returns_200():
    r = client.get("/api/llm/status")
    assert r.status_code == 200


def test_llm_status_response_shape():
    body = client.get("/api/llm/status").json()
    assert "provider" in body
    assert "model" in body
    assert "has_key" in body
    assert "configured" in body


def test_llm_status_not_configured_when_no_config():
    # No config file → defaults to provider=none → not configured
    body = client.get("/api/llm/status").json()
    assert body["provider"] == "none"
    assert body["configured"] is False


def test_llm_status_configured_when_ollama(tmp_path, monkeypatch):
    cfg = tmp_path / "forecast_config.json"
    cfg.write_text(json.dumps({"llm": {"provider": "ollama", "model": "llama3.2"}}))
    monkeypatch.setattr(main, "CONFIG_PATH", cfg)
    body = client.get("/api/llm/status").json()
    assert body["provider"] == "ollama"
    assert body["configured"] is True  # Ollama needs no key


def test_llm_status_not_configured_without_key(tmp_path, monkeypatch):
    cfg = tmp_path / "forecast_config.json"
    cfg.write_text(json.dumps({"llm": {"provider": "anthropic", "model": "claude-haiku"}}))
    monkeypatch.setattr(main, "CONFIG_PATH", cfg)
    body = client.get("/api/llm/status").json()
    assert body["provider"] == "anthropic"
    assert body["configured"] is False  # key not present


def test_llm_status_never_returns_api_key():
    body = client.get("/api/llm/status").json()
    assert "api_key" not in body


# ─── PUT /api/llm/config ─────────────────────────────────────────────────

def test_put_llm_config_returns_200():
    r = client.put("/api/llm/config", json={"provider": "none"})
    assert r.status_code == 200


def test_put_llm_config_response_has_success_true():
    body = client.put("/api/llm/config", json={"provider": "ollama"}).json()
    assert body["success"] is True


def test_put_llm_config_persists_provider(tmp_path, monkeypatch):
    cfg = tmp_path / "forecast_config.json"
    monkeypatch.setattr(main, "CONFIG_PATH", cfg)
    client.put("/api/llm/config", json={"provider": "ollama", "model": "llama3.2"})
    saved = json.loads(cfg.read_text())
    assert saved["llm"]["provider"] == "ollama"
    assert saved["llm"]["model"] == "llama3.2"


def test_put_llm_config_saves_api_key_to_env_file(tmp_path, monkeypatch):
    import llm_service
    env_file = tmp_path / ".env.local"
    monkeypatch.setattr(llm_service, "ENV_FILE", env_file)
    client.put("/api/llm/config", json={"provider": "anthropic", "api_key": "sk-test-123"})
    assert "LLM_API_KEY=sk-test-123" in env_file.read_text()


def test_put_llm_config_does_not_save_key_to_config_json(tmp_path, monkeypatch):
    cfg = tmp_path / "forecast_config.json"
    monkeypatch.setattr(main, "CONFIG_PATH", cfg)
    client.put("/api/llm/config", json={"provider": "anthropic", "api_key": "secret"})
    saved_text = cfg.read_text()
    assert "secret" not in saved_text
    assert "api_key" not in saved_text


def test_put_then_get_round_trip(tmp_path, monkeypatch):
    cfg = tmp_path / "forecast_config.json"
    monkeypatch.setattr(main, "CONFIG_PATH", cfg)
    client.put("/api/llm/config", json={"provider": "ollama", "model": "llama3.2",
                                        "base_url": "http://localhost:11434/v1"})
    body = client.get("/api/llm/status").json()
    assert body["provider"] == "ollama"
    assert body["model"] == "llama3.2"
