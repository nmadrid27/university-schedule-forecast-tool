# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the **SCAD FOUN Enrollment Forecasting Tool** - a production data analysis tool for forecasting foundation course section needs at Savannah College of Art and Design.

- **Primary Purpose:** Forecast Spring/Summer term FOUN course enrollments and section requirements
- **Technology:** Python-based analysis tool with Streamlit web UI and CLI scripts
- **Data Source:** SCAD enrollment data (Fall 2025, Winter 2026 actuals)
- **Output:** Section recommendations by campus (Savannah vs SCADnow online)

## Project Type

**Active Production Tool** - This is a working enrollment forecasting system with:
- Streamlit web applications (chat + classic interfaces)
- Production CLI scripts for batch forecasting
- Prophet + Exponential Smoothing ensemble models
- Real SCAD enrollment data and sequencing guides

## Architecture

### Version 2.0 - Modular Package Design

**NEW:** The forecasting logic has been refactored into a modular `forecast_tool/` package to support both chat and classic interfaces.

```
forecast_tool/
├── chat/              # Natural language interface
│   ├── command_parser.py    # Parse user intents from text
│   ├── conversation.py      # Manage chat state and history
│   └── responses.py         # Format bot responses
├── ui/                # Streamlit UI components
│   ├── chat_window.py       # Chat interface (left panel)
│   └── output_window.py     # Results display (right panel)
├── forecasting/       # Prediction models
│   ├── prophet_forecast.py  # Prophet time series model
│   ├── ets_forecast.py      # Exponential Smoothing model
│   └── ensemble.py          # Model combination + section calc
├── data/              # Data management
│   ├── loaders.py           # CSV/Excel loading + course mapping
│   ├── transformers.py      # Quarter/date conversions
│   └── validators.py        # Data validation (future)
└── config/            # Settings
    └── settings.py          # Default configuration values
```

### Main Applications

1. **Chat Interface** (`app_chat.py` - NEW in v2.0)
   - Natural language input for forecasting
   - Conversational workflow with guided prompts
   - Two-column layout: chat (left) + results (right)
   - Context-aware command parsing
   - Session state management
   - Integrated file upload and configuration
   - **Target Users:** Non-technical staff, administrators

2. **Classic Interface** (`app.py` - 798 lines, original)
   - Form-based interactive UI
   - Direct parameter controls
   - Prophet + Exponential Smoothing ensemble forecasting
   - Configurable parameters (capacity, buffer, growth targets)
   - CSV/Excel upload and export capabilities
   - Historical data integration
   - **Target Users:** Power users, analysts

3. **One-Click Launcher** (`Forecast_Tool_Launcher.command` - NEW)
   - Shell script for non-technical users
   - Auto-creates Python virtual environment
   - Installs dependencies automatically
   - Launches Streamlit and opens browser
   - **Target Users:** Anyone without Python experience

4. **Production Forecasting Scripts** (CLI)
   - `forecast_spring26_from_sequence_guides.py` - **PRIMARY PRODUCTION SCRIPT**
   - `forecast_fall26_from_sequence_guides.py` - Fall term forecasting
   - `forecast_spring26_from_seat_projection.py` - Seat projection methodology
   - `calculate_foun_demand.py` - FOUN demand calculator (247 lines)
   - `spring_2026_demand_forecast.py` - Demand-based approach
   - `spring_2026_forecast.py` - Core forecasting logic
   - **Target Users:** Automated workflows, batch processing

5. **Prophet Forecast Module** (`prophet_forecast/`)
   - Modular CLI tool for Prophet-based forecasting
   - Components: `cli.py`, `forecaster.py`, `data_loader.py`, `config.py`
   - Standalone command-line interface
   - **Note:** Separate from main forecast_tool package

6. **Utility Scripts**
   - `test_parser.py` - Data parsing tests
   - `inspect_data.py` - Data exploration
   - `analyze_ratio.py` - Ratio analysis
   - `utils.py` - Helper functions

### Technology Stack

**Core Dependencies:**
- `streamlit>=1.28.0` - Web UI framework
- `prophet>=1.1.4` - Facebook Prophet time series forecasting
- `statsmodels>=0.14.0` - ARIMA, Exponential Smoothing models
- `pandas>=2.0.0` - Data manipulation
- `numpy>=1.24.0` - Numerical computing
- `openpyxl>=3.1.0` - Excel file support

