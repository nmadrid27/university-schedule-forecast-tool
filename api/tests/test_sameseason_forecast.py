import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import forecaster as F


def _patch_terms(monkeypatch, by_code):
    """Make load_term_enrollments return canned {(campus,course): seats} per term code."""
    calls = []

    def fake(path, term_code, crosswalk=None, demand_metric="actual"):
        calls.append(term_code)
        return dict(by_code.get(term_code, {}))

    monkeypatch.setattr(F, "load_term_enrollments", fake)
    return calls


def test_level_single_point(monkeypatch):
    _patch_terms(monkeypatch, {"202610": {("SAVANNAH", "FOUN 110"): 1950}})
    rows = F.run_sameseason_forecast(Path("x.csv"), "Fall 2026", capacity=20, buffer_percent=0.0, crosswalk={})
    row = next(r for r in rows if r["course"] == "FOUN 110" and r["campus"] == "Savannah")
    assert round(row["projected_seats"]) == 1950
    assert row["method"] == "same_season"
    assert row["sections"] == 98  # ceil(1950/20)


def test_trend_two_points(monkeypatch):
    _patch_terms(monkeypatch, {
        "202610": {("SAVANNAH", "FOUN 110"): 100},
        "202710": {("SAVANNAH", "FOUN 110"): 120},
    })
    rows = F.run_sameseason_forecast(Path("x.csv"), "Fall 2027", capacity=20, buffer_percent=0.0, crosswalk={})
    row = next(r for r in rows if r["course"] == "FOUN 110")
    assert round(row["projected_seats"]) == 140  # linear trend 100->120 -> 140


def test_post_rollout_cutoff_only_queries_2026_plus(monkeypatch):
    calls = _patch_terms(monkeypatch, {"202610": {("SAVANNAH", "FOUN 110"): 60}})
    F.run_sameseason_forecast(Path("x.csv"), "Fall 2026", crosswalk={})
    assert "202610" in calls
    assert "202510" not in calls


def test_new_course_flagged(monkeypatch):
    _patch_terms(monkeypatch, {
        "202610": {("SAVANNAH", "FOUN 110"): 60},
        "202710": {("SAVANNAH", "FOUN 110"): 5, ("SAVANNAH", "FOUN 999"): 12},
    })
    rows = F.run_sameseason_forecast(Path("x.csv"), "Fall 2026", crosswalk={})
    new = next(r for r in rows if r["course"] == "FOUN 999")
    assert new["projected_seats"] == 0.0
    assert new["method"] == "same_season_new_course"


def test_empty_when_no_history(monkeypatch):
    _patch_terms(monkeypatch, {})
    rows = F.run_sameseason_forecast(Path("x.csv"), "Fall 2026", crosswalk={})
    assert rows == []


def test_buffer_applied(monkeypatch):
    _patch_terms(monkeypatch, {"202610": {("SCADNOW", "FOUN 113"): 200}})
    rows = F.run_sameseason_forecast(Path("x.csv"), "Fall 2026", capacity=20, buffer_percent=10.0, crosswalk={})
    row = next(r for r in rows if r["course"] == "FOUN 113")
    assert round(row["projected_seats"]) == 220
    assert row["campus"] == "SCADnow"


def test_post_rollout_prior_codes():
    from forecaster import _post_rollout_prior_same_season_codes as priors
    assert priors("Spring 2026") == []                      # first post-rollout Spring
    assert priors("Fall 2026") == ["202610"]                # Fall 2025
    assert priors("Spring 2027") == ["202630"]              # Spring 2026
    assert priors("Fall 2027") == ["202710", "202610"]      # most recent first
