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


def test_import_stores_uploaded_xlsx_and_points_config():
    r = client.post(
        "/api/data/import",
        files={"file": (
            "PZSMSCP export.xlsx",
            b"fake-xlsx-bytes",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
    )
    assert r.status_code == 200
    dest = main.DATA_DIR / "Master Schedule of Classes.xlsx"
    assert dest.is_file()
    assert dest.read_bytes() == b"fake-xlsx-bytes"

    import json
    saved = json.loads(main.CONFIG_PATH.read_text())
    assert saved["enrollment_source"] == "Data/Master Schedule of Classes.xlsx"


def test_import_accepts_csv():
    r = client.post(
        "/api/data/import",
        files={"file": ("export.csv", b"a,b\n1,2\n", "text/csv")},
    )
    assert r.status_code == 200
    assert (main.DATA_DIR / "Master Schedule of Classes.csv").is_file()


def test_import_rejects_unsupported_extension():
    r = client.post(
        "/api/data/import",
        files={"file": ("notes.txt", b"nope", "text/plain")},
    )
    assert r.status_code == 400


def test_import_admits_sets_admits_file():
    r = client.post(
        "/api/data/import",
        files={"file": ("PZSAAPF.xlsx", b"fake",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"kind": "admits"},
    )
    assert r.status_code == 200
    assert (main.DATA_DIR / "Admits.xlsx").is_file()
    import json
    saved = json.loads(main.CONFIG_PATH.read_text())
    assert saved["admitsFile"] == "Data/Admits.xlsx"
    # Master Schedule source must be untouched by an admits import
    assert "enrollment_source" not in saved or "Admits" not in saved.get("enrollment_source", "")