**Python Version:** 3.10+ (recommended)

## Standard Workflow

### Production Forecasting (Recommended Method)

This is the standard workflow used for official FOUN section forecasts:

1. **Update Configuration**
   ```bash
   # Edit forecast_config.json with current term codes and file paths
   vim forecast_config.json
   ```

2. **Run Production Forecast**
   ```bash
   python3 forecast_spring26_from_sequence_guides.py --config forecast_config.json
   ```

3. **Review Output**
   - Default output: `Data/Spring_2026_FOUN_Forecast_SAV_SCADnow_From_Sequence_Guides.csv`
   - Contains: course, campus, projected seats, recommended sections

### Interactive Forecasting - Chat Interface (NEW - Recommended for Most Users)

**One-Click Launch:**

```bash
# macOS: Double-click in Finder
Forecast_Tool_Launcher.command

# Or run from terminal
./Forecast_Tool_Launcher.command
```

**Manual Launch:**

```bash
# Install dependencies
pip install -r requirements.txt

# Launch chat interface
streamlit run app_chat.py
```

**Features:**
- Natural language input ("Forecast Spring 2026")
- Conversational guidance
- Context-aware suggestions
- Integrated file upload and configuration
- Same forecasting engine as classic UI

**Example Interaction:**

```
User: Forecast Spring 2026
Bot:  I'll generate a forecast. Please upload your enrollment data first.

[Upload CSV file]

User: Forecast all courses for Spring 2026
Bot:  Forecast complete for 12 courses in Spring 2026.
      Results are displayed on the right.
```

See [QUICKSTART_CHAT.md](QUICKSTART_CHAT.md) for detailed usage guide.

### Interactive Forecasting - Classic UI (Original Interface)

For power users who prefer traditional form-based controls:

1. **Install Dependencies**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Launch Classic App**
   ```bash
   streamlit run app.py
   ```
   - Opens browser at http://localhost:8501
   - Upload CSV/Excel with historical enrollment data
   - Adjust parameters in sidebar
   - Download forecast results

3. **Configuration Options in UI**
   - Students per Section (default: 20)
   - Capacity Buffer % (default: 10%)
   - Quarters to Forecast (1-4, default: 2)
   - Prophet Weight vs Exp. Smoothing (default: 0.6)
   - Target Growth % (-20% to +20%)
   - Include Waitlist in Demand (optional)

## Data Files

### Key Input Files

Located in `Data/` directory:

**Current Term Enrollments:**
- `FAll25.csv` (57KB) - Fall 2025 actual enrollments
- `Winter26.csv` (56KB) - Winter 2026 actual enrollments
- `Master Schedule of Classes.csv` (9.2MB) - Complete schedule with all terms

**Sequencing Logic:**
- `FOUN_sequencing_map_by_major.csv` (21KB) - **CRITICAL FILE**
  - Maps Fall/Winter prerequisite courses → Spring FOUN courses
  - Organized by major/program
  - Includes "CHOICE" course options
  - Campus-specific filtering (SAV/NOW/General)

**Historical Data:**
- `FOUN_Historical.csv` (139KB) - Multi-year FOUN enrollment history
- `Spring25.csv`, `Summer25.csv` - Previous term actuals for ratio analysis

**Admissions Data:**
- `MZSSFDC-SF Admission Deposit Comparison - Fall 2025.xlsx`
- `PZSAAPF-SL31 - Accepted Applicants with Latest Decision.xlsx`

**Reference Data:**
- `Masterlist.md` (117KB) - Complete course catalog reference
- `Masterlist_FOUN_courses_by_major.xlsx` - FOUN courses by major
- `Masterlist_FOUN_courses_by_quarter.xlsx` - FOUN courses by quarter

### Output Files (Generated Forecasts)

Recent forecasts in `Data/`:
- `Spring_2026_FOUN_Forecast_SAV_SCADnow_From_Sequence_Guides.csv` - Latest (Jan 15)
- `Summer_2026_FOUN_Forecast.csv` - Latest (Jan 16)
- Multiple Spring 2026 variants with different methodologies

## Configuration

### `forecast_config.json`

Controls the production forecasting script:

