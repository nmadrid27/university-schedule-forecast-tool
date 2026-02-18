"""
Natural language command parser for the chat interface.
Converts user messages into structured commands for the forecasting system.
"""

import re
from typing import Dict, Any


class CommandParser:
    """Parse natural language user input into structured commands."""

    def __init__(self):
        """Initialize the command parser with intent patterns."""
        self.intent_patterns = {
            'forecast': [
                r'\b(forecast|predict|project|estimate)\b',
                r'\b(show|display|generate)\s+(me\s+)?(the\s+)?forecast',
                r'\b(run|create|make)\s+(a\s+)?forecast',
                r'\bwhat.*(will|would).*enrollment\b',
            ],
            'upload': [
                r'\b(upload|import|load|add)\s+(new\s+)?(data|file|csv|excel)',
                r'\b(new|fresh)\s+data\b',
                r'\bupload\b',
            ],
            'configure': [
                r'\b(set|change|adjust|modify|update)\s+(the\s+)?(capacity|buffer|sections|parameters|settings)',
                r'\b(capacity|buffer)\s+(to|=|is)\s+\d+',
                r'\bconfigure\b',
            ],
            'compare': [
                r'\b(compare|comparison|versus|vs)\b',
                r'\b(prophet|sequence|demand|ets).*vs.*\b',
                r'\bdifference between\b',
            ],
            'download': [
                r'\b(download|export|save)\b',
                r'\bget.*csv\b',
                r'\b(give|show)\s+me.*file\b',
            ],
            'help': [
                r'\b(help|guide|how|what can)\b',
                r'\b(explain|tell me about|show me)\b',
            ],
        }

        # Patterns for extracting entities
        self.entity_patterns = {
            'term': r'\b(spring|summer|fall|winter)\s+(\d{4})\b',
            'course_code': r'\b([A-Z]{3,4}\s+\d{3})\b',
            'number': r'\b(\d+)\b',
            'capacity': r'\b(capacity|sections?)\s+(?:to|=|is|of)?\s*(\d+)\b',
            'buffer': r'\b(buffer|extra)\s+(?:to|=|is|of)?\s*(\d+)%?\b',
        }

    def parse(self, user_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Parse user message into structured command.

        Args:
            user_message: The user's input text
            context: Optional context from previous conversation (uploaded files, etc.)

        Returns:
            Dictionary with:
                - intent: The primary intent ('forecast', 'upload', 'configure', etc.)
                - parameters: Extracted parameters (term, courses, capacity, etc.)
                - confidence: Confidence score (0.0 to 1.0)
                - raw_message: Original user input
        """
        if context is None:
            context = {}

        message_lower = user_message.lower()

        # Classify intent
        intent, confidence = self._classify_intent(message_lower)

        # Extract entities based on intent
        parameters = self._extract_parameters(user_message, message_lower, intent, context)

        return {
            'intent': intent,
            'parameters': parameters,
            'confidence': confidence,
            'raw_message': user_message,
        }

    def _classify_intent(self, message_lower: str) -> tuple:
        """
        Classify the intent of the message.

        Returns:
            Tuple of (intent_name, confidence_score)
        """
        scores = {}

        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    score += 1
            if score > 0:
                scores[intent] = score / len(patterns)

        if not scores:
            return 'unknown', 0.0

        # Get intent with highest score
        best_intent = max(scores.items(), key=lambda x: x[1])
        return best_intent[0], best_intent[1]

    def _extract_parameters(self, message: str, message_lower: str, intent: str, context: Dict) -> Dict[str, Any]:
        """Extract parameters based on intent and message content."""
        params = {}

        # Extract term (e.g., "Spring 2026")
        term_match = re.search(self.entity_patterns['term'], message, re.IGNORECASE)
        if term_match:
            params['term'] = f"{term_match.group(1).capitalize()} {term_match.group(2)}"

        # Extract course codes
        course_matches = re.findall(self.entity_patterns['course_code'], message)
        if course_matches:
            params['courses'] = course_matches

        # Intent-specific extraction
        if intent == 'forecast':
            # Check for "all courses"
            if re.search(r'\b(all|every)\s+(courses?|classes?)\b', message_lower):
                params['all_courses'] = True

            # Check for method preference
            if re.search(r'\b(prophet|time series)\b', message_lower):
                params['method'] = 'prophet'
            elif re.search(r'\b(sequence|sequencing)\b', message_lower):
                params['method'] = 'sequence'
            elif re.search(r'\b(demand|cohort)\b', message_lower):
                params['method'] = 'demand'

        elif intent == 'configure':
            # Extract capacity
            capacity_match = re.search(self.entity_patterns['capacity'], message_lower)
            if capacity_match:
                try:
                    params['capacity'] = int(capacity_match.group(2))
                except (ValueError, IndexError):
                    pass

            # Extract buffer
            buffer_match = re.search(self.entity_patterns['buffer'], message_lower)
            if buffer_match:
                try:
                    params['buffer_percent'] = int(buffer_match.group(2))
                except (ValueError, IndexError):
                    pass

        elif intent == 'compare':
            # Extract methods to compare
            methods = []
            if re.search(r'\bprophet\b', message_lower):
                methods.append('prophet')
            if re.search(r'\bsequence\b', message_lower):
                methods.append('sequence')
            if re.search(r'\b(demand|cohort)\b', message_lower):
                methods.append('demand')
            if re.search(r'\bets\b', message_lower):
                methods.append('ets')

            if len(methods) >= 2:
                params['methods'] = methods

        # Add context information
        if context.get('uploaded_files'):
            params['has_data'] = True
        if context.get('current_forecast'):
            params['has_forecast'] = True

        return params

    def get_suggested_response(self, parsed_command: Dict[str, Any]) -> str:
        """
        Get a suggested response based on the parsed command.

        Args:
            parsed_command: Output from parse()

        Returns:
            Suggested response text for the chatbot
        """
        intent = parsed_command['intent']
        params = parsed_command['parameters']

        if intent == 'forecast':
            if params.get('term'):
                return f"I'll generate a forecast for {params['term']}."
            elif params.get('all_courses'):
                return "I'll forecast all available courses."
            else:
                return "I'll generate a forecast. Which term would you like to forecast?"

        elif intent == 'upload':
            return "Please use the file uploader on the right to upload your enrollment data (CSV or Excel format)."

        elif intent == 'configure':
            if params.get('capacity'):
                return f"Setting section capacity to {params['capacity']} students."
            elif params.get('buffer_percent'):
                return f"Setting capacity buffer to {params['buffer_percent']}%."
            else:
                return "You can adjust parameters in the sidebar, or tell me what you'd like to change."

        elif intent == 'compare':
            if params.get('methods'):
                return f"I'll compare these forecasting methods: {', '.join(params['methods'])}."
            else:
                return "Which forecasting methods would you like to compare?"

        elif intent == 'download':
            return "You can download the forecast results as a CSV file using the download button below the results table."

        elif intent == 'help':
            return self._get_help_message()

        else:
            return "I'm not sure I understand. You can ask me to forecast enrollment, upload data, configure settings, or compare methods."

    def _get_help_message(self) -> str:
        """Get the help message with available commands."""
        return """
I can help you with:

**Forecasting:**
- "Forecast Spring 2026"
- "Predict enrollment for all courses"
- "Show me the forecast for FOUN 110"

**Data Management:**
- "Upload new enrollment data"
- "Load historical data"

**Configuration:**
- "Set capacity to 25"
- "Increase buffer to 15%"
- "Use Prophet method"

**Analysis:**
- "Compare Prophet vs Sequence forecasting"
- "Show me the difference between methods"

**Export:**
- "Download forecast as CSV"
- "Export results"

Just ask in plain English and I'll do my best to help!
"""
