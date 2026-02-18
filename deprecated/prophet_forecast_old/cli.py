"""
Command-line interface for the Prophet Forecast module.
"""

import argparse
import sys
from pathlib import Path

from prophet_forecast.data_loader import load_historical_data
from prophet_forecast.forecaster import UniversityForecaster
from prophet_forecast.config import DEFAULT_SECTION_CAPACITY, DEFAULT_BUFFER_PERCENT


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Prophet-based enrollment forecaster for university scheduling",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to historical enrollment CSV file",
    )
    parser.add_argument(
        "--output", "-o",
        default="forecast_output.csv",
        help="Output path for forecast CSV",
    )
    parser.add_argument(
        "--periods", "-p",
        type=int,
        default=4,
        help="Number of quarters to forecast",
    )
    parser.add_argument(
        "--capacity", "-c",
        type=int,
        default=DEFAULT_SECTION_CAPACITY,
        help="Students per section",
    )
    parser.add_argument(
        "--buffer",
        type=float,
        default=DEFAULT_BUFFER_PERCENT,
        help="Capacity buffer percentage",
    )
    parser.add_argument(
        "--campus",
        default=None,
        help="Filter by campus code (e.g., SAV, NOW, ATL)",
    )
    parser.add_argument(
        "--course",
        default=None,
        help="Filter by course code (e.g., 'DRAW 100')",
    )
    parser.add_argument(
        "--by-campus",
        action="store_true",
        help="Create separate forecasts per campus",
    )
    parser.add_argument(
        "--growth",
        type=float,
        default=0.0,
        help="Growth percentage adjustment (e.g., 5 for 5%% growth)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress output messages",
    )
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1
    
    if not args.quiet:
        print(f"Loading data from: {args.input}")
    
    # Load data
    df = load_historical_data(
        filepath=input_path,
        campus_filter=args.campus,
        course_filter=args.course,
    )
    
    if df.empty:
        print("Error: No data found with the specified filters", file=sys.stderr)
        return 1
    
    if not args.quiet:
        print(f"Loaded {len(df)} records")
        print(f"Courses: {df['course_code'].nunique()}")
        print(f"Campuses: {df['campus'].unique().tolist()}")
    
    # Create and train forecaster
    forecaster = UniversityForecaster(
        section_capacity=args.capacity,
        buffer_percent=args.buffer,
        by_campus=args.by_campus,
    )
    
    if not args.quiet:
        print("Training Prophet models...")
    
    forecaster.fit(df)
    
    if not args.quiet:
        print(f"Trained {len(forecaster.models)} models")
    
    # Generate forecasts
    if not args.quiet:
        print(f"Forecasting {args.periods} quarters ahead...")
    
    forecast_df = forecaster.predict(
        periods=args.periods,
        growth_percent=args.growth,
    )
    
    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    forecast_df.to_csv(output_path, index=False)
    
    if not args.quiet:
        print(f"\n--- Forecast Summary ---")
        print(forecast_df.to_string(index=False))
        print(f"\nSaved to: {args.output}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
