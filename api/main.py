"""
FastAPI Backend for SCAD Forecast Tool
Exposes existing Python forecasting logic to the Next.js frontend.
"""

import json
import logging
import math
import os
import re
import shutil
import sys
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any, Literal, Tuple
from datetime import datetime

# Ensure both package-style imports (api.main) and script-style imports
# (python api/main.py, desktop/app.py importing bare main) resolve reliably.
API_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = API_DIR.parent
for _p in (str(API_DIR), str(SOURCE_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from forecaster import (
    run_sequence_forecast,
    run_sameseason_forecast,
    run_ratio_forecast,
    load_previous_forecast,
    get_available_terms,
    term_code_to_label,
    resolve_term_info,
    load_crosswalk,
    load_term_enrollments,
    load_all_term_enrollments,
    analyze_admits_registration,
    normalize_demand_metric,
    _load_admits_rows,
    _post_rollout_prior_same_season_codes,
)
from adjustments import (
    Adjustment,
    AdjustmentScope,
    load_adjustments,
    add_adjustment,
    toggle_adjustment,
    remove_adjustment,
    apply_config_adjustments,
    apply_output_adjustments,
)
from llm_service import (
    create_llm_service,
    load_api_key,
    save_api_key,
)
import paths

paths.ensure_seeded()
PROJECT_ROOT = paths.app_data_dir()
CONFIG_PATH = paths.config_path()
DATA_DIR = paths.data_dir()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SCAD Forecast Tool API",
    description="AI-powered FOUN enrollment forecasting",
    version="1.0.0"
)

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== Standalone Command Parser ==============

class SimpleCommandParser:
    """Lightweight command parser without Streamlit dependencies."""

    def __init__(self):
        self.intent_patterns = {
            'forecast': [
                r'forecast', r'predict', r'project', r'estimate',
                r'(spring|summer|fall|winter)\s*\d{4}',
                r'enrollment', r'sections'
            ],
            'help': [r'help', r'what can you do', r'how do i', r'commands'],
            'settings': [r'settings', r'config', r'capacity', r'parameters'],
            'upload': [r'upload', r'import', r'load data'],
            'compare': [r'compare', r'versus', r'vs', r'difference'],
        }

    def parse(self, user_message: str, context: Dict = None) -> Dict[str, Any]:
        message_lower = user_message.lower()
        intent, confidence = self._classify_intent(message_lower)
        parameters = self._extract_parameters(user_message, message_lower, intent)

        return {
            'intent': intent,
            'parameters': parameters,
            'confidence': confidence,
            'raw_message': user_message
        }

    def _classify_intent(self, message_lower: str) -> tuple:
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return (intent, 0.85)
        return ('unknown', 0.3)

    def _extract_parameters(self, message: str, message_lower: str, intent: str) -> Dict:
        params = {}

        # Extract term
        term_match = re.search(r'(spring|fall|summer|winter)\s*(\d{4}|\d{2})', message_lower)
        if term_match:
            season = term_match.group(1).capitalize()
            year = term_match.group(2)
            if len(year) == 2:
                year = '20' + year
            params['term'] = f"{season} {year}"

        # Extract course
        course_match = re.search(r'FOUN\s*(\d{3})', message, re.IGNORECASE)
        if course_match:
            params['course'] = f"FOUN {course_match.group(1)}"

        # Extract campus
        if 'scadnow' in message_lower or 'online' in message_lower:
            params['campus'] = 'SCADnow'
        elif 'savannah' in message_lower:
            params['campus'] = 'Savannah'

        return params

    def get_response(self, parsed: Dict) -> str:
        intent = parsed.get('intent', 'unknown')
        params = parsed.get('parameters', {})

        if intent == 'forecast':
            term = params.get('term', 'Spring 2026')
            return f"Here is the forecast for {term} enrollments based on current models and historical data trends. The projections suggest a moderate growth trajectory."

        elif intent == 'help':
            return """I can help you with:

• **Forecast enrollments** - "Forecast Spring 2026" or "Show me Fall projections"
• **Compare methods** - "Compare Prophet vs sequence-based"
• **Adjust settings** - "Set capacity to 25 students"
• **Upload data** - "Upload enrollment data"
• **View trends** - "Show FOUN 110 trends"

What would you like to do?"""

        elif intent == 'settings':
            cfg = _read_disk_config()
            cap = cfg.get("capacity", 20)
            prog = cfg.get("progression_rate", 0.95)
            buf = cfg.get("buffer_percent", 10.0)
            return f"""Current forecast settings:

• **Capacity**: {cap} students/section
• **Progression Rate**: {prog * 100:.0f}%
• **Buffer**: {buf:.0f}%
• **Method**: Sequence-based

You can adjust these by saying "Set capacity to 25" or "Change buffer to 15%"."""

        else:
            return """I understand you're asking about forecasting. Could you be more specific? Try:

• "Forecast Spring 2026 enrollments"
• "Compare forecasting methods"
• "Show current settings"
• "Help" """


# Initialize parser
parser = SimpleCommandParser()

# ============== Models ==============

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    history: Optional[List[Dict[str, str]]] = None
    term: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    parsedCommand: Dict[str, Any]
    adjustments: Optional[List[Dict[str, Any]]] = None
    llm_used: bool = False

class ForecastRequest(BaseModel):
    term: str
    # Free-form strings, normalized in the handler: stale clients sending
    # "Historical" or unknown values must degrade to the default, not 422.
    method: Optional[str] = None
    demandMetric: Optional[str] = None
    # Internal switch for /api/backtest: calibration must score the raw model
    # output, so the backtest path disables manual adjustments.
    applyAdjustments: bool = True
    config: Optional[Dict[str, Any]] = None
    # Scenario percentages: e.g. [{"label": "conservative", "pct": -9},
    #                               {"label": "optimistic",  "pct": -5}]
    scenarios: Optional[List[Dict[str, Any]]] = None

class ScenarioResult(BaseModel):
    label: str
    pct: float
    projectedSeats: float
    sections: int

class ForecastResult(BaseModel):
    course: str
    campus: str
    projectedSeats: float
    sections: int
    change: Optional[float] = None
    changePercent: Optional[float] = None
    adjusted: Optional[bool] = None
    anomalyFlag: Optional[Dict[str, Any]] = None
    scenarios: Optional[List[ScenarioResult]] = None

class ForecastSummary(BaseModel):
    totalStudents: float
    totalSections: int
    coursesForecasted: int
    method: str
    adjustmentsApplied: Optional[int] = None
    demandMetric: Optional[str] = None
    warnings: Optional[List[str]] = None

class ForecastResponse(BaseModel):
    results: List[ForecastResult]
    summary: ForecastSummary

class TermOption(BaseModel):
    termCode: str
    label: str

class TermsResponse(BaseModel):
    available_terms: List[TermOption]
    forecastable_terms: List[TermOption]
    forecastable_by_method: Optional[Dict[str, List[TermOption]]] = None

class ConfigModel(BaseModel):
    capacity: int = Field(default=20, ge=1, le=100)
    progressionRate: float = Field(default=0.95, ge=0.0, le=1.0)
    bufferPercent: float = Field(default=10.0, ge=0.0, le=100.0)
    quartersToForecast: int = Field(default=2, ge=1, le=8)
    defaultTerm: str = "Spring 2026"
    # None = "not provided": PUT must not clobber the on-disk value when a
    # client omits these fields (stale clients send only the classic fields).
    method: Optional[Literal["auto", "historical", "sequence"]] = None
    demandMetric: Optional[Literal["actual", "max", "actual_plus_waitlist"]] = None
    admitsFile: Optional[str] = None
    enrollmentByMajorFile: Optional[str] = None

class AdjustmentRequest(BaseModel):
    type: Literal["config", "output"]
    parameter: Optional[Literal["capacity", "progression_rate", "buffer_percent"]] = None
    operation: Optional[Literal["multiply", "add", "set"]] = None
    value: float
    scope: Optional[Dict[str, Optional[str]]] = None
    reason: str = ""

    @model_validator(mode="after")
    def validate_shape(self):
        if self.type == "config":
            if self.parameter is None:
                raise ValueError("config adjustments require 'parameter'")
            if self.operation is not None:
                raise ValueError("config adjustments must not include 'operation'")
        elif self.type == "output":
            if self.operation is None:
                raise ValueError("output adjustments require 'operation'")
            if self.parameter is not None:
                raise ValueError("output adjustments must not include 'parameter'")
        return self

class LLMConfigRequest(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None

def _read_disk_config() -> dict:
    """Read forecast_config.json from disk."""
    if CONFIG_PATH.is_file():
        with CONFIG_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    return {}


def _write_disk_config(data: dict) -> None:
    """Write forecast_config.json to disk."""
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

# ============== Routes ==============

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Parse user message and return structured response.

    If an LLM is configured, uses it for intent parsing and adjustment extraction.
    Falls back to SimpleCommandParser if no LLM or on LLM failure.
    """
    try:
        disk_cfg = _read_disk_config()
        llm = create_llm_service(disk_cfg)

        # Try LLM first if configured
        if llm and llm.is_configured():
            # Build active adjustments context
            term = request.term or disk_cfg.get("default_term", "Spring 2026")
            ta = load_adjustments(DATA_DIR, term)
            active = [a.model_dump() for a in ta.adjustments if a.enabled]

            llm_result = await llm.parse_message(
                message=request.message,
                history=request.history or [],
                config=disk_cfg,
                active_adjustments=active,
            )

            # If LLM didn't error out, use its result
            if llm_result.get("intent") != "unknown" or not llm_result.get("error"):
                # Persist any adjustments the LLM extracted
                new_adjustments = []
                for adj_data in llm_result.get("adjustments", []):
                    if not isinstance(adj_data, dict):
                        logger.warning(
                            "Skipping malformed LLM adjustment payload (expected object, got %s)",
                            type(adj_data).__name__,
                        )
                        continue

                    adj_type = adj_data.get("type", "output")
                    parameter = adj_data.get("parameter")
                    operation = adj_data.get("operation")

                    # Skip malformed LLM adjustments rather than failing chat.
                    if adj_type not in {"config", "output"}:
                        continue
                    if adj_type == "config":
                        if parameter not in {"capacity", "progression_rate", "buffer_percent"}:
                            continue
                        operation = None
                    else:
                        if operation not in {"multiply", "add", "set"}:
                            continue
                        parameter = None

                    value_raw = adj_data.get("value", 0)
                    try:
                        value = float(value_raw)
                    except (TypeError, ValueError):
                        logger.warning(
                            "Skipping malformed LLM adjustment with non-numeric value: %r",
                            value_raw,
                        )
                        continue
                    if not math.isfinite(value):
                        logger.warning(
                            "Skipping malformed LLM adjustment with non-finite value: %r",
                            value_raw,
                        )
                        continue

                    scope_raw = adj_data.get("scope")
                    scope = scope_raw if isinstance(scope_raw, dict) else {}
                    adj = Adjustment(
                        type=adj_type,
                        parameter=parameter,
                        operation=operation,
                        value=value,
                        scope=AdjustmentScope(
                            course=scope.get("course"),
                            campus=scope.get("campus"),
                        ),
                        reason=adj_data.get("reason", ""),
                        source="llm",
                    )
                    add_adjustment(DATA_DIR, term, adj)
                    new_adjustments.append(adj.model_dump())

                # If LLM found adjustments, treat intent as "adjust" for the frontend
                intent = llm_result.get("intent", "unknown")
                if new_adjustments and intent == "unknown":
                    intent = "adjust"

                return ChatResponse(
                    message=llm_result.get("response_text", ""),
                    parsedCommand={
                        "intent": intent,
                        "parameters": llm_result.get("parameters", {}),
                        "confidence": llm_result.get("confidence", 0.5),
                    },
                    adjustments=new_adjustments if new_adjustments else None,
                    llm_used=True,
                )

        # Fallback to regex parser
        parsed = parser.parse(request.message, request.context or {})
        response_text = parser.get_response(parsed)

        return ChatResponse(
            message=response_text,
            parsedCommand={
                "intent": parsed.get("intent", "unknown"),
                "parameters": parsed.get("parameters", {}),
                "confidence": parsed.get("confidence", 0.0),
            },
            llm_used=False,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to process chat request")


@app.post("/api/forecast", response_model=ForecastResponse)
def run_forecast(request: ForecastRequest):
    """Run forecast for specified term using real sequence-based logic.

    Automatically loads and applies any active adjustments for the term.
    """
    try:
        # Load config from disk, overlay any request-level overrides
        disk_cfg = _read_disk_config()
        req_cfg = request.config or {}

        capacity = int(req_cfg.get("capacity", disk_cfg.get("capacity", 20)))
        progression_rate = float(req_cfg.get("progressionRate", req_cfg.get("progression_rate", disk_cfg.get("progression_rate", 0.95))))
        buffer_percent = float(req_cfg.get("bufferPercent", req_cfg.get("buffer_percent", disk_cfg.get("buffer_percent", 10.0))))
        demand_metric = normalize_demand_metric(
            request.demandMetric
            or req_cfg.get("demandMetric")
            or req_cfg.get("demand_metric")
            or disk_cfg.get("demand_metric", "actual")
        )

        # Use the requested term, falling back to config default
        target_term = request.term or disk_cfg.get("default_term", "Spring 2026")

        # Load adjustments for this term (skipped for backtests, which measure
        # raw model accuracy against actuals)
        active_adjustments: List = []
        if request.applyAdjustments:
            ta = load_adjustments(DATA_DIR, target_term)
            active_adjustments = [a for a in ta.adjustments if a.enabled]

        # Apply config-level adjustments (global ones modify capacity/progression/buffer)
        if active_adjustments:
            adjusted_cfg = apply_config_adjustments(
                active_adjustments, capacity, progression_rate, buffer_percent
            )
            capacity = adjusted_cfg["capacity"]
            progression_rate = adjusted_cfg["progression_rate"]
            buffer_percent = adjusted_cfg["buffer_percent"]

        # Resolve data file paths (relative paths are relative to PROJECT_ROOT)
        def resolve(key: str, default: str) -> Path:
            raw = disk_cfg.get(key, default)
            p = Path(raw)
            return p if p.is_absolute() else PROJECT_ROOT / p

        sequence_map_path = resolve("sequence_map", "Data/FOUN_sequencing_map_by_major.csv")
        enrollment_source_path = resolve("enrollment_source", "Data/Master Schedule of Classes.csv")

        # Optional data enrichment files (None = not configured)
        def resolve_optional(key: str) -> Optional[Path]:
            raw = disk_cfg.get(key)
            if not raw:
                return None
            p = Path(raw)
            return p if p.is_absolute() else PROJECT_ROOT / p

        admits_path = resolve_optional("admitsFile")
        enrollment_by_major_path = resolve_optional("enrollmentByMajorFile")

        # Run the real forecast. "auto" tries the historical same-season model
        # first and falls back to the sequence-map model when same-season history
        # does not exist yet (e.g. Spring 2026, the first post-rollout Spring).
        method = (request.method or req_cfg.get("method") or disk_cfg.get("method") or "auto").lower()
        if method not in {"auto", "historical", "sequence"}:
            method = "auto"

        def _has_signal(candidate_rows: List[Dict]) -> bool:
            return bool(candidate_rows) and sum((r.get("projected_seats") or 0) for r in candidate_rows) > 0

        def _run_sequence() -> Tuple[List[Dict], str]:
            seq_rows = run_sequence_forecast(
                sequence_map_path=sequence_map_path,
                enrollment_source_path=enrollment_source_path,
                target_term=target_term,
                capacity=capacity,
                progression_rate=progression_rate,
                buffer_percent=buffer_percent,
                admits_path=admits_path,
                enrollment_by_major_path=enrollment_by_major_path,
                demand_metric=demand_metric,
            )
            seq_label = "Sequence-based"
            # Fallback: if sequence-based returned no results (e.g. Summer has
            # no sequencing data), try the ratio-based method using the closest
            # feeder quarter's existing forecast output.
            if not seq_rows:
                info = resolve_term_info(target_term)
                feeder_quarter = info["closer_feeder"]["quarter"].capitalize()
                feeder_tc = info["closer_feeder"]["term_code"]
                feeder_label = term_code_to_label(feeder_tc)
                feeder_year = feeder_label.split()[1] if " " in feeder_label else feeder_tc[:4]
                feeder_pattern = f"{feeder_quarter}_{feeder_year}_FOUN_Forecast*.csv"
                feeder_csvs = sorted(DATA_DIR.glob(feeder_pattern))
                historical_path = DATA_DIR / "FOUN_Historical.csv"
                if feeder_csvs:
                    preferred = [p for p in feeder_csvs
                                 if "Sequence_Guides" in p.name or "sequence_guides" in p.name]
                    candidates = preferred + [p for p in reversed(feeder_csvs) if p not in preferred]
                    for csv_path in candidates:
                        seq_rows = run_ratio_forecast(
                            feeder_forecast_path=csv_path,
                            historical_data_path=historical_path,
                            target_term=target_term,
                            capacity=capacity,
                            buffer_percent=buffer_percent,
                        )
                        if seq_rows:
                            seq_label = "Ratio-based"
                            break
            return seq_rows, seq_label

        if method == "sequence":
            rows, method_label = _run_sequence()
        else:
            rows = run_sameseason_forecast(
                master_schedule_path=enrollment_source_path,
                target_term=target_term,
                capacity=capacity,
                buffer_percent=buffer_percent,
                demand_metric=demand_metric,
            )
            method_label = "Same-season historical"
            if method == "auto" and not _has_signal(rows):
                rows, method_label = _run_sequence()
                if _has_signal(rows):
                    method_label = f"Auto ({method_label})"

        # Apply output-level adjustments to rows. Must run even when the base
        # forecast produced no rows: course+campus "set" adjustments inject rows
        # for courses the model cannot produce, which is the manual-estimate
        # recovery path the no-data 422 below tells the admin to use.
        if active_adjustments:
            rows = apply_output_adjustments(active_adjustments, rows, capacity)

        # Guardrail: nothing to forecast means the Master Schedule lacks the
        # data this method needs. Explain it instead of returning zeros.
        no_data = (not rows) or sum((r.get("projected_seats") or 0) for r in rows) == 0
        if no_data:
            _g = resolve_term_info(target_term)
            _closer = term_code_to_label(_g.get("closer_feeder", {}).get("term_code", ""))
            _farther = term_code_to_label(_g.get("farther_feeder", {}).get("term_code", ""))
            if method == "sequence":
                _detail = (
                    f"No feeder enrollment found to forecast {target_term}. The imported "
                    f"Master Schedule must include the prior quarters ({_farther} and "
                    f"{_closer}). Import the PZSMSCP export covering those terms."
                )
            elif method == "auto":
                _priors = _post_rollout_prior_same_season_codes(target_term)
                _hist_need = term_code_to_label(_priors[0]) if _priors else "a prior post-rollout same-season term"
                _detail = (
                    f"No forecast data found for {target_term}. Auto mode needs either "
                    f"same-season history ({_hist_need}) or sequence feeder terms "
                    f"({_farther} and {_closer}) in the imported Master Schedule."
                )
            else:
                _priors = _post_rollout_prior_same_season_codes(target_term)
                if not _priors:
                    _season = target_term.split()[0]
                    _detail = (
                        f"{target_term} is the first post-rollout {_season}, so there is no "
                        f"prior same-season term under the current FOUN curriculum to forecast "
                        f"from. Switch to the sequence method for this term, or set a manual "
                        f"estimate."
                    )
                else:
                    _prior = term_code_to_label(_priors[0])
                    _detail = (
                        f"No same-season history found to forecast {target_term}. Import a "
                        f"Master Schedule that includes the prior year's same quarter ({_prior})."
                    )
            raise HTTPException(status_code=422, detail=_detail)

        # Load previous forecast for change comparison (best-effort).
        # Only compare against the same term's prior forecast to avoid
        # misleading change deltas from cross-term comparisons.
        previous: Dict = {}
        term_pattern = f"Data/{target_term.replace(' ', '_')}_FOUN_Forecast*.csv"
        term_matches = sorted(PROJECT_ROOT.glob(term_pattern))
        if term_matches:
            previous = load_previous_forecast(term_matches[-1])

        # Build OLS historical series for anomaly detection (best-effort).
        # Use the active Master Schedule loader so campus labels and demand
        # metrics match the forecast path. The older FOUN_Historical loader is
        # course-only and cannot key anomalies by campus.
        _ols_historical: Dict[Tuple[str, str], Dict[str, int]] = {}
        try:
            from forecast_tool.forecasting.ols_forecast import detect_anomaly
            _crosswalk = load_crosswalk(enrollment_source_path.parent / "sequence_crosswalk_template.csv")
            _campus_label = {"SAVANNAH": "Savannah", "SCADNOW": "SCADnow", "ATLANTA": "Atlanta"}
            # Single pass over the Master Schedule; per-term calls re-parse
            # the whole file once per term and dominate request latency.
            for _tc, _totals in load_all_term_enrollments(
                enrollment_source_path,
                crosswalk=_crosswalk,
                demand_metric=demand_metric,
            ).items():
                for (_campus, _course), _seats in _totals.items():
                    if str(_course).startswith("FOUN"):
                        _ols_historical.setdefault((_course, _campus_label.get(_campus, _campus)), {})[_tc] = int(_seats)
        except Exception:
            pass

        # Determine target season for anomaly detection
        _target_season = None
        try:
            _info = resolve_term_info(target_term)
            _target_season = _info.get("target_quarter", "").capitalize()
        except Exception:
            pass

        # Parse scenario definitions from request
        _scenarios_def = request.scenarios or []

        results = []
        for row in rows:
            seats = row["projected_seats"]
            prev_seats = previous.get((row["course"], row["campus"]))
            change = None
            change_pct = None
            if prev_seats is not None:
                change = seats - prev_seats
                if prev_seats > 0:
                    change_pct = round((change / prev_seats) * 100, 1)

            # Anomaly detection: compare forecast against OLS trend
            anomaly = None
            _hist = _ols_historical.get((row["course"], row["campus"]))
            if _hist and _target_season:
                try:
                    anomaly = detect_anomaly(
                        _hist, _target_season, latest_actual=seats
                    ) or None
                except Exception:
                    pass

            # Scenario projections
            scenario_results = None
            if _scenarios_def:
                import math as _math
                scenario_results = []
                for sc in _scenarios_def:
                    label = sc.get("label", str(sc.get("pct", 0)))
                    pct = float(sc.get("pct", 0)) / 100.0
                    sc_seats = max(0.0, seats * (1 + pct))
                    sc_sections = _math.ceil(sc_seats / capacity) if capacity > 0 and sc_seats > 0 else 0
                    scenario_results.append(ScenarioResult(
                        label=label,
                        pct=float(sc.get("pct", 0)),
                        projectedSeats=round(sc_seats, 1),
                        sections=sc_sections,
                    ))

            results.append(
                ForecastResult(
                    course=row["course"],
                    campus=row["campus"],
                    projectedSeats=seats,
                    sections=row["sections"],
                    change=change,
                    changePercent=change_pct,
                    adjusted=row.get("adjusted"),
                    anomalyFlag=anomaly if anomaly and anomaly.get("flagged") else None,
                    scenarios=scenario_results,
                )
            )

        total_students = sum(r.projectedSeats for r in results)
        total_sections = sum(r.sections for r in results)
        adj_count = len(active_adjustments) if active_adjustments else 0
        warnings: List[str] = []
        if admits_path and "Sequence" in method_label:
            warnings.extend(analyze_admits_registration(admits_path).get("warnings", []))

        return ForecastResponse(
            results=results,
            summary=ForecastSummary(
                totalStudents=total_students,
                totalSections=total_sections,
                coursesForecasted=len(set(r.course for r in results)),
                method=method_label,
                adjustmentsApplied=adj_count if adj_count > 0 else None,
                demandMetric=demand_metric,
                warnings=warnings or None,
            ),
        )
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Required data file not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception:
        raise HTTPException(status_code=500, detail="Forecast computation failed")


# ============== Adjustment Routes ==============

@app.get("/api/adjustments/{term}")
def get_adjustments(term: str):
    """List all adjustments for a term."""
    try:
        ta = load_adjustments(DATA_DIR, term)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"term": ta.term, "adjustments": [a.model_dump() for a in ta.adjustments]}


@app.post("/api/adjustments/{term}")
def create_adjustment(term: str, request: AdjustmentRequest):
    """Add a new adjustment for a term."""
    scope = AdjustmentScope(
        course=request.scope.get("course") if request.scope else None,
        campus=request.scope.get("campus") if request.scope else None,
    )
    adj = Adjustment(
        type=request.type,
        parameter=request.parameter,
        operation=request.operation,
        value=request.value,
        scope=scope,
        reason=request.reason,
        source="manual",
    )
    try:
        ta = add_adjustment(DATA_DIR, term, adj)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"term": ta.term, "adjustment": adj.model_dump()}


@app.put("/api/adjustments/{term}/{adj_id}/toggle")
def toggle_adj(term: str, adj_id: str):
    """Toggle an adjustment on/off."""
    try:
        ta = toggle_adjustment(DATA_DIR, term, adj_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"term": ta.term, "adjustments": [a.model_dump() for a in ta.adjustments]}


@app.delete("/api/adjustments/{term}/{adj_id}")
def delete_adjustment(term: str, adj_id: str):
    """Remove an adjustment."""
    try:
        ta = remove_adjustment(DATA_DIR, term, adj_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"term": ta.term, "adjustments": [a.model_dump() for a in ta.adjustments]}


# ============== LLM Config Routes ==============

@app.get("/api/llm/status")
def llm_status():
    """Check if LLM is configured. Never returns the API key."""
    disk_cfg = _read_disk_config()
    llm_cfg = disk_cfg.get("llm", {})
    provider = llm_cfg.get("provider", "none")
    has_key = bool(load_api_key()) if provider not in ("none", "ollama") else True
    llm = create_llm_service(disk_cfg)
    configured = llm.is_configured() if llm else False
    return {
        "provider": provider,
        "model": llm_cfg.get("model"),
        "base_url": llm_cfg.get("base_url"),
        "has_key": has_key,
        "configured": configured,
    }


@app.put("/api/llm/config")
def update_llm_config(request: LLMConfigRequest):
    """Update LLM provider/model/key. Writes key to app-data settings.json, rest to config."""
    disk_cfg = _read_disk_config()
    llm_cfg = disk_cfg.get("llm", {})

    if request.provider is not None:
        llm_cfg["provider"] = request.provider
    if request.model is not None:
        llm_cfg["model"] = request.model
    if request.base_url is not None:
        llm_cfg["base_url"] = request.base_url if request.base_url else None
    if request.api_key is not None:
        save_api_key(request.api_key)

    disk_cfg["llm"] = llm_cfg
    _write_disk_config(disk_cfg)

    has_key = bool(load_api_key()) if llm_cfg.get("provider") not in ("none", "ollama") else True
    return {
        "success": True,
        "provider": llm_cfg.get("provider", "none"),
        "model": llm_cfg.get("model"),
        "configured": has_key and llm_cfg.get("provider", "none") != "none",
    }


# ============== Existing Routes ==============

@app.get("/api/terms", response_model=TermsResponse)
def list_terms():
    """List available and forecastable terms from the Master Schedule."""
    try:
        disk_cfg = _read_disk_config()
        raw = disk_cfg.get("enrollment_source", "Data/Master Schedule of Classes.csv")
        p = Path(raw)
        master_path = p if p.is_absolute() else PROJECT_ROOT / p

        if not master_path.is_file():
            raise HTTPException(status_code=404, detail="Master Schedule not found")

        term_codes = get_available_terms(master_path)
        term_code_set = set(term_codes)

        available = []
        for tc in term_codes:
            label = term_code_to_label(tc)
            available.append(TermOption(termCode=tc, label=label))

        candidates = set(term_codes)
        if term_codes:
            max_code = max(term_codes)
            max_acad = int(max_code[:4])
            # Include near-future terms so the scheduler can forecast beyond the
            # last imported term when the needed feeder/history terms exist.
            for acad_year in range(max_acad, max_acad + 3):
                for qq in ["10", "20", "30", "40"]:
                    candidates.add(f"{acad_year}{qq}")

        by_method: Dict[str, List[TermOption]] = {
            "historical": [],
            "sequence": [],
            "auto": [],
        }

        def _dedupe_sort(items: List[TermOption]) -> List[TermOption]:
            seen = set()
            out = []
            for item in items:
                if item.termCode not in seen:
                    seen.add(item.termCode)
                    out.append(item)
            out.sort(key=lambda x: x.termCode)
            return out

        def _sequence_has_ratio_fallback(info: Dict) -> bool:
            feeder_q = info["closer_feeder"]["quarter"].capitalize()
            feeder_tc = info["closer_feeder"]["term_code"]
            feeder_label = term_code_to_label(feeder_tc)
            feeder_parts = feeder_label.split()
            feeder_year = feeder_parts[1] if len(feeder_parts) == 2 else feeder_tc[:4]
            pattern = f"{feeder_q}_{feeder_year}_FOUN_Forecast*.csv"
            return bool(list(DATA_DIR.glob(pattern)))

        for candidate in candidates:
            label = term_code_to_label(candidate)
            try:
                info = resolve_term_info(label)
            except (ValueError, KeyError):
                continue

            option = TermOption(termCode=candidate, label=label)
            priors = _post_rollout_prior_same_season_codes(label)
            # run_sameseason_forecast projects from ANY available post-rollout
            # prior, so offering the term must not require the most recent one.
            historical_ok = any(p in term_code_set for p in priors)

            closer_tc = info["closer_feeder"]["term_code"]
            farther_tc = info["farther_feeder"]["term_code"]
            sequence_ok = (closer_tc in term_code_set and farther_tc in term_code_set) or _sequence_has_ratio_fallback(info)

            if historical_ok:
                by_method["historical"].append(option)
            if sequence_ok:
                by_method["sequence"].append(option)
            if historical_ok or sequence_ok:
                by_method["auto"].append(option)

        by_method = {key: _dedupe_sort(value) for key, value in by_method.items()}

        return TermsResponse(
            available_terms=available,
            forecastable_terms=by_method["auto"],
            forecastable_by_method=by_method,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to retrieve terms")


@app.get("/api/config", response_model=ConfigModel)
def get_config():
    """Get current forecast configuration from disk."""
    disk_cfg = _read_disk_config()
    return ConfigModel(
        capacity=int(disk_cfg.get("capacity", 20)),
        progressionRate=float(disk_cfg.get("progression_rate", 0.95)),
        bufferPercent=float(disk_cfg.get("buffer_percent", 10.0)),
        quartersToForecast=int(disk_cfg.get("quarters_to_forecast", 2)),
        defaultTerm=disk_cfg.get("default_term", "Spring 2026"),
        method=disk_cfg.get("method", "auto") if disk_cfg.get("method") in {"auto", "historical", "sequence"} else "auto",
        demandMetric=normalize_demand_metric(disk_cfg.get("demand_metric", "actual")),
        admitsFile=disk_cfg.get("admitsFile"),
        enrollmentByMajorFile=disk_cfg.get("enrollmentByMajorFile"),
    )


@app.put("/api/config")
def update_config(config: ConfigModel):
    """Update forecast configuration on disk."""
    disk_cfg = _read_disk_config()
    disk_cfg["capacity"] = config.capacity
    disk_cfg["progression_rate"] = config.progressionRate
    disk_cfg["buffer_percent"] = config.bufferPercent
    disk_cfg["quarters_to_forecast"] = config.quartersToForecast
    disk_cfg["default_term"] = config.defaultTerm
    if config.method is not None:
        disk_cfg["method"] = config.method
    if config.demandMetric is not None:
        disk_cfg["demand_metric"] = config.demandMetric
    _write_disk_config(disk_cfg)
    return {"success": True, "config": config}


@app.get("/api/data/files")
async def list_data_files():
    """List available data files in the Data directory."""
    try:
        data_dir = DATA_DIR
        files = []

        if data_dir.exists():
            for f in data_dir.glob("*.csv"):
                files.append({
                    "name": f.name,
                    "path": f.name,
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                })
            for f in data_dir.glob("*.xlsx"):
                files.append({
                    "name": f.name,
                    "path": f.name,
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                })

        return {"files": files}
    except OSError:
        raise HTTPException(status_code=500, detail="Failed to read data directory")


@app.post("/api/data/import")
async def import_data_file(file: UploadFile = File(...), kind: str = Form("master")):
    """Receive an uploaded report and store it in the Data directory.

    kind="master" stores the PZSMSCP Master Schedule (the forecast's enrollment
    source); kind="admits" stores the PZSAAPF accepted-applicants report (new-
    student demand for intro courses). A multipart upload lets a plain
    <input type="file"> drive the picker, avoiding the pywebview js_api dialog
    which does not display reliably on macOS from a worker thread.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".xlsx", ".xlsm", ".xls", ".csv"):
        raise HTTPException(status_code=400, detail="Unsupported file type")
    if suffix == ".xls":
        raise HTTPException(
            status_code=400,
            detail="Legacy .xls files cannot be read. In Excel, save the report "
                   "as .xlsx and import it again.",
        )
    if kind == "admits" and suffix == ".csv":
        raise HTTPException(
            status_code=400,
            detail="The admits report must be an Excel file. Export the PZSAAPF "
                   "report as .xlsx and import it again.",
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    content = await file.read()

    if kind == "admits":
        dest = DATA_DIR / ("Admits" + suffix)
        config_key = "admitsFile"
    else:
        dest = DATA_DIR / ("Master Schedule of Classes" + suffix)
        config_key = "enrollment_source"

    # Stage the upload next to the destination (same filesystem, so the final
    # os.replace is atomic), validate it with the real loader, and only then
    # touch the live file. A wrong or corrupt upload must never clobber a
    # known-good data file or repoint the config at unreadable data.
    tmp = DATA_DIR / (".import_tmp_" + dest.name)
    try:
        tmp.write_bytes(content)
        if kind == "admits":
            rows, header = _load_admits_rows(tmp)
            # Require the real PZSAAPF header: the legacy column fallback in
            # _load_admits_rows would otherwise accept any readable workbook
            # (e.g. a Master Schedule uploaded as admits) and silently zero
            # admits demand downstream.
            if not rows or "student id" not in header:
                raise HTTPException(
                    status_code=422,
                    detail="The uploaded file does not look like a PZSAAPF admits "
                           "export (no Student ID column found). The previous "
                           "admits file was left untouched.",
                )
        else:
            if not get_available_terms(tmp):
                raise HTTPException(
                    status_code=422,
                    detail="The uploaded file contains no readable TERM data, so it "
                           "does not look like a PZSMSCP Master Schedule export. The "
                           "previous Master Schedule was left untouched.",
                )
        if dest.exists():
            shutil.copy2(dest, dest.with_name(dest.name + ".bak"))
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)

    # Point the active config at the imported file so the forecast finds it
    # regardless of extension (.xlsx vs .csv).
    cfg = _read_disk_config()
    cfg[config_key] = f"Data/{dest.name}"
    _write_disk_config(cfg)

    return {"success": True, "stored_as": dest.name, "kind": kind, "data_dir": str(DATA_DIR)}


# ============== Backtest / Calibration Routes ==============

class BacktestRequest(BaseModel):
    term: str
    # None = fall through to the request config dict, then disk config —
    # a truthy default here would make the configured values unreachable.
    method: Optional[str] = None
    demandMetric: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class BacktestRow(BaseModel):
    course: str
    campus: str
    actual: float
    forecast: float
    error: float
    absError: float
    pctError: Optional[float] = None


class BacktestMetrics(BaseModel):
    mae: float
    mape: Optional[float] = None
    bias: float
    captureRate: Optional[float] = None
    actualTotal: float
    forecastTotal: float
    comparedRows: int


class BacktestResponse(BaseModel):
    term: str
    method: str
    demandMetric: str
    metrics: BacktestMetrics
    byCampus: Dict[str, BacktestMetrics]
    rows: List[BacktestRow]


@app.post("/api/backtest", response_model=BacktestResponse)
def run_backtest(request: BacktestRequest):
    """Compare a forecast for a term against actual Master Schedule enrollment.

    This is intended for calibration: it reports MAE/MAPE/bias/capture by
    course and campus using PZSMSCP ACT/MAX/waitlist data as ground truth.
    """
    try:
        disk_cfg = _read_disk_config()
        req_cfg = dict(request.config or {})
        # Resolve the metric ONCE and use it for both the forecast side and
        # the actuals side, so the comparison is metric-consistent.
        demand_metric = normalize_demand_metric(
            request.demandMetric
            or req_cfg.get("demandMetric")
            or req_cfg.get("demand_metric")
            or disk_cfg.get("demand_metric", "actual")
        )
        # Calibration scores the raw model: no planning buffer unless the
        # caller explicitly set one, and no manual adjustments.
        if "bufferPercent" not in req_cfg and "buffer_percent" not in req_cfg:
            req_cfg["bufferPercent"] = 0
        forecast = run_forecast(ForecastRequest(
            term=request.term,
            method=request.method,
            demandMetric=demand_metric,
            applyAdjustments=False,
            config=req_cfg,
        ))

        raw = disk_cfg.get("enrollment_source", "Data/Master Schedule of Classes.csv")
        source = Path(raw)
        master_path = source if source.is_absolute() else PROJECT_ROOT / source
        info = resolve_term_info(request.term)
        crosswalk = load_crosswalk(master_path.parent / "sequence_crosswalk_template.csv")
        campus_label = {"SAVANNAH": "Savannah", "SCADNOW": "SCADnow", "ATLANTA": "Atlanta"}

        actual = {
            (course, campus_label.get(campus, campus)): seats
            for (campus, course), seats in load_term_enrollments(
                master_path,
                info["target_term_code"],
                crosswalk=crosswalk,
                demand_metric=demand_metric,
            ).items()
        }
        forecast_map = {(r.course, r.campus): r.projectedSeats for r in forecast.results}
        keys = sorted(set(actual.keys()) | set(forecast_map.keys()))
        rows: List[BacktestRow] = []
        for course, campus in keys:
            actual_val = float(actual.get((course, campus), 0.0))
            forecast_val = float(forecast_map.get((course, campus), 0.0))
            error = forecast_val - actual_val
            pct = round((error / actual_val) * 100, 1) if actual_val > 0 else None
            rows.append(BacktestRow(
                course=course,
                campus=campus,
                actual=actual_val,
                forecast=forecast_val,
                error=error,
                absError=abs(error),
                pctError=pct,
            ))

        def _metrics(items: List[BacktestRow]) -> BacktestMetrics:
            actual_total = sum(r.actual for r in items)
            forecast_total = sum(r.forecast for r in items)
            compared = [r for r in items if r.actual > 0 or r.forecast > 0]
            mae = sum(r.absError for r in compared) / len(compared) if compared else 0.0
            pct_rows = [abs(r.error / r.actual) * 100 for r in compared if r.actual > 0]
            mape = sum(pct_rows) / len(pct_rows) if pct_rows else None
            bias = forecast_total - actual_total
            capture = (forecast_total / actual_total) if actual_total > 0 else None
            return BacktestMetrics(
                mae=round(mae, 2),
                mape=round(mape, 2) if mape is not None else None,
                bias=round(bias, 2),
                captureRate=round(capture, 3) if capture is not None else None,
                actualTotal=round(actual_total, 2),
                forecastTotal=round(forecast_total, 2),
                comparedRows=len(compared),
            )

        campuses = sorted({r.campus for r in rows})
        return BacktestResponse(
            term=request.term,
            method=forecast.summary.method,
            demandMetric=demand_metric,
            metrics=_metrics(rows),
            byCampus={campus: _metrics([r for r in rows if r.campus == campus]) for campus in campuses},
            rows=rows,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Backtest failed")


# ============== Ensemble & Diagnostics Routes ==============

class EnsembleRequest(BaseModel):
    course: Optional[str] = None
    campus: Optional[str] = None
    periods: int = 1
    optimize_weights: bool = False
    config: Optional[Dict[str, Any]] = None


class EnsembleResult(BaseModel):
    course: str
    campus: str
    projectedSeats: float
    sections: int
    method: str
    # The season the projection targets (the one following the last observed
    # term); None when the course fell back to the mixed-series fit.
    season: Optional[str] = None
    weights: Optional[Dict[str, float]] = None
    cvMape: Optional[float] = None


class EnsembleResponse(BaseModel):
    results: List[EnsembleResult]
    summary: Dict[str, Any]


class DiagnosticsResponse(BaseModel):
    results: Dict[str, Any]
    summary: Dict[str, Any]


@app.post("/api/forecast/ensemble", response_model=EnsembleResponse)
def run_ensemble_forecast(request: EnsembleRequest):
    """Run OLS+ETS+ARIMA ensemble forecast on historical enrollment data.

    OLS (season-aware linear regression) replaces Prophet. It is faster,
    fully interpretable, requires no external C library, and performs
    comparably on 4-8 data-point enrollment series.
    """
    import warnings
    import numpy as np
    import pandas as pd
    from forecast_tool.data.loaders import load_historical_data
    from forecast_tool.data.transformers import quarter_to_date
    from forecast_tool.forecasting.ols_forecast import forecast_ols
    from forecast_tool.forecasting.ets_forecast import forecast_ets
    from forecast_tool.forecasting.arima_forecast import forecast_arima
    from forecast_tool.forecasting.ensemble import (
        ensemble_forecast_weighted,
        optimize_ensemble_weights,
    )

    # OLS replaces Prophet; redistribute former Prophet weight to OLS
    OLS_WEIGHTS = {"ols": 0.40, "ets": 0.35, "arima": 0.25}

    try:
        disk_cfg = _read_disk_config()
        req_cfg = request.config or {}
        capacity = int(req_cfg.get("capacity", disk_cfg.get("capacity", 20)))
        buffer_percent = float(
            req_cfg.get(
                "bufferPercent",
                req_cfg.get("buffer_percent", disk_cfg.get("buffer_percent", 0.0)),
            )
        )

        df_hist = load_historical_data(data_dir=str(DATA_DIR))
        if df_hist.empty:
            raise HTTPException(status_code=404, detail="Historical data not found or empty")

        # Filter to FOUN courses
        foun_mask = df_hist["course_code"].str.startswith("FOUN ")
        df_foun = df_hist[foun_mask].copy()
        if df_foun.empty:
            raise HTTPException(status_code=404, detail="No FOUN courses in historical data")

        # Optionally filter by course/campus
        if request.course:
            df_foun = df_foun[df_foun["course_code"] == request.course]
        if request.campus:
            # Historical data doesn't have campus breakdown at this level;
            # results will be aggregated across campuses
            pass

        # Group by course and build time series
        courses = df_foun["course_code"].unique()
        periods = request.periods

        results = []
        cv_mapes: List[float] = []

        from forecast_tool.data.transformers import date_to_quarter_label

        _SEASON_ORDER = ["winter", "spring", "summer", "fall"]

        def _next_season_subseries(df):
            """Return (same-season sub-series, season) for the season that
            follows the last observation. FOUN enrollment is strongly seasonal
            (Fall in the hundreds, Summer near zero), so fitting a trend or a
            non-seasonal ARIMA through the mixed sawtooth produces spurious
            slopes; each season must be projected from its own history. The
            sub-series ds becomes the calendar year so OLS uses a year axis.
            """
            labels = df["ds"].map(lambda d: str(date_to_quarter_label(d)).split()[0].lower())
            last = labels.iloc[-1]
            nxt = _SEASON_ORDER[(_SEASON_ORDER.index(last) + 1) % 4]
            sub = df[labels == nxt]
            sub = pd.DataFrame({
                "ds": sub["ds"].map(lambda d: str(d.year)),
                "y": sub["y"].values,
            })
            return sub, nxt

        def _season_aware(fn):
            """Fit on the same-season sub-series when it has 2+ points; sparse
            or unrecognizable series fall back to the full mixed series."""
            def wrapped(df_train, periods_):
                try:
                    sub, _ = _next_season_subseries(df_train)
                except Exception:
                    sub = None
                if sub is not None and len(sub) >= 2:
                    return fn(sub, periods_)
                return fn(df_train, periods_)
            return wrapped

        forecast_fns = {
            "ols": _season_aware(forecast_ols),
            "ets": _season_aware(forecast_ets),
            "arima": _season_aware(forecast_arima),
        }

        for course in sorted(courses):
            course_df = df_foun[df_foun["course_code"] == course]
            agg = (
                course_df.groupby(["year", "quarter"])["enrollment"]
                .sum()
                .reset_index()
            )
            agg["ds"] = agg.apply(
                lambda row: quarter_to_date(row["year"], row["quarter"]), axis=1
            )
            agg = agg.rename(columns={"enrollment": "y"}).sort_values("ds").reset_index(drop=True)
            df_ts = agg[["ds", "y"]]

            if len(df_ts) < 4:
                continue

            # Per-course state: optimized weights must never leak from one
            # course to the next (courses below the 8-point optimization
            # threshold keep the defaults).
            weights_used = dict(OLS_WEIGHTS)
            cv_mape = None
            try:
                _sub, season_label = _next_season_subseries(df_ts)
                if len(_sub) < 2:
                    season_label = None
            except Exception:
                season_label = None

            # Optimize weights if requested and enough data
            if request.optimize_weights and len(df_ts) >= 8:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        weights_used, best_error = optimize_ensemble_weights(
                            df_ts, forecast_fns, min_train_size=4, horizon=1, step=1,
                            metric="mape",
                        )
                    cv_mape = best_error if best_error != float("inf") else None
                except (ValueError, Exception):
                    weights_used = dict(OLS_WEIGHTS)

            # Run each model
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                preds = {}
                for name, fn in forecast_fns.items():
                    try:
                        raw = fn(df_ts, periods)
                        if isinstance(raw, pd.DataFrame):
                            preds[name] = float(raw["yhat"].values[-1]) if not raw.empty and "yhat" in raw.columns else float("nan")
                        else:
                            arr = np.asarray(raw).flatten()
                            preds[name] = float(arr[-1]) if len(arr) > 0 else float("nan")
                    except Exception:
                        preds[name] = float("nan")

            projected = ensemble_forecast_weighted(preds, weights_used)
            if np.isnan(projected) or projected <= 0:
                continue

            buffer_mult = 1.0 + (buffer_percent / 100.0)
            projected *= buffer_mult
            sections = int(np.ceil(projected / capacity)) if capacity > 0 else 0

            results.append(EnsembleResult(
                course=course,
                campus="All",
                projectedSeats=round(projected, 2),
                sections=sections,
                method="Ensemble (OLS+ETS+ARIMA)",
                season=season_label,
                weights={k: round(v, 3) for k, v in weights_used.items()},
                cvMape=round(cv_mape, 2) if cv_mape is not None else None,
            ))
            if cv_mape is not None:
                cv_mapes.append(cv_mape)

        total_students = sum(r.projectedSeats for r in results)
        total_sections = sum(r.sections for r in results)

        return EnsembleResponse(
            results=results,
            summary={
                "totalStudents": round(total_students, 1),
                "totalSections": total_sections,
                "coursesForecasted": len(results),
                "method": "Ensemble (OLS+ETS+ARIMA)",
                # With per-course optimization the weights vary by course (see
                # each result row); the summary only reports the shared default.
                "weights": None if request.optimize_weights
                else {k: round(v, 3) for k, v in OLS_WEIGHTS.items()},
                "cvMape": round(sum(cv_mapes) / len(cv_mapes), 2) if cv_mapes else None,
            },
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception:
        raise HTTPException(status_code=500, detail="Ensemble forecast failed")


@app.get("/api/diagnostics", response_model=DiagnosticsResponse)
def run_diagnostics():
    """Run stationarity and seasonality diagnostics on all FOUN courses."""
    import numpy as np
    from forecast_tool.data.loaders import load_historical_data
    from forecast_tool.data.transformers import quarter_to_date
    from forecast_tool.diagnostics.stationarity_test import analyze_all_courses

    try:
        df_hist = load_historical_data(data_dir=str(DATA_DIR))
        if df_hist.empty:
            raise HTTPException(status_code=404, detail="Historical data not found or empty")

        foun_mask = df_hist["course_code"].str.startswith("FOUN ") | df_hist["course_code"].str.startswith("DRAW ")
        df_foun = df_hist[foun_mask].copy()

        # Build per-course enrollment series (aggregated by quarter, ordered chronologically)
        course_dict = {}
        for course in df_foun["course_code"].unique():
            course_df = df_foun[df_foun["course_code"] == course]
            agg = (
                course_df.groupby(["year", "quarter"])["enrollment"]
                .sum()
                .reset_index()
            )
            agg["ds"] = agg.apply(
                lambda row: quarter_to_date(row["year"], row["quarter"]), axis=1
            )
            agg = agg.sort_values("ds").reset_index(drop=True)
            if len(agg) >= 4:
                course_dict[course] = agg["enrollment"]

        if not course_dict:
            raise HTTPException(status_code=404, detail="Insufficient historical data for diagnostics")

        analysis = analyze_all_courses(course_dict)

        # Sanitize for JSON serialization: convert numpy types, strip arrays
        def sanitize(obj):
            if isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [sanitize(v) for v in obj]
            if isinstance(obj, (np.bool_,)):
                return bool(obj)
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            return obj

        clean_results = sanitize(analysis["results"])
        clean_summary = sanitize(analysis["summary"])

        # Remove large arrays from API response
        for course_data in clean_results.values():
            seasonality = course_data.get("seasonality", {})
            for key in ["seasonal_component", "trend_component", "residual_component"]:
                if key in seasonality:
                    seasonality[key] = None

        return DiagnosticsResponse(
            results=clean_results,
            summary=clean_summary,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Diagnostics analysis failed")


def mount_static_ui() -> None:
    """Serve the statically-exported Next.js UI at / when present.

    No-op in dev/test where the web build is absent. Mounted last so it does
    not shadow /api routes.
    """
    from fastapi.staticfiles import StaticFiles

    web_dir = paths.bundle_dir() / "web"
    if web_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="ui")


mount_static_ui()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