```json
{
  "sequence_map": "Data/FOUN_sequencing_map_by_major.csv",
  "fall_enroll": "Data/Master Schedule of Classes.csv",
  "winter_enroll": "Data/Master Schedule of Classes.csv",
  "fall_term_code": "202610",
  "winter_term_code": "202620",
  "output": "Data/Spring_2026_FOUN_Forecast_SAV_SCADnow_From_Sequence_Guides.csv",
  "capacity": 20,
  "progression_rate": 0.95
}
```

**Key Parameters:**
- `sequence_map` - Path to sequencing guide CSV
- `fall_enroll`, `winter_enroll` - Enrollment data files
- `fall_term_code`, `winter_term_code` - SCAD term codes (YYYYQQ format)
- `capacity` - Students per section (default: 20)
- `progression_rate` - Term-to-term retention rate (default: 0.95 = 95%)
- `output` - Output file path

### Term Code Format

SCAD uses 6-digit term codes: `YYYYQQ`
- `202610` - Fall 2025 (2026 academic year, quarter 1)
- `202620` - Winter 2026 (2026 academic year, quarter 2)
- `202630` - Spring 2026 (2026 academic year, quarter 3)
- `202640` - Summer 2026 (2026 academic year, quarter 4)

## Forecasting Logic

### Sequencing-Based Methodology (Primary)

**How It Works:**

1. **Sequencing Guide Lookup**
   - Maps Fall/Winter courses to Spring FOUN courses by major
   - Example: MASH majors taking FILM 100 in Fall → FOUN 110 in Spring
   - "CHOICE" entries split demand evenly across listed options

2. **Campus Detection**
   - **SCADnow (online):** Room = `OLNOW` OR section starts with `N`
   - **Savannah:** All other sections
   - When using Master Schedule: uses `CAMPUS` column (`SAV` or `NOW`)

3. **Progression Rate Application**
   - **Fall → Spring:** 2 quarter transitions = 0.95² = 0.9025 retention
   - **Winter → Spring:** 1 quarter transition = 0.95 retention
   - Configurable in `forecast_config.json`

4. **Demand Aggregation**
   - Sum progressed enrollments by course and campus
   - Apply campus filtering from sequencing guide ("General" applies to all)

5. **Section Calculation**
   - Sections = ceil(projected_seats / capacity)
   - Default capacity: 20 students/section
   - Can apply buffer % for late adds

**Assumptions:**
- Sequencing guide is accurate and maintained
- Progression rate is consistent across courses
- No major changes in program requirements
- Current Fall/Winter data represents typical cohort behavior

### Prophet + Exponential Smoothing Methodology (Streamlit UI)

**Ensemble Approach:**

1. **Prophet Model**
   - Handles seasonality (quarterly patterns)
   - Captures multi-year trends
   - Robust to missing data
   - Weight: 60% (default)

2. **Exponential Smoothing Model**
   - Captures short-term patterns
   - Adaptive to recent changes
   - Weight: 40% (default)

3. **Ensemble Prediction**
   - Weighted average of both models
   - Provides confidence intervals (lower/upper bounds)
   - More robust than single-model approach

**Data Requirements:**
- Minimum: 4 quarters of historical data per course
- Recommended: 8+ quarters for better accuracy
- Format: year, quarter, course_code, enrollment

## Directory Structure

