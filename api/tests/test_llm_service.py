"""Tests for parse_llm_response — the function that extracts structured data
and natural language text from raw LLM output."""

from api.llm_service import parse_llm_response


# --------------- Happy path ---------------

def test_parses_json_code_block_with_trailing_natural_text():
    raw = """\
```json
{
  "intent": "forecast",
  "parameters": {"term": "Spring 2026"},
  "adjustments": [],
  "confidence": 0.9
}
```

I'll run the forecast for Spring 2026 now."""

    result = parse_llm_response(raw)

    assert result["intent"] == "forecast"
    assert result["parameters"] == {"term": "Spring 2026"}
    assert result["adjustments"] == []
    assert result["confidence"] == 0.9
    assert result["response_text"] == "I'll run the forecast for Spring 2026 now."


def test_uses_text_before_json_block_when_no_text_after():
    raw = """\
Sure, here's the parsed intent.

```json
{"intent": "help", "parameters": {}, "adjustments": [], "confidence": 0.8}
```"""

    result = parse_llm_response(raw)

    assert result["intent"] == "help"
    assert result["response_text"] == "Sure, here's the parsed intent."


def test_parses_raw_json_without_code_fences():
    raw = '{"intent": "settings", "parameters": {}, "adjustments": [], "confidence": 0.7} Here are your settings.'

    result = parse_llm_response(raw)

    assert result["intent"] == "settings"
    assert result["confidence"] == 0.7


def test_returns_unknown_intent_when_no_json_present():
    raw = "I'm not sure what you mean. Could you clarify?"

    result = parse_llm_response(raw)

    assert result["intent"] == "unknown"
    assert result["parameters"] == {}
    assert result["adjustments"] == []
    assert result["confidence"] == 0.3
    assert result["response_text"] == "I'm not sure what you mean. Could you clarify?"


def test_returns_fallback_on_malformed_json():
    raw = """\
```json
{intent: forecast, broken json
```
Something went wrong."""

    result = parse_llm_response(raw)

    assert result["intent"] == "unknown"
    assert result["confidence"] == 0.3


def test_applies_defaults_for_missing_json_fields():
    """JSON block that only has intent — missing parameters, adjustments, confidence."""
    raw = '```json\n{"intent": "compare"}\n```\nComparing terms.'

    result = parse_llm_response(raw)

    assert result["intent"] == "compare"
    assert result["parameters"] == {}
    assert result["adjustments"] == []
    assert result["confidence"] == 0.5


def test_text_after_takes_priority_over_text_before():
    """When text exists both before and after the JSON block, text_after wins."""
    raw = """\
Some preamble text.

```json
{"intent": "adjust", "parameters": {}, "adjustments": [], "confidence": 0.85}
```

This is the explanation that should be used."""

    result = parse_llm_response(raw)

    assert result["response_text"] == "This is the explanation that should be used."


def test_adjustment_data_passes_through_correctly():
    raw = """\
```json
{
  "intent": "adjust",
  "parameters": {"course": "FOUN 110", "campus": "Savannah"},
  "adjustments": [
    {
      "type": "output",
      "parameter": "seats",
      "operation": "multiply",
      "value": 1.1,
      "scope": {"course": "FOUN 110"},
      "reason": "Expecting more retakes"
    }
  ],
  "confidence": 0.95
}
```

I've applied a 10% increase to FOUN 110."""

    result = parse_llm_response(raw)

    assert result["intent"] == "adjust"
    assert len(result["adjustments"]) == 1
    adj = result["adjustments"][0]
    assert adj["type"] == "output"
    assert adj["operation"] == "multiply"
    assert adj["value"] == 1.1
    assert adj["scope"] == {"course": "FOUN 110"}


def test_fallback_response_text_when_no_natural_language():
    """JSON block with no surrounding text should use fallback message."""
    raw = '```json\n{"intent": "forecast", "parameters": {}, "adjustments": [], "confidence": 0.9}\n```'

    result = parse_llm_response(raw)

    assert result["response_text"] == "I've processed your request."
