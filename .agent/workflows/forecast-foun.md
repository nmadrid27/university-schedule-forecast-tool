---
description: How to forecast FOUN course demand by term and campus
---

# FOUN Demand Forecasting Workflow

## Prerequisites

- Activate virtual environment: `source .venv/bin/activate`
- Ensure pandas and openpyxl are installed

## Step 1: Identify the Target Term

Determine which term you're forecasting:

- **Fall/Winter/Spring**: Use admissions data + sequence progression
- **Summer**: Use previous Spring enrollment with reduced rates

## Step 2: Load Source Data

// turbo

```bash
# Check available data files
ls -la Data/*.csv Data/*.xlsx
```

For **Summer forecasting**, load the Spring forecast:

```python
spring = pd.read_csv('Data/Spring_2026_FOUN_Combined_Forecast.csv')
```

## Step 3: Apply Forecasting Rates

### For Summer Terms

Use these validated progression rates from Spring to Summer:

| Course | SAV Rate | SCADnow Rate | Source Course |
|--------|----------|--------------|---------------|
| FOUN 112 | 35% | 4% | Spring FOUN 110 |
| FOUN 113 | 30% | 34% | Spring FOUN 111 |
| FOUN 220 | 6% + 8% | 7% | Spring FOUN 112 + 113 |
| FOUN 245 | 6% | 0% | Spring FOUN 113 |
| FOUN 230 | 2% | 0% | Spring FOUN 112 |
| FOUN 240 | 1.6% | 0% | Spring FOUN 112 |
| FOUN 251 | 24% | 0% | Spring FOUN 245 |
| FOUN 260 | 15% | 16% | Spring FOUN 250 |
| FOUN 250 | 3% | 0% | Spring FOUN 240 |

### For Retakes

Add to base demand:

- **1% scenario**: `Spring_enrollment × 0.01` for FOUN 110, 111, 112, 113
- **2% scenario**: `Spring_enrollment × 0.02` for FOUN 110, 111, 112, 113

## Step 4: Calculate Sections

```python
SECTION_SIZE = 18
sections = max(1, (demand + 17) // 18) if demand > 0 else 0
```

## Step 5: Generate Output

Save forecast to:

```
Data/{Term}_{Year}_FOUN_Forecast_By_Campus.csv
Data/{Term}_{Year}_FOUN_Forecast_By_Campus_With_Retakes.csv
```

## Step 6: Validate (Optional)

If seat projection files are available, compare:

- Forecast should be ~2-3x FY-only projections
- Check for missing campus data (ATL often missing)
- Verify section totals match expected ranges

## Expected Summer Totals

| Campus | Base | +1% Retakes | +2% Retakes |
|--------|------|-------------|-------------|
| SAV | 34-36 | 39-40 | 41-42 |
| SCADnow | 5 | 5 | 5 |
| **Total** | **39-41** | **44-45** | **46-47** |

## Reference

See `foun_demand_logic.md` for complete methodology documentation.
