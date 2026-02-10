"""
FastAPI Backend for SCAD Forecast Tool
Exposes existing Python forecasting logic to the Next.js frontend.
"""

import json
import re
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from forecaster import (
    run_sequence_forecast,
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
                method="Sequence-based",
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
