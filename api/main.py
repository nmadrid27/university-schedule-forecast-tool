"""
FastAPI Backend for SCAD Forecast Tool
Exposes existing Python forecasting logic to the Next.js frontend.
"""

import json
import re
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
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
    QUARTER_CYCLE,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "forecast_config.json"
DATA_DIR = PROJECT_ROOT / "Data"

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
            return """Current forecast settings:

• **Capacity**: 20 students/section
• **Progression Rate**: 95%
• **Buffer**: 10%
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

class ChatResponse(BaseModel):
    message: str
    parsedCommand: Dict[str, Any]

class ForecastRequest(BaseModel):
    term: str
    method: Optional[str] = "sequence"
    config: Optional[Dict[str, Any]] = None

class ForecastResult(BaseModel):
    course: str
    campus: str
    projectedSeats: float
    sections: int
    change: Optional[float] = None
    changePercent: Optional[float] = None

class ForecastSummary(BaseModel):
    totalStudents: float
    totalSections: int
    coursesForecasted: int
    method: str

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
    capacity: int = 20
    progressionRate: float = 0.95
    bufferPercent: float = 0.0
    quartersToForecast: int = 2
    defaultTerm: str = "Spring 2026"

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
    """Parse user message and return structured response."""
    try:
        parsed = parser.parse(request.message, request.context or {})
        response_text = parser.get_response(parsed)

        return ChatResponse(
            message=response_text,
            parsedCommand={
                "intent": parsed.get("intent", "unknown"),
                "parameters": parsed.get("parameters", {}),
                "confidence": parsed.get("confidence", 0.0),
            }
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to process chat request")


@app.post("/api/forecast", response_model=ForecastResponse)
def run_forecast(request: ForecastRequest):
    """Run forecast for specified term using real sequence-based logic."""
    try:
        # Load config from disk, overlay any request-level overrides
        disk_cfg = _read_disk_config()
        req_cfg = request.config or {}

        capacity = int(req_cfg.get("capacity", disk_cfg.get("capacity", 20)))
        progression_rate = float(req_cfg.get("progression_rate", disk_cfg.get("progression_rate", 0.95)))
        buffer_percent = float(req_cfg.get("buffer_percent", disk_cfg.get("buffer_percent", 0.0)))

        # Resolve data file paths (relative paths are relative to PROJECT_ROOT)
        def resolve(key: str, default: str) -> Path:
            raw = disk_cfg.get(key, default)
            p = Path(raw)
            return p if p.is_absolute() else PROJECT_ROOT / p

        sequence_map_path = resolve("sequence_map", "Data/FOUN_sequencing_map_by_major.csv")
        enrollment_source_path = resolve("enrollment_source", "Data/Master Schedule of Classes.csv")

        # Use the requested term, falling back to config default
        target_term = request.term or disk_cfg.get("default_term", "Spring 2026")

        # Run the real forecast
        rows = run_sequence_forecast(
            sequence_map_path=sequence_map_path,
            enrollment_source_path=enrollment_source_path,
            target_term=target_term,
            capacity=capacity,
            progression_rate=progression_rate,
            buffer_percent=buffer_percent,
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

        # Load previous forecast for change comparison (best-effort)
        previous: Dict = {}
        for pattern in [
            f"Data/{target_term.replace(' ', '_')}_FOUN_Forecast*.csv",
            "Data/*_FOUN_Forecast*.csv",
        ]:
            matches = sorted(PROJECT_ROOT.glob(pattern))
            if matches:
                previous = load_previous_forecast(matches[-1])
                break

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

            results.append(
                ForecastResult(
                    course=row["course"],
                    campus=row["campus"],
                    projectedSeats=seats,
                    sections=row["sections"],
                    change=change,
                    changePercent=change_pct,
                )
            )

        total_students = sum(r.projectedSeats for r in results)
        total_sections = sum(r.sections for r in results)

        return ForecastResponse(
            results=results,
            summary=ForecastSummary(
                totalStudents=total_students,
                totalSections=total_sections,
                coursesForecasted=len(set(r.course for r in results)),
                method=method_label,
            ),
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Required data file not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception:
        raise HTTPException(status_code=500, detail="Forecast computation failed")


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
                # Determine feeder calendar year
                feeder_parts = label.split()
                feeder_year = feeder_parts[1] if len(feeder_parts) == 2 else ""
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
        bufferPercent=float(disk_cfg.get("buffer_percent", 0.0)),
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
                    "path": str(f),
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                })
            for f in data_dir.glob("*.xlsx"):
                files.append({
                    "name": f.name,
                    "path": str(f),
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
    """Run Prophet+ETS+ARIMA ensemble forecast on historical enrollment data."""
    import os
    import warnings
    import numpy as np
    import pandas as pd
    from forecast_tool.data.loaders import load_historical_data
    from forecast_tool.data.transformers import quarter_to_date
    from forecast_tool.forecasting.prophet_forecast import forecast_prophet
    from forecast_tool.forecasting.ets_forecast import forecast_ets
    from forecast_tool.forecasting.arima_forecast import forecast_arima
    from forecast_tool.forecasting.ensemble import (
        ensemble_forecast_weighted,
        optimize_ensemble_weights,
        DEFAULT_WEIGHTS,
    )

    try:
        disk_cfg = _read_disk_config()
        req_cfg = request.config or {}
        capacity = int(req_cfg.get("capacity", disk_cfg.get("capacity", 20)))
        buffer_percent = float(req_cfg.get("buffer_percent", disk_cfg.get("buffer_percent", 0.0)))

        # forecast_tool loaders use relative paths from project root
        prev_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            df_hist = load_historical_data()
        finally:
            os.chdir(prev_cwd)
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

        forecast_fns = {
            "prophet": forecast_prophet,
            "ets": forecast_ets,
            "arima": forecast_arima,
        }

        results = []
        weights_used = dict(DEFAULT_WEIGHTS)
        cv_mape = None

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
            if request.optimize_weights and len(df_ts) >= 10:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        weights_used, best_error = optimize_ensemble_weights(
                            df_ts, forecast_fns, min_train_size=6, horizon=1, step=1
                        )
                    cv_mape = best_error if best_error != float("inf") else None
                except (ValueError, Exception):
                    weights_used = dict(DEFAULT_WEIGHTS)

            # Run each model
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                preds = {}
                for name, fn in forecast_fns.items():
                    try:
                        raw = fn(df_ts, periods)
                        if isinstance(raw, pd.DataFrame):
                            if not raw.empty and "yhat" in raw.columns:
                                preds[name] = float(raw["yhat"].values[-1])
                            else:
                                preds[name] = float("nan")
                        else:
                            arr = np.asarray(raw).flatten()
                            preds[name] = float(arr[-1]) if len(arr) > 0 else float("nan")
                    except Exception:
                        preds[name] = float("nan")

            projected = ensemble_forecast_weighted(preds, weights_used)
            if np.isnan(projected) or projected <= 0:
                continue

            # Apply buffer
            buffer_mult = 1.0 + (buffer_percent / 100.0)
            projected *= buffer_mult
            sections = int(np.ceil(projected / capacity)) if capacity > 0 else 0

            results.append(EnsembleResult(
                course=course,
                campus="All",
                projectedSeats=round(projected, 2),
                sections=sections,
                method="Ensemble (Prophet+ETS+ARIMA)",
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
                "method": "Ensemble (Prophet+ETS+ARIMA)",
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
    import os
    import numpy as np
    import pandas as pd
    from forecast_tool.data.loaders import load_historical_data
    from forecast_tool.data.transformers import quarter_to_date
    from forecast_tool.diagnostics.stationarity_test import analyze_all_courses

    try:
        prev_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            df_hist = load_historical_data()
        finally:
            os.chdir(prev_cwd)
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
