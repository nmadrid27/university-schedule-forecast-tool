import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import llm_service


def test_save_and_load_key_roundtrip(monkeypatch, tmp_path):
    settings = tmp_path / "settings.json"
    monkeypatch.setattr(llm_service, "settings_path", lambda: settings)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    assert llm_service.load_api_key() is None
    llm_service.save_api_key("sk-test-123")
    assert llm_service.load_api_key() == "sk-test-123"


def test_env_var_overrides_settings(monkeypatch, tmp_path):
    settings = tmp_path / "settings.json"
    monkeypatch.setattr(llm_service, "settings_path", lambda: settings)
    llm_service.save_api_key("sk-from-file")
    monkeypatch.setenv("LLM_API_KEY", "sk-from-env")
    assert llm_service.load_api_key() == "sk-from-env"
