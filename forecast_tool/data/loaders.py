"""
Data loading utilities for enrollment forecasting.
Extracted from app.py for modularity.
"""

import pandas as pd
import streamlit as st


def load_course_mapping():
    """Load course code mapping from Data/sequence_crosswalk_template.csv."""
    try:
        crosswalk_path = "Data/sequence_crosswalk_template.csv"
        df_cross = pd.read_csv(crosswalk_path)
        # Create dictionary: legacy_code -> foun_code
        # Strip whitespace just in case
        mapping = dict(zip(df_cross['legacy_code'].str.strip(), df_cross['foun_code'].str.strip()))
        return mapping
    except FileNotFoundError:
        st.warning("Crosswalk file (Data/sequence_crosswalk_template.csv) not found.")
        return {}
    except Exception as e:
        st.warning(f"Error loading crosswalk: {e}")
        return {}


def load_historical_data():
    """Load and process historical data from Data/FOUN_Historical.csv."""
    try:
        hist_path = "Data/FOUN_Historical.csv"
        df_hist = pd.read_csv(hist_path)

        # Process columns
        # Combine SUBJ and CRS NUMBER to create Course
        df_hist['course_code'] = df_hist['SUBJ'] + " " + df_hist['CRS NUMBER'].astype(str)

        # Rename Enrollment
        df_hist = df_hist.rename(columns={'ACT ENR': 'enrollment'})

        # Add Waitlist column (0 for historical)
        df_hist['waitlist'] = 0

        # Parse TERM (YYYYMM)
        # 10=Fall (prev year), 20=Winter, 30=Spring, 40=Summer
        def parse_term(term_code):
            term_str = str(term_code)
            year_part = int(term_str[:4])
            suffix = int(term_str[4:])

            if suffix == 10:
                return 'Fall', year_part - 1
            elif suffix == 20:
                return 'Winter', year_part
            elif suffix == 30:
                return 'Spring', year_part
            elif suffix == 40:
                return 'Summer', year_part
            return None, None

        df_hist[['quarter', 'year']] = df_hist['TERM'].apply(lambda x: pd.Series(parse_term(x)))

        # Apply Course Mapping
        mapping = load_course_mapping()
        if mapping:
            # Use map to replace, fillna with original to keep codes that don't need mapping
            df_hist['course_code'] = df_hist['course_code'].map(mapping).fillna(df_hist['course_code'])

        return df_hist[['year', 'quarter', 'course_code', 'enrollment', 'waitlist']]

    except FileNotFoundError:
        st.warning("Historical data file (Data/FOUN_Historical.csv) not found.")
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"Error loading historical data: {e}")
        return pd.DataFrame()


def calculate_summer_ratios(df):
    """Calculate average Summer/Spring ratio for each course."""
    ratios = {}

    # Ensure we have necessary columns
    if 'course_code' not in df.columns or 'quarter' not in df.columns or 'year' not in df.columns:
        return ratios

    # Group by Course, Year, Quarter
    # We need to sum enrollment in case there are multiple rows per course/term
    df_agg = df.groupby(['course_code', 'year', 'quarter'])['enrollment'].sum().reset_index()

    courses = df_agg['course_code'].unique()

    for course in courses:
        course_df = df_agg[df_agg['course_code'] == course]
        course_ratios = []

        years = course_df['year'].unique()
        for year in years:
            # Find Spring and Summer for this year
            spring = course_df[(course_df['year'] == year) & (course_df['quarter'].str.lower() == 'spring')]
            summer = course_df[(course_df['year'] == year) & (course_df['quarter'].str.lower() == 'summer')]

            if not spring.empty and not summer.empty:
                spring_val = spring['enrollment'].values[0]
                summer_val = summer['enrollment'].values[0]

                if spring_val > 0:
                    course_ratios.append(summer_val / spring_val)

        if course_ratios:
            ratios[course] = sum(course_ratios) / len(course_ratios)

    return ratios
