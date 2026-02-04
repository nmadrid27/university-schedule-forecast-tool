"""
Data loading and preprocessing utilities for enrollment forecasting.
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Union

from prophet_forecast.config import TERM_MAP, QUARTER_TO_MONTH


def parse_term_code(term_code: Union[int, str]) -> tuple[str, int]:
    """
    Parse a term code (YYYYMM) into quarter name and academic year.
    
    Args:
        term_code: 6-digit term code (e.g., 202210 = Fall 2021)
        
    Returns:
        Tuple of (quarter_name, year)
        
    Examples:
        >>> parse_term_code(202210)
        ('Fall', 2021)
        >>> parse_term_code(202220)
        ('Winter', 2022)
    """
    term_str = str(int(term_code))
    year_part = int(term_str[:4])
    suffix = int(term_str[4:])
    
    quarter = TERM_MAP.get(suffix, "Unknown")
    
    # Fall term belongs to the previous academic year
    if suffix == 10:
        year = year_part - 1
    else:
        year = year_part
        
    return quarter, year


def term_to_date(year: int, quarter: str) -> datetime:
    """
    Convert year and quarter to a datetime for time series modeling.
    
    Args:
        year: Academic year
        quarter: Quarter name (Fall, Winter, Spring, Summer)
        
    Returns:
        datetime representing the start of the quarter
    """
    q_lower = quarter.lower().strip()
    month = QUARTER_TO_MONTH.get(q_lower, 1)
    
    # Winter quarter belongs to the next calendar year
    if q_lower == "winter":
        year = year + 1
        
    return datetime(int(year), month, 1)


def date_to_quarter_label(date: datetime) -> str:
    """
    Convert a datetime back to a quarter label.
    
    Args:
        date: datetime object
        
    Returns:
        Quarter label (e.g., "Spring 2026")
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


def load_historical_data(
    filepath: Union[str, Path],
    campus_filter: str = None,
    course_filter: str = None,
) -> pd.DataFrame:
    """
    Load and process historical enrollment data.
    
    Args:
        filepath: Path to the historical CSV file
        campus_filter: Optional campus code to filter by (e.g., "SAV")
        course_filter: Optional course code to filter by (e.g., "DRAW 100")
        
    Returns:
        DataFrame with columns: year, quarter, course_code, campus, enrollment, ds
    """
    df = pd.read_csv(filepath)
    
    # Create course code from SUBJ and CRS NUMBER
    df["course_code"] = df["SUBJ"].astype(str).str.strip() + " " + df["CRS NUMBER"].astype(str).str.strip()
    
    # Rename columns for consistency
    df = df.rename(columns={
        "ACT ENR": "enrollment",
        "CAMPUS": "campus",
    })
    
    # Parse term codes
    parsed = df["TERM"].apply(parse_term_code)
    df["quarter"] = parsed.apply(lambda x: x[0])
    df["year"] = parsed.apply(lambda x: x[1])
    
    # Apply filters
    if campus_filter:
        df = df[df["campus"].str.upper() == campus_filter.upper()]
        
    if course_filter:
        df = df[df["course_code"].str.upper() == course_filter.upper()]
    
    # Create datetime column for Prophet
    df["ds"] = df.apply(lambda r: term_to_date(r["year"], r["quarter"]), axis=1)
    
    # Keep relevant columns
    columns = ["year", "quarter", "course_code", "campus", "enrollment", "ds"]
    return df[columns]


def aggregate_enrollment(
    df: pd.DataFrame,
    by_campus: bool = False,
) -> pd.DataFrame:
    """
    Aggregate enrollment data by course and optionally by campus.
    
    Args:
        df: DataFrame from load_historical_data
        by_campus: If True, aggregate by (course, campus, date); otherwise just (course, date)
        
    Returns:
        Aggregated DataFrame ready for Prophet
    """
    if by_campus:
        group_cols = ["course_code", "campus", "ds", "year", "quarter"]
    else:
        group_cols = ["course_code", "ds", "year", "quarter"]
    
    agg_df = df.groupby(group_cols, as_index=False)["enrollment"].sum()
    agg_df = agg_df.sort_values(["course_code", "ds"])
    
    return agg_df
