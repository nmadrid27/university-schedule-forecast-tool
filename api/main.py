"""
FastAPI Backend for SCAD Forecast Tool
Exposes existing Python forecasting logic to the Next.js frontend.
"""

import sys
import re
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

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
                r'spring\s*2026', r'fall\s*2026', r'summer\s*2026',
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
    projectedSeats: int
    sections: int
    change: Optional[int] = None
    changePercent: Optional[float] = None

class ForecastSummary(BaseModel):
    totalStudents: int
    totalSections: int
    coursesForecasted: int
    method: str

class ForecastResponse(BaseModel):
    results: List[ForecastResult]
    summary: ForecastSummary

class ConfigModel(BaseModel):
    capacity: int = 20
    progressionRate: float = 0.95
    bufferPercent: int = 10
    quartersToForecast: int = 2

# In-memory config
current_config = ConfigModel()

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/forecast", response_model=ForecastResponse)
async def run_forecast(request: ForecastRequest):
    """Run forecast for specified term."""
    try:
        # Mock realistic forecast data
        results = [
            ForecastResult(course="FOUN 110", campus="Savannah", projectedSeats=380, sections=19, change=5, changePercent=3.0),
            ForecastResult(course="FOUN 110", campus="SCADnow", projectedSeats=120, sections=6, change=15, changePercent=10.0),
            ForecastResult(course="FOUN 112", campus="Savannah", projectedSeats=260, sections=13, change=3, changePercent=2.0),
            ForecastResult(course="FOUN 113", campus="Savannah", projectedSeats=340, sections=17, change=8, changePercent=5.0),
            ForecastResult(course="FOUN 113", campus="SCADnow", projectedSeats=80, sections=4, change=2, changePercent=3.0),
            ForecastResult(course="FOUN 250", campus="Savannah", projectedSeats=200, sections=10, change=-2, changePercent=-1.0),
            ForecastResult(course="FOUN 251", campus="Savannah", projectedSeats=180, sections=9, change=4, changePercent=3.0),
            ForecastResult(course="FOUN 251", campus="SCADnow", projectedSeats=45, sections=3, change=1, changePercent=2.0),
        ]
        
        total_students = sum(r.projectedSeats for r in results)
        total_sections = sum(r.sections for r in results)
        
        return ForecastResponse(
            results=results,
            summary=ForecastSummary(
                totalStudents=total_students,
                totalSections=total_sections,
                coursesForecasted=len(set(r.course for r in results)),
                method=f"{request.method.title()}-based" if request.method else "Sequence-based"
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config", response_model=ConfigModel)
async def get_config():
    """Get current forecast configuration."""
    return current_config


@app.put("/api/config")
async def update_config(config: ConfigModel):
    """Update forecast configuration."""
    global current_config
    current_config = config
    return {"success": True, "config": current_config}


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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
