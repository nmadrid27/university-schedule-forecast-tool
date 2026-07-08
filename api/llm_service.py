"""
Provider-agnostic LLM service for SCAD FOUN Forecasting Tool.

Supports OpenAI, Anthropic, Ollama (via OpenAI-compatible API), and custom
OpenAI-compatible endpoints. Handles system prompt construction, structured
output parsing, and graceful fallback.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from paths import settings_path


# --------------- Configuration ---------------

PROVIDER_DEFAULTS = {
    "openai": {"base_url": None, "default_model": "gpt-4o-mini"},
    "anthropic": {"base_url": None, "default_model": "claude-sonnet-4-5-20250514"},
    "ollama": {"base_url": "http://localhost:11434/v1", "default_model": "llama3.2"},
    "custom": {"base_url": None, "default_model": "gpt-4o-mini"},
}


def _read_settings() -> Dict[str, Any]:
    sp = settings_path()
    if sp.is_file():
        try:
            return json.loads(sp.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _write_settings(data: Dict[str, Any]) -> None:
    sp = settings_path()
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(data, indent=2))


def load_api_key() -> Optional[str]:
    """Load LLM API key from the environment or app-data settings.json."""
    key = os.environ.get("LLM_API_KEY")
    if key:
        return key
    return _read_settings().get("LLM_API_KEY")


def save_api_key(key: str) -> None:
    """Persist the LLM API key to app-data settings.json."""
    data = _read_settings()
    data["LLM_API_KEY"] = key
    _write_settings(data)


def save_env_var(name: str, value: str) -> None:
    """Persist an arbitrary setting to app-data settings.json."""
    data = _read_settings()
    data[name] = value
    _write_settings(data)


# --------------- System Prompt ---------------

SYSTEM_PROMPT_TEMPLATE = """You are the AI assistant for the SCAD FOUN Enrollment Forecasting Tool at Savannah College of Art and Design.

## Your Role
Help academic schedulers forecast foundation (FOUN) course enrollment and apply qualitative adjustments. You understand SCAD's quarter system, course codes, campus structure, and forecasting methods.

## SCAD Domain Knowledge
- **Term codes**: YYYYQQ format. 10=Fall, 20=Winter, 30=Spring, 40=Summer.
- **Campuses**: Savannah, SCADnow (online)
- **FOUN courses**: FOUN 110, 112, 113, 115, 120, 130, 210, 230, 240, 250, 251
- **Forecasting**: Primary method is sequence-based (from prerequisite enrollment). Fallback is ratio-based.
- **Progression rate**: Students who continue between terms (default 0.95 = 95%)
- **Section capacity**: Students per section (default 20)
- **Buffer percent**: Extra capacity cushion (default 10%)

## Current Configuration
{config_block}

## Active Adjustments
{adjustments_block}

## Response Format
Always respond with a JSON block followed by natural language explanation.

```json
{{
  "intent": "forecast|adjust|help|settings|compare|unknown",
  "parameters": {{
    "term": "Spring 2026",
    "course": "FOUN 110",
    "campus": "Savannah"
  }},
  "adjustments": [
    {{
      "type": "config|output",
      "parameter": "capacity|progression_rate|buffer_percent",
      "operation": "multiply|add|set",
      "value": 1.10,
      "scope": {{"course": "FOUN 110", "campus": "Savannah"}},
      "reason": "Expecting 10% more retakes based on advisor feedback"
    }}
  ],
  "confidence": 0.9
}}
```

Then provide your natural language response.

## Adjustment Examples
- "Expect 10% more retakes in FOUN 110" -> output adjustment: multiply 1.10 on FOUN 110
- "Set section caps to 25" -> config adjustment: capacity = 25
- "Add 20 extra seats for FOUN 230 at SCADnow" -> output adjustment: add 20 on FOUN 230/SCADnow
- "Lower progression rate to 90%" -> config adjustment: progression_rate = 0.90
- "Increase buffer to 15%" -> config adjustment: buffer_percent = 15