```
/Users/nathanmadrid/Desktop/Dev/Forecast Tool/
├── README.md                          # Quick start guide (updated for v2.0)
├── QUICKSTART_CHAT.md                 # Chat interface guide (NEW)
├── AGENTS.md                          # Production workflow runbook
├── CLAUDE.md                          # This file
├── PRD_Frontend_Interface.md          # Product requirements for chat UI
├── requirements.txt                   # Python dependencies
├── requirements_chat.txt              # Additional chat UI dependencies (NEW)
├── forecast_config.json               # Production script configuration
│
├── app_chat.py                        # Chat-based UI (NEW - v2.0)
├── app.py                             # Classic form-based UI (original)
├── Forecast_Tool_Launcher.command     # One-click launcher (NEW)
│
├── forecast_tool/                     # Modular package (NEW - v2.0)
│   ├── __init__.py
│   ├── chat/                          # Natural language interface
│   │   ├── __init__.py
│   │   ├── command_parser.py          # Parse user intents from text
│   │   ├── conversation.py            # Manage chat state and history
│   │   └── responses.py               # Format bot responses
│   ├── ui/                            # Streamlit UI components
│   │   ├── __init__.py
│   │   ├── chat_window.py             # Chat interface (left panel)
│   │   └── output_window.py           # Results display (right panel)
│   ├── forecasting/                   # Prediction models
│   │   ├── __init__.py
│   │   ├── prophet_forecast.py        # Prophet time series model
│   │   ├── ets_forecast.py            # Exponential Smoothing model
│   │   └── ensemble.py                # Model combination + section calc
│   ├── data/                          # Data management
│   │   ├── __init__.py
│   │   ├── loaders.py                 # CSV/Excel loading + course mapping
│   │   └── transformers.py            # Quarter/date conversions
│   └── config/                        # Settings
│       ├── __init__.py
│       └── settings.py                # Default configuration values
│
├── forecast_spring26_from_sequence_guides.py  # PRIMARY production script
├── forecast_fall26_from_sequence_guides.py    # Fall forecasting
├── forecast_spring26_from_seat_projection.py
├── forecast_spring26_using_sequence.py
├── calculate_foun_demand.py          # FOUN demand calculator
├── spring_2026_demand_forecast.py
├── spring_2026_forecast.py
├── utils.py                           # Helper functions
│
├── test_parser.py                     # Data parsing tests
├── inspect_data.py                    # Data exploration
├── analyze_ratio.py                   # Ratio analysis
├── check_fall.py                      # Fall data checks
├── compare_summer.py                  # Summer comparison
├── forecast_off_sequence.py           # Off-sequence forecasting
├── manual_forecast.py                 # Manual forecast utilities
│
├── prophet_forecast/                  # Modular CLI forecasting tool (separate)
│   ├── README.md
│   ├── __init__.py
│   ├── cli.py                         # Command-line interface
│   ├── forecaster.py                  # Core forecasting logic
│   ├── data_loader.py                 # Data loading utilities
│   └── config.py                      # Configuration handling
│
├── Data/                              # Enrollment data and outputs (33 files)
│   ├── FAll25.csv                     # Fall 2025 enrollments (57KB)
│   ├── Winter26.csv                   # Winter 2026 enrollments (56KB)
│   ├── Master Schedule of Classes.csv # Complete schedule (9.2MB)
│   ├── FOUN_sequencing_map_by_major.csv  # Sequencing logic (CRITICAL)
│   ├── FOUN_Historical.csv            # Historical FOUN data
│   ├── Spring_2026_FOUN_Forecast_*.csv   # Generated forecasts
│   ├── Summer_2026_FOUN_Forecast.csv
│   └── [other data files...]
│
├── docs/                              # Additional documentation
├── .venv/                             # Python virtual environment
├── .vscode/                           # VS Code settings
├── .obsidian/                         # Obsidian vault config
└── [config files...]
```

## Common Development Tasks

### Update Forecast for New Term

1. **Obtain Latest Enrollment Data**
   - Export from SCAD system with current term enrollments
   - Save as CSV in `Data/` directory

2. **Update Configuration**
   ```bash
   # Edit forecast_config.json
   vim forecast_config.json
   ```
   Update:
   - `fall_term_code` / `winter_term_code` with current term codes
   - `fall_enroll` / `winter_enroll` file paths if file names changed
   - `output` path with new term identifier

3. **Verify Sequencing Guide**
   - Check `Data/FOUN_sequencing_map_by_major.csv` is current
   - Confirm no program requirement changes
   - Update if needed

4. **Run Forecast**
   ```bash
   python3 forecast_spring26_from_sequence_guides.py --config forecast_config.json
   ```

5. **Review Output**
   - Check output CSV for anomalies
   - Compare with previous term forecasts
   - Validate section counts are reasonable

### Add New Forecasting Script

When creating a new forecasting methodology:

1. **Create Script File**
   ```bash
   touch forecast_[term]_[methodology].py
   ```

