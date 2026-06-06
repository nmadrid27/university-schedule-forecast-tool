"""
FastAPI Backend for SCAD Forecast Tool
Exposes existing Python forecasting logic to the Next.js frontend.
"""

import json
import logging
import math
import re
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any, Literal, Tuple
from datetime import datetime

# Ensure forecast_tool package is importable from the api/ directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forecaster import (
    run_sequence_forecast,
    run_ratio_forecast,
    load_previous_forecast,
    get_available_terms,
    term_code_to_label,
    resolve_term_info,
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "forecast_config.json"
DATA_DIR = PROJECT_ROOT / "Data"
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
    method: Optional[str] = "sequence"
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

class ForecastResponse(BaseModel):
    results: List[ForecastResult]
    summary: ForecastSummary

class TermOption(BaseModel):
    termCode: str
    label: str

class TermsResponse(BaseModel):
    available_terms: List[TermOption]
    forecastable_terms: List[TermOption]

class ConfigModel(BaseModel):
    capacity: int = Field(default=20, ge=1, le=100)
    progressionRate: float = Field(default=0.95, ge=0.0, le=1.0)
    bufferPercent: float = Field(default=10.0, ge=0.0, le=100.0)
    quartersToForecast: int = Field(default=2, ge=1, le=8)
    defaultTerm: str = "Spring 2026"
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

        # Use the requested term, falling back to config default
        target_term = request.term or disk_cfg.get("default_term", "Spring 2026")

        # Load adjustments for this term
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

        # Run the real forecast
        rows = run_sequence_forecast(
            sequence_map_path=sequence_map_path,
            enrollment_source_path=enrollment_source_path,
            target_term=target_term,
            capacity=capacity,
            progression_rate=progression_rate,
            buffer_percent=buffer_percent,
            admits_path=admits_path,
            enrollment_by_major_path=enrollment_by_major_path,
        )

        # Fallback: if sequence-based returned no results (e.g. Summer has
        # no sequencing data), try the ratio-based method using the closest
        # feeder quarter's existing forecast output.
        method_label = "Sequence-based"
        if not rows:
            info = resolve_term_info(target_term)
            feeder_quarter = info["closer_feeder"]["quarter"].capitalize()
            feeder_tc = info["closer_feeder"]["term_code"]
            feeder_label = term_code_to_label(feeder_tc)
            feeder_year = feeder_label.split()[1] if " " in feeder_label else feeder_tc[:4]
            # Look for the feeder quarter's forecast CSV
            feeder_pattern = f"{feeder_quarter}_{feeder_year}_FOUN_Forecast*.csv"
            feeder_csvs = sorted(DATA_DIR.glob(feeder_pattern))
            historical_path = DATA_DIR / "FOUN_Historical.csv"
            if feeder_csvs:
                # Prefer the Sequence Guides output (most reliable),
                # then try others until one has compatible columns.
                preferred = [
                    p for p in feeder_csvs
                    if "Sequence_Guides" in p.name or "sequence_guides" in p.name
                ]
                candidates = preferred + [
                    p for p in reversed(feeder_csvs) if p not in preferred
                ]
                for csv_path in candidates:
                    rows = run_ratio_forecast(
                        feeder_forecast_path=csv_path,
                        historical_data_path=historical_path,
                        target_term=target_term,
                        capacity=capacity,
                        buffer_percent=buffer_percent,
                    )
                    if rows:
                        method_label = "Ratio-based"
                        break

        # Apply output-level adjustments to rows
        if active_adjustments and rows:
            rows = apply_output_adjustments(active_adjustments, rows, capacity)

        # Load previous forecast for change comparison (best-effort).
        # Only compare against the same term's prior forecast to avoid
        # misleading change deltas from cross-term comparisons.
        previous: Dict = {}
        term_pattern = f"Data/{target_term.replace(' ', '_')}_FOUN_Forecast*.csv"
        term_matches = sorted(PROJECT_ROOT.glob(term_pattern))
        if term_matches:
            previous = load_previous_forecast(term_matches[-1])

        # Build OLS historical series for anomaly detection (best-effort)
        _ols_historical: Dict[Tuple[str, str], Dict[str, int]] = {}
        try:
            from forecast_tool.forecasting.ols_forecast import detect_anomaly
            from forecast_tool.data.loaders import load_historical_data
            _df_hist = load_historical_data(data_dir=str(DATA_DIR))
            if not _df_hist.empty:
                _foun_hist = _df_hist[_df_hist["course_code"].str.startswith("FOUN ")]
                for (_course, _campus), _grp in _foun_hist.groupby(["course_code", "campus"]):
                    _hist_map = {}
                    for _, _r in _grp.iterrows():
                        _qtr_lookup = {"Fall": "10", "Winter": "20", "Spring": "30", "Summer": "40"}
                        _tc = f"{_r['year']}{_qtr_lookup.get(_r['quarter'], '00')}"
                        _hist_map[_tc] = int(_r["enrollment"])
                    _ols_historical[(_course, _campus)] = _hist_map
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

        return ForecastResponse(
            results=results,
            summary=ForecastSummary(
                totalStudents=total_students,
                totalSections=total_sections,
                coursesForecasted=len(set(r.course for r in results)),
                method=method_label,
                adjustmentsApplied=adj_count if adj_count > 0 else None,
            ),
        )
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
    ta = load_adjustments(DATA_DIR, term)
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
    ta = add_adjustment(DATA_DIR, term, adj)
    return {"term": ta.term, "adjustment": adj.model_dump()}


