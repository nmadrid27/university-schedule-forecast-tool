"""
Response formatting utilities for the chat interface.
Generates user-friendly responses based on command outcomes.
"""

from typing import Dict, Any


def format_forecast_response(forecast_data: Dict[str, Any]) -> str:
    """
    Format a response for forecast results.

    Args:
        forecast_data: Dictionary containing forecast results

    Returns:
        Formatted response string
    """
    num_courses = forecast_data.get('num_courses', 0)
    term = forecast_data.get('term', 'the selected term')

    response = f"Forecast complete for {num_courses} courses in {term}.\n\n"
    response += "Results are displayed on the right. You can:\n"
    response += "- Review the forecast table\n"
    response += "- View trend visualizations\n"
    response += "- Download results as CSV\n"

    return response


def format_upload_response(upload_data: Dict[str, Any]) -> str:
    """
    Format a response for file upload.

    Args:
        upload_data: Dictionary containing upload results

    Returns:
        Formatted response string
    """
    num_records = upload_data.get('num_records', 0)
    num_courses = upload_data.get('num_courses', 0)
    filename = upload_data.get('filename', 'your file')

    response = f"Successfully loaded {filename}!\n\n"
    response += f"- {num_records} enrollment records\n"
    response += f"- {num_courses} unique courses\n\n"
    response += "You can now ask me to forecast any term."

    return response


def format_error_response(error_type: str, details: str = None) -> str:
    """
    Format an error response.

    Args:
        error_type: Type of error ('missing_data', 'invalid_input', etc.)
        details: Optional error details

    Returns:
        Formatted error message
    """
    error_messages = {
        'missing_data': "I need enrollment data to generate a forecast. Please upload a CSV or Excel file first.",
        'insufficient_data': "There isn't enough historical data for this course. I need at least 2 quarters of data.",
        'invalid_course': "I couldn't find that course code in the uploaded data.",
        'invalid_term': "Please specify a valid term (e.g., 'Spring 2026', 'Summer 2026').",
        'invalid_parameter': "That parameter value doesn't look right. Please check and try again.",
    }

    base_message = error_messages.get(error_type, "Something went wrong.")

    if details:
        return f"{base_message}\n\nDetails: {details}"
    return base_message


def format_config_response(config_changes: Dict[str, Any]) -> str:
    """
    Format a response for configuration changes.

    Args:
        config_changes: Dictionary of parameter changes

    Returns:
        Formatted response string
    """
    response = "Settings updated:\n\n"

    for param, value in config_changes.items():
        param_display = param.replace('_', ' ').title()
        response += f"- {param_display}: {value}\n"

    response += "\nThe next forecast will use these settings."

    return response


def format_welcome_message() -> str:
    """Get the initial welcome message for the chat interface."""
    return """
Welcome to the SCAD FOUN Enrollment Forecasting Tool!

I can help you forecast course enrollments using AI-powered time series analysis.

**To get started:**
1. Upload your enrollment data (CSV or Excel)
2. Tell me which term you want to forecast (e.g., "Forecast Spring 2026")
3. Review the results and download as needed

**Try asking:**
- "Forecast Spring 2026"
- "Show me enrollment for FOUN 110"
- "Compare forecasting methods"
- "Set capacity to 25 students"

What would you like to do?
"""


def format_method_comparison_intro(methods: list) -> str:
    """
    Format introduction for method comparison.

    Args:
        methods: List of method names to compare

    Returns:
        Formatted introduction string
    """
    methods_str = " vs ".join(methods)
    return f"Comparing {methods_str}...\n\nI'll run both methods and show you the differences."