2. **Standard Structure**
   ```python
   import pandas as pd
   import argparse
   import json

   def load_config(config_path):
       with open(config_path) as f:
           return json.load(f)

   def load_data(config):
       # Load enrollment data
       pass

   def generate_forecast(data, config):
       # Forecasting logic
       pass

   def save_output(forecast, output_path):
       forecast.to_csv(output_path, index=False)

   if __name__ == "__main__":
       parser = argparse.ArgumentParser()
       parser.add_argument('--config', required=True)
       args = parser.parse_args()

       config = load_config(args.config)
       data = load_data(config)
       forecast = generate_forecast(data, config)
       save_output(forecast, config['output'])
   ```

3. **Document in AGENTS.md**
   - Add to workflow section
   - Explain methodology differences
   - Note when to use this approach

### Modify Streamlit UI

**Add New Configuration Parameter:**

1. Edit `app.py`:
   ```python
   # In sidebar section (~line 17)
   new_param = st.sidebar.slider("New Parameter", min, max, default)
   ```

2. Pass to forecasting logic:
   ```python
   # Where forecast is generated
   forecast = generate_forecast(data, new_param=new_param)
   ```

3. Test locally:
   ```bash
   streamlit run app.py
   ```

**Add New Visualization:**

1. After forecast generation in `app.py`:
   ```python
   st.subheader("New Visualization")
   fig = create_chart(forecast_data)
   st.plotly_chart(fig)  # or st.line_chart(), st.bar_chart()
   ```

### Data Quality Checks

**Inspect Data:**
```bash
# Check data structure
python3 inspect_data.py

# Verify column names
python3 inspect_cols.py

# Test data parser
python3 test_parser.py
```

**Common Data Issues:**

1. **Missing enrollment data**
   - Check CSV has all expected courses
   - Verify term codes are correct
   - Confirm file encoding (UTF-8)

2. **Sequencing guide mismatches**
   - Course codes must match exactly (case-sensitive)
   - Campus values: "SAV", "NOW", or "General" only
   - CHOICE courses: semicolon-separated list

3. **Campus detection failures**
   - SCADnow: Room = "OLNOW" or section prefix = "N"
   - Master Schedule: CAMPUS column = "SAV" or "NOW"
   - Check for unexpected room/section naming

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Streamlit Not Found:**
```bash
# Install in virtual environment
pip install streamlit>=1.28.0

# Or use system Python
python3 -m pip install streamlit
```

**Prophet Installation Issues:**
```bash
# Prophet requires compiler tools
# macOS:
xcode-select --install

# Then:
pip install prophet
```

**CSV Encoding Errors:**
```python
# Try different encodings in script
df = pd.read_csv(file, encoding='utf-8')
df = pd.read_csv(file, encoding='latin-1')
df = pd.read_csv(file, encoding='iso-8859-1')
```

**Empty Forecast Output:**
- Check sequencing guide has entries for target term
- Verify term codes match enrollment data
- Confirm campus filtering logic
- Check progression rate isn't too low

**Section Count Seems Wrong:**
- Verify capacity setting (default: 20)
- Check if buffer % should be applied
- Review progression rate (default: 0.95)
- Compare with historical section counts

### Debug Mode

**Enable Verbose Output:**

1. Edit forecasting script, add:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. Add debug prints:
   ```python
   print(f"Loaded {len(df)} enrollment records")
   print(f"Unique courses: {df['course'].nunique()}")
   print(f"Forecasted seats:\n{forecast.head()}")
   ```

3. Run with output:
   ```bash
   python3 forecast_script.py --config forecast_config.json > debug.log 2>&1
   ```

## Performance Baseline

- **Forecast generation:** ~2-5 seconds for typical term
- **Streamlit UI load:** <3 seconds
- **Data processing:** <1 second for 50-100 courses
- **Prophet model training:** 1-2 seconds per course

## Code Standards

**Python:**
- PEP 8 style guide
- 4-space indentation
- Type hints where helpful
- Docstrings for functions

**Data Files:**
- CSV format preferred for version control
- Excel only when necessary (binary files)
- UTF-8 encoding
- Column names: lowercase with underscores

**Git Commits:**
- Conventional Commits format
- Examples: `feat: add summer forecasting`, `fix: campus detection logic`

## Important Notes

### What NOT to Do

- **Don't commit sensitive data** - Enrollment data may contain student info
- **Don't modify sequencing guide** without SCAD approval
- **Don't change progression rate** without data justification
- **Don't delete old forecasts** - Keep for accuracy validation
- **Don't skip data validation** - Bad input = bad forecast

### Data Privacy

