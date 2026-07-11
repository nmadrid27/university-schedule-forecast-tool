import io
import json
import sys
from pathlib import Path

import openpyxl
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main

client = TestClient(main.app)

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture(autouse=True)
def _tmp_data(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "CONFIG_PATH", tmp_path / "forecast_config.json")


def _minimal_master_csv() -> bytes:
    return b"TERM,CRN,SUBJ,CRS NUMBER,ACT ENR\n202610,10001,FOUN,110,20\n"


def _minimal_master_xlsx() -> bytes:
    """Tiny PZSMSCP-shaped workbook: metadata row, header row, one data row."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["PZSMSCP - Flexible Master Schedule of Classes"])
    ws.append(["TERM", "CRN", "SUBJ", "CRS NUMBER", "ACT ENR", "CAMPUS"])
    ws.append(["202610", "10001", "FOUN", "110", 20, "SAV"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _minimal_admits_xlsx() -> bytes:
    """Tiny PZSAAPF-shaped workbook: header row with Student ID, one data row."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Student ID", "Campus", "Currently Registered Courses (NO WL)"])
    ws.append(["900000001", "M", "FOUN110"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# --------------- Happy path ------------------------------------------------

def test_import_stores_uploaded_xlsx_and_points_config():
    content = _minimal_master_xlsx()
    r = client.post(
        "/api/data/import",
        files={"file": ("PZSMSCP export.xlsx", content, XLSX_MIME)},
    )
    assert r.status_code == 200
    dest = main.DATA_DIR / "Master Schedule of Classes.xlsx"
    assert dest.is_file()
    assert dest.read_bytes() == content

    saved = json.loads(main.CONFIG_PATH.read_text())
    assert saved["enrollment_source"] == "Data/Master Schedule of Classes.xlsx"


def test_import_accepts_csv():
    r = client.post(
        "/api/data/import",
        files={"file": ("export.csv", _minimal_master_csv(), "text/csv")},
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
        files={"file": ("PZSAAPF.xlsx", _minimal_admits_xlsx(), XLSX_MIME)},
        data={"kind": "admits"},
    )
    assert r.status_code == 200
    assert (main.DATA_DIR / "Admits.xlsx").is_file()
    saved = json.loads(main.CONFIG_PATH.read_text())
    assert saved["admitsFile"] == "Data/Admits.xlsx"
    # Master Schedule source must be untouched by an admits import
    assert "enrollment_source" not in saved or "Admits" not in saved.get("enrollment_source", "")


# --------------- Validation and data safety --------------------------------

def test_import_master_rejects_unparseable_content_and_preserves_existing():
    """Uploading a file the loader cannot read must not clobber the live
    Master Schedule or repoint the config — this was the wrong-report
    failure mode (e.g. a Spring-only CLSS export or corrupt bytes)."""
    dest = main.DATA_DIR / "Master Schedule of Classes.xlsx"
    dest.write_bytes(b"GOOD-EXISTING-DATA")
    main.CONFIG_PATH.write_text(json.dumps(
        {"enrollment_source": "Data/Master Schedule of Classes.xlsx"}))

    r = client.post(
        "/api/data/import",
        files={"file": ("garbage.xlsx", b"not-a-real-xlsx", XLSX_MIME)},
    )
    assert r.status_code == 422
    assert dest.read_bytes() == b"GOOD-EXISTING-DATA"
    saved = json.loads(main.CONFIG_PATH.read_text())
    assert saved["enrollment_source"] == "Data/Master Schedule of Classes.xlsx"


def test_import_master_rejects_csv_without_term_column():
    r = client.post(
        "/api/data/import",
        files={"file": ("export.csv", b"a,b\n1,2\n", "text/csv")},
    )
    assert r.status_code == 422
    assert not (main.DATA_DIR / "Master Schedule of Classes.csv").exists()


def test_import_master_backs_up_previous_file():
    dest = main.DATA_DIR / "Master Schedule of Classes.csv"
    dest.write_bytes(b"OLD-DATA")

    new_content = _minimal_master_csv()
    r = client.post(
        "/api/data/import",
        files={"file": ("export.csv", new_content, "text/csv")},
    )
    assert r.status_code == 200
    assert dest.read_bytes() == new_content
    bak = main.DATA_DIR / "Master Schedule of Classes.csv.bak"
    assert bak.is_file()
    assert bak.read_bytes() == b"OLD-DATA"


def test_import_admits_rejects_unreadable_file():
    r = client.post(
        "/api/data/import",
        files={"file": ("PZSAAPF.xlsx", b"not-a-real-xlsx", XLSX_MIME)},
        data={"kind": "admits"},
    )
    assert r.status_code == 422
    assert not (main.DATA_DIR / "Admits.xlsx").exists()


def test_import_leaves_no_temp_files_behind():
    client.post(
        "/api/data/import",
        files={"file": ("garbage.xlsx", b"not-a-real-xlsx", XLSX_MIME)},
    )
    client.post(
        "/api/data/import",
        files={"file": ("export.csv", _minimal_master_csv(), "text/csv")},
    )
    leftovers = [p.name for p in main.DATA_DIR.iterdir() if p.name.startswith(".import_tmp")]
    assert leftovers == []
