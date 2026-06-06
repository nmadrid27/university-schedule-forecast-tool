import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _tmp_data(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "CONFIG_PATH", tmp_path / "forecast_config.json")


def test_import_copies_source_file(tmp_path):
    src = tmp_path / "PZSMSCP_export.xlsx"
    src.write_bytes(b"fake-xlsx-bytes")
    r = client.post("/api/data/import", json={"source_path": str(src)})
    assert r.status_code == 200
    dest = main.DATA_DIR / "Master Schedule of Classes.xlsx"
    assert dest.is_file()
    assert dest.read_bytes() == b"fake-xlsx-bytes"


def test_import_rejects_missing_file():
    r = client.post("/api/data/import", json={"source_path": "/no/such/file.xlsx"})
    assert r.status_code == 400