## Rules
- Only include adjustments in the JSON when the user clearly requests a change.
- For forecast requests, set intent to "forecast" with the term in parameters.
- For questions about settings/config, set intent to "settings".
- If unclear, set intent to "unknown" and ask for clarification in your response.
- confidence should reflect how sure you are about the parsed intent (0.0 to 1.0).
- Parameters should only include fields that were explicitly mentioned or clearly implied.
- Valid parameter ranges: capacity 1-100, progression_rate 0.0-1.0, buffer_percent 0-100.
- term MUST always be in "Quarter YYYY" format (e.g. "Spring 2026") — never use numeric term codes like "202630".
"""


def build_system_prompt(
    config: Dict[str, Any],
    active_adjustments: List[Dict],
) -> str:
    """Build the system prompt with current config and adjustments injected."""
    config_block = (
        f"- Capacity: {config.get('capacity', 20)} students/section\n"
        f"- Progression Rate: {config.get('progression_rate', 0.95)}\n"
        f"- Buffer: {config.get('buffer_percent', 10.0)}%\n"
        f"- Default Term: {config.get('default_term', 'Spring 2026')}"
    )

    if active_adjustments:
        lines = []
        for adj in active_adjustments:
            scope_parts = []
            scope = adj.get("scope", {})
            if scope.get("course"):
                scope_parts.append(scope["course"])
            if scope.get("campus"):
                scope_parts.append(scope["campus"])
            scope_str = f" [{', '.join(scope_parts)}]" if scope_parts else ""
            if adj["type"] == "config":
                lines.append(f"- {adj.get('parameter', '?')} = {adj['value']}{scope_str}: {adj.get('reason', '')}")
            else:
                lines.append(f"- {adj.get('operation', '?')} {adj['value']}{scope_str}: {adj.get('reason', '')}")
        adjustments_block = "\n".join(lines)
    else:
        adjustments_block = "None currently active."

    return SYSTEM_PROMPT_TEMPLATE.format(
        config_block=config_block,
        adjustments_block=adjustments_block,
    )


# --------------- Parsing ---------------

def parse_llm_response(raw_text: str) -> Dict[str, Any]:
    """Extract JSON block and natural language from LLM response."""
    # Try to find a JSON code block
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
        text_before = raw_text[:json_match.start()].strip()
        text_after = raw_text[json_match.end():].strip()
        natural_text = text_after if text_after else text_before
    else:
        # Try to find raw JSON object
        brace_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if brace_match:
            json_str = brace_match.group(0)
            natural_text = raw_text[brace_match.end():].strip()
            if not natural_text:
                natural_text = raw_text[:brace_match.start()].strip()
        else:
            return {
                "intent": "unknown",
                "parameters": {},
                "adjustments": [],
                "confidence": 0.3,
                "response_text": raw_text.strip(),
            }

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError:
        return {
            "intent": "unknown",
            "parameters": {},
            "adjustments": [],
            "confidence": 0.3,
            "response_text": raw_text.strip(),
        }

    parsed["response_text"] = natural_text or "I've processed your request."
    parsed.setdefault("intent", "unknown")
    parsed.setdefault("parameters", {})
    parsed.setdefault("adjustments", [])
    parsed.setdefault("confidence", 0.5)
    return parsed


# --------------- LLM Client ---------------

class LLMService:
    """Provider-agnostic LLM client."""

    def __init__(self, provider: str, model: Optional[str] = None,
                 base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.provider = provider.lower()
        defaults = PROVIDER_DEFAULTS.get(self.provider, PROVIDER_DEFAULTS["custom"])
        self.model = model or defaults["default_model"]
        self.base_url = base_url or defaults["base_url"]
        self.api_key = api_key or load_api_key()

    def is_configured(self) -> bool:
        """Check if the LLM is ready to use."""
        if self.provider == "ollama":
            return True  # No key needed
        if self.provider == "anthropic":
            return bool(self.api_key)
        # openai, custom
        return bool(self.api_key)

    async def parse_message(
        self,
        message: str,
        history: List[Dict[str, str]],
        config: Dict[str, Any],
        active_adjustments: List[Dict],
    ) -> Dict[str, Any]:
        """Send message to LLM and return parsed structured response.

        Args:
            message: Current user message.
            history: List of {role, content} dicts (last N messages).
            config: Current forecast config.
            active_adjustments: Currently active adjustments for context.

        Returns:
            Dict with intent, parameters, adjustments, confidence, response_text.
        """
        system_prompt = build_system_prompt(config, active_adjustments)

        if self.provider == "anthropic":
            return await self._call_anthropic(system_prompt, message, history)
        else:
            # openai, ollama, custom all use OpenAI-compatible API
            return await self._call_openai_compatible(system_prompt, message, history)

    async def _call_openai_compatible(
        self,
        system_prompt: str,
        message: str,
        history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Call OpenAI-compatible API (OpenAI, Ollama, custom)."""
        try:
            from openai import AsyncOpenAI
        except ImportError:
            return _fallback_response("OpenAI SDK not installed. Run: pip install openai")

        client_kwargs: Dict[str, Any] = {"api_key": self.api_key or "not-needed"}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        client = AsyncOpenAI(**client_kwargs)

        messages = [{"role": "system", "content": system_prompt}]
        for h in history[-20:]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
            )
            raw = response.choices[0].message.content or ""
            return parse_llm_response(raw)
        except Exception as e:
            return _fallback_response(f"LLM call failed: {str(e)}")

    async def _call_anthropic(
        self,
        system_prompt: str,
        message: str,
        history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Call Anthropic API."""
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            return _fallback_response("Anthropic SDK not installed. Run: pip install anthropic")

        client = AsyncAnthropic(api_key=self.api_key)

        messages = []
        for h in history[-20:]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})

        try:
            response = await client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=messages,
                max_tokens=1024,
                temperature=0.3,
            )
            raw = response.content[0].text if response.content else ""
            return parse_llm_response(raw)
        except Exception as e:
            return _fallback_response(f"LLM call failed: {str(e)}")


def _fallback_response(error_msg: str) -> Dict[str, Any]:
    """Return a structured error response for LLM failures."""
    return {
        "intent": "unknown",
        "parameters": {},
        "adjustments": [],
        "confidence": 0.0,
        "response_text": f"I couldn't process that with the AI assistant. {error_msg}",
        "error": error_msg,
    }


def create_llm_service(config: Dict[str, Any]) -> Optional[LLMService]:
    """Create an LLM service from forecast config. Returns None if not configured."""
    llm_cfg = config.get("llm", {})
    provider = llm_cfg.get("provider", "none")
    if not provider or provider == "none":
        return None

    return LLMService(
        provider=provider,
        model=llm_cfg.get("model"),
        base_url=llm_cfg.get("base_url"),
    )
