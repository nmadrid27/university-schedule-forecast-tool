"""Tests for GET /api/terms endpoint."""

import csv
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main
from main import app  # noqa: E402

client = TestClient(app)


def test_terms_returns_200():
    r = client.get("/api/terms")
    assert r.status_code == 200


def test_terms_response_has_required_keys():
    body = client.get("/api/terms").json()
    assert "available_terms" in body
    assert "forecastable_terms" in body
    assert "forecastable_by_method" in body
    assert set(body["forecastable_by_method"]).issuperset({"auto", "historical", "sequence"})


def test_terms_each_item_has_term_code_and_label():
    body = client.get("/api/terms").json()
    for item in body["available_terms"]:
        assert "termCode" in item
        assert "label" in item


def test_terms_available_list_is_non_empty():
    body = client.get("/api/terms").json()
    assert len(body["available_terms"]) > 0


def test_terms_forecastable_is_subset_of_available():
    body = client.get("/api/terms").json()
    available_codes = {t["termCode"] for t in body["available_terms"]}
    # Forecastable terms may include near-future terms not yet in available,
    # but all their codes should be 6-digit YYYYQQ format
    for item in body["forecastable_terms"]:
        assert len(item["termCode"]) == 6
        assert item["termCode"].isdigit()


def test_terms_labels_are_human_readable():
    body = client.get("/api/terms").json()
    for item in body["available_terms"][:5]:
        # Labels should be like "Spring 2026", "Fall 2025", etc.
        assert any(
            season in item["label"]
            for season in ("Spring", "Fall", "Winter", "Summer")
        )


def test_terms_ratio_forecastability_uses_closer_feeder_year(monkeypatch, tmp_path):
    data_dir = tmp_path / "Data"
    data_dir.mkdir()

    master = data_dir / "Master.csv"
    with master.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["TERM", "SUBJ", "CRS NUMBER", "ACT ENR", "CAMPUS"],
        )
        writer.writeheader()
        # Keep Summer 2026 feeder missing so Winter 2027 is not sequence-forecastable.
        for term in ["202610", "202620", "202630", "202710"]:
            writer.writerow({
                "TERM": term,
                "SUBJ": "FOUN",
                "CRS NUMBER": "110",
                "ACT ENR": "10",
                "CAMPUS": "SAV",
            })

    # Winter 2027's closer feeder is Fall 2026.
    (data_dir / "Fall_2026_FOUN_Forecast_Test.csv").write_text(
        "course,campus,projected_seats\nFOUN 110,Savannah,100\n",
        encoding="utf-8",
    )

    cfg = tmp_path / "forecast_config.json"
    cfg.write_text(json.dumps({"enrollment_source": str(master)}), encoding="utf-8")

    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "CONFIG_PATH", cfg)

    body = client.get("/api/terms").json()
    forecastable_codes = {t["termCode"] for t in body["forecastable_terms"]}
    assert "202720" in forecastable_codes  # Winter 2027


def test_historical_offered_when_any_post_rollout_prior_is_available(monkeypatch):
    """run_sameseason_forecast can forecast from ANY post-rollout prior
    same-season term, so /api/terms must not require the most recent one.
    With only Fall 2025 (202610) imported, Fall 2027 (202810) is historically
    forecastable even though Fall 2026 (202710) is missing."""
    monkeypatch.setattr(main, "get_available_terms", lambda *a, **k: ["202610"])
    body = client.get("/api/terms").json()
    historical_codes = [t["termCode"] for t in body["forecastable_by_method"]["historical"]]
    assert "202810" in historical_codes
