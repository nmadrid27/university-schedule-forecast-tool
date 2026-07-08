"""Tests for LLMService class, create_llm_service, load_api_key, save_api_key.

parse_llm_response is already covered in test_llm_service.py.
build_system_prompt is already covered in test_llm_service_prompt.py.
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import llm_service as svc_mod
from llm_service import (
    LLMService,
    create_llm_service,
    load_api_key,
    save_api_key,
)


# ─── load_api_key ─────────────────────────────────────────────────────────

class TestLoadApiKey:
    def test_reads_from_env_var(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "env-key-xyz")
        assert load_api_key() == "env-key-xyz"

    def test_reads_from_settings_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({"LLM_API_KEY": "file-key-abc"}))
        monkeypatch.setattr(svc_mod, "settings_path", lambda: settings)
        assert load_api_key() == "file-key-abc"

    def test_returns_none_on_malformed_settings(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        settings = tmp_path / "settings.json"
        settings.write_text("{ not valid json")
        monkeypatch.setattr(svc_mod, "settings_path", lambda: settings)
        assert load_api_key() is None

    def test_returns_none_when_no_env_var_and_no_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.setattr(svc_mod, "settings_path", lambda: tmp_path / "settings.json")
        assert load_api_key() is None

    def test_env_var_takes_priority_over_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "env-wins")
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({"LLM_API_KEY": "file-key"}))
        monkeypatch.setattr(svc_mod, "settings_path", lambda: settings)
        assert load_api_key() == "env-wins"


# ─── save_api_key ─────────────────────────────────────────────────────────

class TestSaveApiKey:
    def test_creates_file_when_not_exists(self, tmp_path, monkeypatch):
        settings = tmp_path / "settings.json"
        monkeypatch.setattr(svc_mod, "settings_path", lambda: settings)
        save_api_key("new-key")
        assert json.loads(settings.read_text())["LLM_API_KEY"] == "new-key"

    def test_updates_existing_key(self, tmp_path, monkeypatch):
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({"LLM_API_KEY": "old-key"}))
        monkeypatch.setattr(svc_mod, "settings_path", lambda: settings)
        save_api_key("updated-key")
        assert json.loads(settings.read_text())["LLM_API_KEY"] == "updated-key"

    def test_preserves_other_settings(self, tmp_path, monkeypatch):
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({"OTHER_VAR": "keep-me", "LLM_API_KEY": "old"}))
        monkeypatch.setattr(svc_mod, "settings_path", lambda: settings)
        save_api_key("new-key")
        saved = json.loads(settings.read_text())
        assert saved["OTHER_VAR"] == "keep-me"
        assert saved["LLM_API_KEY"] == "new-key"


# ─── LLMService.is_configured ─────────────────────────────────────────────

class TestIsConfigured:
    def test_openai_with_key_is_configured(self):
        service = LLMService(provider="openai", api_key="sk-test")
        assert service.is_configured() is True

    def test_openai_without_key_not_configured(self, monkeypatch):
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.setattr(svc_mod, "settings_path", lambda: Path("/nonexistent/settings.json"))
        service = LLMService(provider="openai")
        assert service.is_configured() is False

    def test_anthropic_with_key_is_configured(self):
        service = LLMService(provider="anthropic", api_key="sk-ant-test")
        assert service.is_configured() is True

    def test_anthropic_without_key_not_configured(self, monkeypatch):
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.setattr(svc_mod, "settings_path", lambda: Path("/nonexistent/settings.json"))
        service = LLMService(provider="anthropic")
        assert service.is_configured() is False

    def test_ollama_always_configured_no_key_needed(self, monkeypatch):
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.setattr(svc_mod, "settings_path", lambda: Path("/nonexistent/settings.json"))
        service = LLMService(provider="ollama")
        assert service.is_configured() is True

    def test_picks_up_default_model_for_known_provider(self):
        service = LLMService(provider="openai", api_key="sk-test")
        assert service.model == "gpt-4o-mini"

    def test_custom_model_overrides_default(self):
        service = LLMService(provider="openai", model="gpt-4o", api_key="sk-test")
        assert service.model == "gpt-4o"


# ─── create_llm_service ───────────────────────────────────────────────────

class TestCreateLLMService:
    def test_returns_none_for_provider_none(self):
        assert create_llm_service({"llm": {"provider": "none"}}) is None

    def test_returns_none_when_no_llm_section(self):
        assert create_llm_service({}) is None

    def test_returns_llm_service_for_openai(self):
        result = create_llm_service({"llm": {"provider": "openai", "model": "gpt-4o-mini"}})
        assert isinstance(result, LLMService)
        assert result.provider == "openai"
        assert result.model == "gpt-4o-mini"

    def test_returns_llm_service_for_anthropic(self):
        result = create_llm_service({"llm": {"provider": "anthropic"}})
        assert isinstance(result, LLMService)
        assert result.provider == "anthropic"

    def test_uses_default_model_when_none_in_config(self):
        result = create_llm_service({"llm": {"provider": "anthropic"}})
        assert result is not None
        assert result.model is not None  # default filled in

    def test_passes_base_url_to_service(self):
        result = create_llm_service({
            "llm": {"provider": "ollama", "base_url": "http://myhost:11434/v1"}
        })
        assert result is not None
        assert result.base_url == "http://myhost:11434/v1"


# ─── parse_message (mocked HTTP clients) ──────────────────────────────────

_VALID_JSON = (
    '{"intent": "forecast", "parameters": {"term": "Spring 2026"}, '
    '"adjustments": [], "confidence": 0.9}'
)


class TestParseMessage:
    @pytest.mark.asyncio
    async def test_anthropic_path_returns_parsed_intent(self):
        service = LLMService(provider="anthropic", api_key="sk-ant-test")

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text=_VALID_JSON)]

        with patch("anthropic.AsyncAnthropic") as MockClass:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_resp)
            MockClass.return_value = mock_client

            result = await service.parse_message("forecast spring 2026", [], {}, [])

        assert result["intent"] == "forecast"
        assert result["parameters"]["term"] == "Spring 2026"

    @pytest.mark.asyncio
    async def test_openai_path_returns_parsed_intent(self):
        service = LLMService(provider="openai", api_key="sk-test")

        mock_choice = MagicMock()
        mock_choice.message.content = _VALID_JSON
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]

        with patch("openai.AsyncOpenAI") as MockClass:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
            MockClass.return_value = mock_client

            result = await service.parse_message("forecast spring 2026", [], {}, [])

        assert result["intent"] == "forecast"

    @pytest.mark.asyncio
    async def test_anthropic_api_error_returns_fallback(self):
        service = LLMService(provider="anthropic", api_key="sk-ant-test")

        with patch("anthropic.AsyncAnthropic") as MockClass:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(
                side_effect=Exception("connection refused")
            )
            MockClass.return_value = mock_client

            result = await service.parse_message("hello", [], {}, [])

        assert result["intent"] == "unknown"
        assert result["confidence"] == 0.0
        assert "error" in result

    @pytest.mark.asyncio
    async def test_openai_api_error_returns_fallback(self):
        service = LLMService(provider="openai", api_key="sk-test")

        with patch("openai.AsyncOpenAI") as MockClass:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=Exception("timeout")
            )
            MockClass.return_value = mock_client

            result = await service.parse_message("hello", [], {}, [])

        assert result["intent"] == "unknown"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_ollama_base_url_passed_to_openai_client(self):
        """Ollama uses _call_openai_compatible; base_url must reach AsyncOpenAI kwargs."""
        service = LLMService(provider="ollama", base_url="http://localhost:11434/v1")

        mock_choice = MagicMock()
        mock_choice.message.content = _VALID_JSON
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        captured_kwargs: dict = {}

        def capture_init(**kw):
            captured_kwargs.update(kw)
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
            return mock_client

        with patch("openai.AsyncOpenAI", side_effect=capture_init):
            await service.parse_message("forecast", [], {}, [])

        assert captured_kwargs.get("base_url") == "http://localhost:11434/v1"

    @pytest.mark.asyncio
    async def test_history_capped_at_20_for_openai_compatible(self):
        """_call_openai_compatible slices history to [-20:] before sending."""
        service = LLMService(provider="openai", api_key="sk-test")

        mock_choice = MagicMock()
        mock_choice.message.content = _VALID_JSON
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        captured_messages: list = []

        async def capture(**kw):
            captured_messages.extend(kw.get("messages", []))
            return mock_resp

        with patch("openai.AsyncOpenAI") as MockClass:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = capture
            MockClass.return_value = mock_client

            long_history = [
                {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
                for i in range(25)
            ]
            await service.parse_message("current message", long_history, {}, [])

        # system (1) + history capped at 20 + current (1) = 22 messages max
        assert len(captured_messages) <= 22

    @pytest.mark.asyncio
    async def test_history_is_included_in_anthropic_messages(self):
        service = LLMService(provider="anthropic", api_key="sk-ant-test")

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text=_VALID_JSON)]
        captured_kwargs = {}

        async def capture(**kw):
            captured_kwargs.update(kw)
            return mock_resp

        with patch("anthropic.AsyncAnthropic") as MockClass:
            mock_client = AsyncMock()
            mock_client.messages.create = capture
            MockClass.return_value = mock_client

            history = [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "Hi!"},
            ]
            await service.parse_message("forecast", history, {}, [])

        # The 2 history messages + 1 current message = 3
        assert len(captured_kwargs["messages"]) == 3