@app.put("/api/adjustments/{term}/{adj_id}/toggle")
def toggle_adj(term: str, adj_id: str):
    """Toggle an adjustment on/off."""
    ta = toggle_adjustment(DATA_DIR, term, adj_id)
    return {"term": ta.term, "adjustments": [a.model_dump() for a in ta.adjustments]}


@app.delete("/api/adjustments/{term}/{adj_id}")
def delete_adjustment(term: str, adj_id: str):
    """Remove an adjustment."""
    ta = remove_adjustment(DATA_DIR, term, adj_id)
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
    """Update LLM provider/model/key. Writes key to .env.local, rest to config."""
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

        # A term is forecastable if both feeder term codes exist in the data
        forecastable = []
        for tc in term_codes:
            label = term_code_to_label(tc)
            try:
                info = resolve_term_info(label)
                closer_tc = info["closer_feeder"]["term_code"]
                farther_tc = info["farther_feeder"]["term_code"]
                if closer_tc in term_code_set and farther_tc in term_code_set:
                    forecastable.append(TermOption(termCode=tc, label=label))
            except (ValueError, KeyError):
                continue

        # Also check terms one step beyond available data
        # (i.e. terms whose feeders are the latest available terms)
        # Generate candidate next terms
        if term_codes:
            max_code = max(term_codes)
            max_acad = int(max_code[:4])
            for acad_year in [max_acad, max_acad + 1]:
                for qq in ["10", "20", "30", "40"]:
                    candidate = str(acad_year) + qq
                    if candidate in term_code_set:
                        continue
                    label = term_code_to_label(candidate)
                    try:
                        info = resolve_term_info(label)
                        closer_tc = info["closer_feeder"]["term_code"]
                        farther_tc = info["farther_feeder"]["term_code"]
                        if closer_tc in term_code_set and farther_tc in term_code_set:
                            forecastable.append(TermOption(termCode=candidate, label=label))
                    except (ValueError, KeyError):
                        continue

        # Also check terms forecastable via the ratio method: if a forecast
        # CSV exists for the closer feeder quarter, the target is forecastable.
        forecastable_codes = {t.termCode for t in forecastable}
        quarter_labels = {"10": "Fall", "20": "Winter", "30": "Spring", "40": "Summer"}
        for qq_target, qq_label in quarter_labels.items():
            for acad_year in [max_acad, max_acad + 1] if term_codes else []:
                candidate = str(acad_year) + qq_target
                if candidate in forecastable_codes:
                    continue
                label = term_code_to_label(candidate)
                try:
                    info = resolve_term_info(label)
                except (ValueError, KeyError):
                    continue
                feeder_q = info["closer_feeder"]["quarter"].capitalize()
                feeder_tc = info["closer_feeder"]["term_code"]
                feeder_label = term_code_to_label(feeder_tc)
                feeder_parts = feeder_label.split()
                feeder_year = feeder_parts[1] if len(feeder_parts) == 2 else feeder_tc[:4]
                pattern = f"{feeder_q}_{feeder_year}_FOUN_Forecast*.csv"
                if list(DATA_DIR.glob(pattern)):
                    forecastable.append(TermOption(termCode=candidate, label=label))

        # Deduplicate and sort forecastable
        seen = set()
        deduped = []
        for t in forecastable:
            if t.termCode not in seen:
                seen.add(t.termCode)
                deduped.append(t)
        deduped.sort(key=lambda x: x.termCode)

        return TermsResponse(
            available_terms=available,
            forecastable_terms=deduped,
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
    _write_disk_config(disk_cfg)
    return {"success": True, "config": config}


@app.get("/api/data/files")
async def list_data_files():
    """List available data files in the Data directory."""
    try:
        data_dir = Path(__file__).parent.parent / "Data"
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
        weights_used = dict(OLS_WEIGHTS)
        cv_mape = None

        forecast_fns = {
            "ols": forecast_ols,
            "ets": forecast_ets,
            "arima": forecast_arima,
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

            # Optimize weights if requested and enough data
            if request.optimize_weights and len(df_ts) >= 8:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        weights_used, best_error = optimize_ensemble_weights(
                            df_ts, forecast_fns, min_train_size=4, horizon=1, step=1
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
                weights={k: round(v, 3) for k, v in weights_used.items()},
                cvMape=round(cv_mape, 2) if cv_mape is not None else None,
            ))

        total_students = sum(r.projectedSeats for r in results)
        total_sections = sum(r.sections for r in results)

        return EnsembleResponse(
            results=results,
            summary={
                "totalStudents": round(total_students, 1),
                "totalSections": total_sections,
                "coursesForecasted": len(results),
                "method": "Ensemble (OLS+ETS+ARIMA)",
                "weights": {k: round(v, 3) for k, v in weights_used.items()},
                "cvMape": round(cv_mape, 2) if cv_mape is not None else None,
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
