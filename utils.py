"""
Shared utilities for the Enrollment Forecasting Tool.
"""

import os
import pandas as pd


def get_project_root():
    """Get the project root directory (where this file lives)."""
    return os.path.dirname(os.path.abspath(__file__))


def get_data_dir():
    """Get the path to the Data directory."""
    return os.path.join(get_project_root(), "Data")


def load_crosswalk():
    """
    Load course code mapping from Data/sequence_crosswalk_template.csv.
    Returns dict mapping legacy_code -> foun_code.
    """
    try:
        crosswalk_path = os.path.join(get_data_dir(), "sequence_crosswalk_template.csv")
        df = pd.read_csv(crosswalk_path)
        return dict(zip(df['legacy_code'].str.strip(), df['foun_code'].str.strip()))
    except FileNotFoundError:
        print("Warning: Crosswalk file not found.")
        return {}
    except Exception as e:
        print(f"Warning: Error loading crosswalk: {e}")
        return {}
