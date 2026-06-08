"""End-to-end-ish smoke test against the real engine and bundled seed data."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main

client = TestClient(main.app)

DATA_PRESENT = (main.DATA_DIR / "FOUN_sequencing_map_by_major.csv").is_file()


@pytest.mark.skipif(not DATA_PRESENT, reason="requires real seq map in Data/")
def test_health():
    assert client.get("/api/health").json()["status"] in ("ok", "healthy")


@pytest.mark.skipif(not DATA_PRESENT, reason="requires real seq map in Data/")
def test_spring_forecast_returns_rows():
    body = client.post("/api/forecast", json={"term": "Spring 2026", "method": "sequence"}).json()
    assert "summary" in body
    assert len(body["results"]) > 0
