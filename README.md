# SCAD FOUN Enrollment Forecasting Tool

Predicts Foundation course enrollment and calculates section needs for upcoming terms using sequence-based forecasting, with a 3-model time-series ensemble (Prophet + ETS + ARIMA) as an alternative method.

## Quick Start (macOS)

### First time? Run the installer:

1. Double-click **`install.command`**
2. Wait for "Installation Complete!" (5-10 minutes on first run)

This installs Homebrew, Python, Node.js, and all dependencies. Safe to run again if needed.

### Launch the tool:

1. Double-click **`Forecast_Tool_Launcher.command`**
2. Wait for "Forecast Tool is running!" — your browser opens automatically
3. Type a forecast request in the chat, e.g. "Forecast Spring 2026"

### Stop the tool:

Double-click **`stop.command`**, or close the Terminal window.

### Full user guide:

See **[docs/HANDOFF_GUIDE.md](docs/HANDOFF_GUIDE.md)** for detailed instructions, troubleshooting, and FAQ.

## Troubleshooting

### Turbopack Database Error

If you encounter a "Failed to open database" error:
1. Double-click `stop.command` to stop everything
2. Delete the folder `frontend/.next`
3. Double-click `Forecast_Tool_Launcher.command` to restart

### Port Already in Use

Double-click `stop.command` to kill any leftover processes, then relaunch.

### Something Else?

See the full troubleshooting section in [docs/HANDOFF_GUIDE.md](docs/HANDOFF_GUIDE.md#troubleshooting).

## Data Format

Upload a CSV or Excel file with these columns:

| Column | Required | Description |
|--------|----------|-------------|
| year | ✅ | 4-digit year (2022, 2023, etc.) |
| quarter | ✅ | Fall, Winter, Spring, Summer (or 1-4) |
| course_code | ✅ | Course identifier (FILM101, GRDS320) |
| enrollment | ✅ | Number of enrolled students |
| program | ❌ | Optional: for grouping/filtering |

## ✨ Features

### Modern Frontend
- **Intuitive UI**: Clean, responsive design built with React and Tailwind CSS
- **Real-time Updates**: Instant feedback on parameter changes
- **Data Upload**: Easy CSV/Excel file import
- **Results Export**: Download forecasts as CSV
- **Configuration**: Adjustable forecasting parameters
- **Professional Design**: Component-based architecture with Radix UI

### Forecasting Engine
- **Dual-model forecasting**: Prophet (seasonality/trends) + Exponential Smoothing (short-term patterns)
- **Ensemble predictions**: Weighted combination of both models
- **Confidence intervals**: Lower/upper bounds for planning scenarios
- **Section calculator**: Converts forecasts to section counts with configurable capacity and buffer
- **Batch processing**: Forecast multiple courses simultaneously
- **Export**: Download results as CSV

## Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| Students per Section | 25 | Section capacity |
| Capacity Buffer | 10% | Extra room for late adds |
| Quarters to Forecast | 2 | 1-4 quarters ahead |
| Prophet Weight | 0.6 | Model weighting (0.6 Prophet, 0.4 ARIMA) |

## Model Details

- **Prophet**: Best for quarterly seasonality and multi-year trends. Handles missing data gracefully.
- **ARIMA(1,1,1)**: Captures short-term autocorrelation patterns. Falls back to AR(1) if needed.
- **Ensemble**: Weighted average produces more robust predictions than either model alone.

## Minimum Data Requirements

- At least 2 quarters of historical data per course (minimum)
- Recommended: 4-8 quarters for better accuracy
- More data improves forecast quality

## 🏗️ Architecture (v3.0)

### Frontend Stack

**Modern React Application** (`frontend/`):
- **Framework**: Next.js 16.1.6 with React 19
- **Styling**: Tailwind CSS 4 with Postcss
- **Components**: Radix UI primitives
- **Icons**: Lucide React
- **Dev Server**: http://localhost:3000

### Backend / Python Analysis

Python forecasting engine (used by frontend or CLI):
```
forecast_tool/
├── forecasting/       # Prediction models
│   ├── prophet_forecast.py  # Prophet model
│   ├── ets_forecast.py      # Exponential Smoothing
│   └── ensemble.py          # Model combination
├── data/              # Data handling
│   ├── loaders.py           # Load CSV/Excel
│   ├── transformers.py      # Time series conversion
│   └── validators.py        # Data validation
└── config/            # Configuration
    └── settings.py          # Default settings
```

### Key Files

- **`frontend/`** - Next.js React application (PRIMARY UI)
- **`Forecast_Tool_Launcher.command`** - One-click launcher
- **`forecast_spring26_from_sequence_guides.py`** - Production CLI script
- **`deprecated/`** - Archived Streamlit files (legacy)

## 📚 Documentation

- **[AGENTS.md](AGENTS.md)** - Production workflow
- **[CLAUDE.md](CLAUDE.md)** - Developer documentation
- **[PRD_Frontend_Interface.md](PRD_Frontend_Interface.md)** - Product requirements
- **[frontend/README.md](frontend/README.md)** - Frontend development guide

## ⚠️ Deprecated

The Streamlit-based interfaces have been deprecated in favor of the modern Next.js frontend:
- `app_chat.py` - **Deprecated** (moved to `deprecated/`)
- `app.py` - **Deprecated** (moved to `deprecated/`)
- Legacy Streamlit files archived in `deprecated/` directory

**Why?** The Next.js frontend provides better UX, performance, and maintainability.

## 🔧 Advanced Usage

### Production Forecasting (CLI)

For automated/batch forecasting:

```bash
python3 forecast_spring26_from_sequence_guides.py --config forecast_config.json
```

See [AGENTS.md](AGENTS.md) for production workflow details.

### Configuration File

Create `forecast_config.json`:

```json
{
  "sequence_map": "Data/FOUN_sequencing_map_by_major.csv",
  "fall_enroll": "Data/Master Schedule of Classes.csv",
  "winter_enroll": "Data/Master Schedule of Classes.csv",
  "fall_term_code": "202610",
  "winter_term_code": "202620",
  "capacity": 20,
  "progression_rate": 0.95
}
```