- Enrollment data may be considered educational records
- Do not share forecasts publicly without approval
- Keep output files in `Data/` directory (not tracked in git)
- Aggregate data only (no individual student records)

### Git Strategy

**Currently:**
- Recent commit: `d080398 Add files via upload`
- Most files in `Data/` are untracked
- `.gitignore` should exclude sensitive data

**Recommended:**
```gitignore
# Add to .gitignore
Data/*.csv
Data/*.xlsx
!Data/*_template.csv
!Data/FOUN_sequencing_map_by_major.csv  # Keep sequencing guide
.venv/
*.pyc
__pycache__/
.DS_Store
```

## Key Documentation Files

| File | Purpose |
|------|---------|
| [README.md](README.md) | Quick start guide for Streamlit UI |
| [AGENTS.md](AGENTS.md) | Production workflow and runbook |
| [CLAUDE.md](CLAUDE.md) | This file - comprehensive developer guide |
| [Data_Gathering_Plan.md](Data_Gathering_Plan.md) | Data collection strategy |
| [foun_demand_logic.md](foun_demand_logic.md) | FOUN demand calculation logic |
| [prophet_forecast/README.md](prophet_forecast/README.md) | CLI module documentation |

## Next Steps for New Developers

1. **Environment Setup**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Read Documentation**
   - [AGENTS.md](AGENTS.md) for workflow
   - [README.md](README.md) for Streamlit UI
   - This file for architecture

3. **Run Sample Forecast**
   ```bash
   # Interactive UI
   streamlit run app.py

   # Or production script
   python3 forecast_spring26_from_sequence_guides.py --config forecast_config.json
   ```

4. **Explore Data**
   ```bash
   python3 inspect_data.py
   python3 test_parser.py
   ```

5. **Review Latest Output**
   ```bash
   cat Data/Spring_2026_FOUN_Forecast_SAV_SCADnow_From_Sequence_Guides.csv
   ```

## Related Projects

This is a **standalone forecasting tool**, distinct from other enrollment systems that may be planned or in development at SCAD. This tool focuses specifically on:

- FOUN (Foundation) course forecasting
- Section planning (not student scheduling)
- Aggregate demand (not individual student needs)
- Desktop/CLI usage (not web-based multi-user system)

For full-stack enrollment management systems with databases, APIs, and role-based access control, see other SCAD IT projects.

## Version History

### Version 2.0 (January 2026) - Chat Interface Release

**Major Features:**
- **Chat-based UI** (`app_chat.py`) with natural language input
- **Modular architecture** - Forecasting logic extracted into `forecast_tool/` package
- **One-click launcher** for non-technical users
- **Command parser** for intent classification and parameter extraction
- **Conversation management** with session state and context tracking
- **Dual interface support** - Chat UI and Classic UI use same engine

**New Files:**
- `app_chat.py` - Main chat application
- `Forecast_Tool_Launcher.command` - Shell script launcher
- `QUICKSTART_CHAT.md` - Chat interface guide
- `requirements_chat.txt` - Additional dependencies
- `forecast_tool/` package (17 Python modules)

**Architecture Changes:**
- Forecasting logic modularized for reuse
- Streamlit UI components separated from business logic
- Configuration externalized to `forecast_tool/config/settings.py`
- Data loaders support both interfaces

**Benefits:**
- Non-technical users can forecast without training
- Conversational workflow reduces errors
- Same forecasting engine ensures consistency
- Easier to maintain and extend

**Backward Compatibility:**
- Original `app.py` unchanged and fully functional
- All production CLI scripts work as before
- No breaking changes to data files or configurations

### Version 1.0 (December 2025) - Initial Release

**Features:**
- Streamlit form-based UI (`app.py`)
- Prophet + Exponential Smoothing ensemble forecasting
- Sequence-based production CLI scripts
- Historical data integration
- CSV/Excel upload and export

---

**Last Updated:** January 29, 2026
**Repository Purpose:** SCAD FOUN enrollment forecasting and section planning tool
**Primary Contact:** Nathan Madrid
**Python Version:** 3.9+ (3.10+ recommended)
**Main Application:** `app_chat.py` (chat UI) or `app.py` (classic UI)
**Production Script:** `forecast_spring26_from_sequence_guides.py`
**Version:** 2.0.0
