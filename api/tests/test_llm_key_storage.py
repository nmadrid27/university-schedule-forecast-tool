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


def test_settings_file_written_with_owner_only_permissions(monkeypatch, tmp_path):
    settings = tmp_path / "settings.json"
    monkeypatch.setattr(llm_service, "settings_path", lambda: settings)
    llm_service.save_api_key("sk-test-123")
    assert (settings.stat().st_mode & 0o777) == 0o600


def test_llm_failure_response_does_not_leak_exception_detail():
    resp = llm_service._llm_failure_response(Exception("sk-secret-detail-xyz"))
    assert "sk-secret-detail-xyz" not in resp["response_text"]
    assert "LLM call failed" in resp["response_text"]
