"""
Data transformation utilities for time series processing.
Extracted from app.py for modularity.
"""

from datetime import datetime


def quarter_to_date(year, quarter):
    """
    Convert year and quarter to a datetime for time series modeling.

    Args:
        year: Calendar year (int)
        quarter: Quarter name (e.g., 'Fall', 'Winter', 'Spring', 'Summer') or number (1-4)

    Returns:
        datetime object representing the start of that quarter
    """
    quarter_map = {
        'fall': 9, 'winter': 1, 'spring': 4, 'summer': 6,
        '1': 1, '2': 4, '3': 6, '4': 9
    }
    q = str(quarter).lower().strip()
    month = quarter_map.get(q, 1)
    # Winter quarter belongs to the next calendar year conceptually
    if q == 'winter':
        year = year + 1
    return datetime(int(year), month, 1)


def date_to_quarter_label(date):
    """
    Convert datetime back to quarter label.

    Args:
        date: datetime object

    Returns:
        String label like "Winter 2026", "Spring 2026", etc.
    """
    month = date.month
    year = date.year
    if month in [1, 2, 3]:
        return f"Winter {year}"
    elif month in [4, 5]:
        return f"Spring {year}"
    elif month in [6, 7, 8]:
        return f"Summer {year}"
    else:
        return f"Fall {year}"
