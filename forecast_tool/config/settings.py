"""
Default configuration settings for the forecasting tool.
"""

# Forecasting Parameters
DEFAULT_SECTION_CAPACITY = 20
DEFAULT_BUFFER_PERCENT = 10
DEFAULT_FORECAST_QUARTERS = 2
DEFAULT_PROPHET_WEIGHT = 0.6
DEFAULT_SUMMER_RATIO = 0.15
DEFAULT_GROWTH_PERCENT = 0

# Data Paths
CROSSWALK_PATH = "Data/sequence_crosswalk_template.csv"
HISTORICAL_DATA_PATH = "Data/FOUN_Historical.csv"
MASTERLIST_BY_MAJOR_PATH = "Data/Masterlist_FOUN_courses_by_major.xlsx"
MASTERLIST_BY_QUARTER_PATH = "Data/Masterlist_FOUN_courses_by_quarter.xlsx"

# Model Configuration
PROPHET_YEARLY_SEASONALITY = True
PROPHET_WEEKLY_SEASONALITY = False
PROPHET_DAILY_SEASONALITY = False
ETS_SEASONAL_PERIODS = 4  # Quarterly data

# UI Configuration
APP_TITLE = "SCAD FOUN Enrollment Forecasting Tool"
APP_ICON = "📊"
DEFAULT_LAYOUT = "wide"
