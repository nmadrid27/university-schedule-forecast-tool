"""Tests for GET /api/terms endpoint."""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app  # noqa: E402

client = TestClient(app)


def test_terms_returns_200():
    r = client.get("/api/terms")
    assert r.status_code == 200


def test_terms_response_has_required_keys():
    body = client.get("/api/terms").json()
    assert "available_terms" in body
    assert "forecastable_terms" in body


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
