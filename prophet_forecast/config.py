"""
Configuration constants for the Prophet Forecast module.
"""

# Term code suffix to quarter name mapping
# YYYYMM format: last 2 digits determine quarter
TERM_MAP = {
    10: "Fall",
    20: "Winter",
    30: "Spring",
    40: "Summer",
}

# Reverse mapping: quarter name to month for datetime conversion
QUARTER_TO_MONTH = {
    "fall": 9,
    "winter": 1,
    "spring": 4,
    "summer": 6,
}

# Default section capacity (students per section)
DEFAULT_SECTION_CAPACITY = 20

# Default buffer percentage for section planning
DEFAULT_BUFFER_PERCENT = 10

# Prophet model configuration
PROPHET_CONFIG = {
    "yearly_seasonality": True,
    "weekly_seasonality": False,
    "daily_seasonality": False,
    "seasonality_mode": "multiplicative",
}

# Default summer ratio relative to Spring (used when data is sparse)
DEFAULT_SUMMER_RATIO = 0.15
