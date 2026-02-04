# Prophet Forecast Module

A standalone Prophet-based enrollment forecasting module for university scheduling.

## Installation

Requires the dependencies already in `requirements.txt`:

- prophet>=1.1.4
- pandas>=2.0.0
- numpy>=1.24.0

## Usage

### Command Line

```bash
# Forecast next 4 quarters using historical data
python -m prophet_forecast.cli --input Data/FOUN_Historical.csv --output Data/forecast.csv --periods 4

# Forecast for a specific campus
python -m prophet_forecast.cli --input Data/FOUN_Historical.csv --output Data/sav_forecast.csv --periods 2 --campus SAV

# Custom section capacity
python -m prophet_forecast.cli --input Data/FOUN_Historical.csv --output Data/forecast.csv --periods 4 --capacity 25
```

### Python API

```python
from prophet_forecast import UniversityForecaster, load_historical_data

# Load data
df = load_historical_data("Data/FOUN_Historical.csv")

# Create forecaster
forecaster = UniversityForecaster(section_capacity=20, buffer_percent=10)

# Train and predict
forecaster.fit(df)
forecast_df = forecaster.predict(periods=4)

print(forecast_df)
```

## Input Data Format

CSV with columns:

- `DEPT`: Department (e.g., "FOUN")
- `SUBJ`: Subject code (e.g., "DRAW", "DSGN")
- `CRS NUMBER`: Course number (e.g., 100, 101)
- `CAMPUS`: Campus code (e.g., "SAV", "NOW", "ATL")
- `MAX ENR`: Maximum enrollment capacity
- `ACT ENR`: Actual enrollment
- `TERM`: Term code (YYYYMM format; 10=Fall, 20=Winter, 30=Spring, 40=Summer)

## Output Format

CSV with columns:

- `course`: Course code (e.g., "DRAW 100")
- `campus`: Campus code
- `quarter`: Quarter label (e.g., "Spring 2026")
- `forecast`: Predicted enrollment
- `lower_bound`: Lower confidence bound
- `upper_bound`: Upper confidence bound
- `sections`: Recommended number of sections
