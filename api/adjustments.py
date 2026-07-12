"""
Forecast adjustment models and persistence.

Adjustments allow users (or LLM) to modify forecast parameters or outputs
per-term. Two types:
  - config-level: modify inputs before forecast runs (capacity, progression_rate, buffer_percent)
  - output-level: modify results after forecast runs (multiply, add, set on projected_seats)

Persisted as JSON in Data/adjustments/{term}.json.
"""

import json
import math
import uuid
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class AdjustmentScope(BaseModel):
    """Optional scope limiter for an adjustment."""
    course: Optional[str] = None
    campus: Optional[str] = None


class Adjustment(BaseModel):
    """A single forecast adjustment."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: Literal["config", "output"]
    # config-level fields
    parameter: Optional[str] = None  # capacity, progression_rate, buffer_percent
    # output-level fields
    operation: Optional[str] = None  # multiply, add, set
    value: float
    scope: AdjustmentScope = Field(default_factory=AdjustmentScope)
    reason: str = ""
    enabled: bool = True
    source: Literal["llm", "manual"] = "manual"


class TermAdjustments(BaseModel):
    """All adjustments for a single term."""
    term: str
    adjustments: List[Adjustment] = Field(default_factory=list)


# --------------- Persistence ---------------

def _adjustments_dir(data_dir: Path) -> Path:
    d = data_dir / "adjustments"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _term_file(data_dir: Path, term: str) -> Path:
    safe = term.replace(" ", "_").lower()
    return _adjustments_dir(data_dir) / f"{safe}.json"


def load_adjustments(data_dir: Path, term: str) -> TermAdjustments:
    path = _term_file(data_dir, term)
    if not path.is_file():
        return TermAdjustments(term=term)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return TermAdjustments(**data)


def save_adjustments(data_dir: Path, ta: TermAdjustments) -> None:
    path = _term_file(data_dir, ta.term)
    _adjustments_dir(data_dir)  # ensure dir exists
    with path.open("w", encoding="utf-8") as f:
        json.dump(ta.model_dump(), f, indent=2)
        f.write("\n")


def add_adjustment(data_dir: Path, term: str, adj: Adjustment) -> TermAdjustments:
    ta = load_adjustments(data_dir, term)
    ta.adjustments.append(adj)
    save_adjustments(data_dir, ta)
    return ta


def toggle_adjustment(data_dir: Path, term: str, adj_id: str) -> TermAdjustments:
    ta = load_adjustments(data_dir, term)
    for adj in ta.adjustments:
        if adj.id == adj_id:
            adj.enabled = not adj.enabled
            break
    save_adjustments(data_dir, ta)
    return ta


def remove_adjustment(data_dir: Path, term: str, adj_id: str) -> TermAdjustments:
    ta = load_adjustments(data_dir, term)
    ta.adjustments = [a for a in ta.adjustments if a.id != adj_id]
    save_adjustments(data_dir, ta)
    return ta


# --------------- Application ---------------

# Display labels used by forecaster result rows, keyed by common spellings.
_CAMPUS_DISPLAY = {
    "savannah": "Savannah",
    "sav": "Savannah",
    "scadnow": "SCADnow",
    "now": "SCADnow",
    "atlanta": "Atlanta",
    "atl": "Atlanta",
}

def apply_config_adjustments(
    adjustments: List[Adjustment],
    capacity: int,
    progression_rate: float,
    buffer_percent: float,
) -> Dict:
    """Apply config-level adjustments, returning modified config values.

    Config adjustments with a scope (course/campus) are stored but not applied
    at the config level -- they'll be handled at the output level instead.
    Only global (no-scope) config adjustments are applied here.
    """
    cap = float(capacity)
    prog = progression_rate
    buf = buffer_percent

    for adj in adjustments:
        if adj.type != "config" or not adj.enabled:
            continue
        # Only apply global (unscoped) config adjustments
        if adj.scope.course or adj.scope.campus:
            continue
        if adj.parameter == "capacity":
            cap = adj.value
        elif adj.parameter == "progression_rate":
            prog = adj.value
        elif adj.parameter == "buffer_percent":
            buf = adj.value

    return {
        "capacity": max(1, min(100, int(cap))),
        "progression_rate": max(0.0, min(1.0, prog)),
        "buffer_percent": max(0.0, min(100.0, buf)),
    }


def apply_output_adjustments(
    adjustments: List[Adjustment],
    results: List[Dict],
    capacity: int,
) -> List[Dict]:
    """Apply output-level adjustments to forecast result rows.

    Each row dict must have: course, campus, projected_seats, sections.
    Returns new list with adjusted values and an 'adjusted' flag.
    """
    output = []
    for row in results:
        r = dict(row)
        was_adjusted = False
        seats = r["projected_seats"]
        row_capacity = capacity  # may be overridden by scoped config adjustment

        for adj in adjustments:
            if not adj.enabled:
                continue
            if adj.type == "output" or (adj.type == "config" and (adj.scope.course or adj.scope.campus)):
                # Check scope match
                if adj.scope.course and adj.scope.course.upper() != r["course"].upper():
                    continue
                if adj.scope.campus and adj.scope.campus.lower() != r["campus"].lower():
                    continue

                if adj.type == "output":
                    op_applied = False
                    if adj.operation == "multiply":
                        seats *= adj.value
                        op_applied = True
                    elif adj.operation == "add":
                        seats += adj.value
                        op_applied = True
                    elif adj.operation == "set":
                        seats = adj.value
                        op_applied = True
                    if op_applied:
                        was_adjusted = True
                elif adj.type == "config" and adj.parameter == "capacity":
                    row_capacity = max(1, min(100, int(adj.value)))
                    was_adjusted = True

        r["projected_seats"] = seats
        if was_adjusted:
            r["sections"] = int(math.ceil(seats / row_capacity)) if row_capacity > 0 and seats > 0 else 0
        # Preserve original sections for unadjusted rows
        r["adjusted"] = was_adjusted
        output.append(r)

    # Inject new rows for 'set' adjustments targeting courses absent from the forecast.
    # This covers courses that the sequence model can't produce (e.g. FOUN 110 in Spring).
    existing_keys = {(r["course"].upper(), r["campus"].lower()) for r in output}
    for adj in adjustments:
        if not adj.enabled or adj.type != "output" or adj.operation != "set":
            continue
        if not adj.scope.course or not adj.scope.campus:
            continue  # need both dimensions to create a specific row
        key = (adj.scope.course.upper(), adj.scope.campus.lower())
        if key in existing_keys:
            continue  # already handled in the loop above
        seats = adj.value
        sections = int(math.ceil(seats / capacity)) if capacity > 0 and seats > 0 else 0
        # Normalize to the display labels forecaster rows use ("Savannah"),
        # or case-sensitive joins downstream (backtest, change deltas) split
        # the injected row into a phantom campus.
        campus_raw = adj.scope.campus
        campus = _CAMPUS_DISPLAY.get(campus_raw.strip().lower(), campus_raw)
        output.append({
            "course": adj.scope.course,
            "campus": campus,
            "projected_seats": seats,
            "sections": sections,
            "adjusted": True,
            "method": "manual_adjustment",
        })

    return output
