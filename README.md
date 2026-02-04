# SCAD FOUN Enrollment Forecasting Tool

Predicts future course enrollment using Prophet + Exponential Smoothing ensemble modeling, then calculates required section counts.

## 🚀 Quick Start

### Option 1: Chat Interface (Recommended for Non-Technical Users)

**One-Click Launch (macOS):**
```bash
# Simply double-click:
Forecast_Tool_Launcher.command
```

The launcher will automatically:
- Check Python installation
- Create virtual environment
- Install dependencies
- Launch the chat interface in your browser

**Manual Launch:**
```bash
# Install dependencies
pip install -r requirements.txt

# Run the chat interface
streamlit run app_chat.py
```

See [QUICKSTART_CHAT.md](QUICKSTART_CHAT.md) for detailed instructions.

### Option 2: Original UI (Classic Interface)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the original app
streamlit run app.py
```

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

### Chat Interface (New in v2.0)
- **Natural Language Input**: Ask questions in plain English
- **Conversational Workflow**: Guided forecasting experience
- **Context-Aware**: Remembers uploaded data and settings
- **Smart Suggestions**: Contextual help and command suggestions
- **One-Click Installation**: No technical setup required

### Forecasting Engine
- **Dual-model forecasting**: Prophet (seasonality/trends) + Exponential Smoothing (short-term patterns)
- **Ensemble predictions**: Weighted combination of both models
- **Confidence intervals**: Lower/upper bounds for planning scenarios
- **Section calculator**: Converts forecasts to section counts with configurable capacity and buffer
- **Batch processing**: Forecast multiple courses simultaneously
- **Export**: Download results as CSV

### Both Interfaces Available
- **Chat UI** (`app_chat.py`): Natural language, beginner-friendly
- **Classic UI** (`app.py`): Traditional form-based interface

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

## 🏗️ Architecture (v2.0)

### Modular Package Structure

```
forecast_tool/
├── chat/              # Natural language processing
│   ├── command_parser.py    # Parse user intent
│   ├── conversation.py      # State management
│   └── responses.py         # Response formatting
├── ui/                # Streamlit components
│   ├── chat_window.py       # Chat interface
│   └── output_window.py     # Results display
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

### Application Files

- `app_chat.py` - Chat-based UI (new)
- `app.py` - Classic form-based UI (original)
- `Forecast_Tool_Launcher.command` - One-click launcher
- `forecast_spring26_from_sequence_guides.py` - Production CLI script

## 📚 Documentation

- **[QUICKSTART_CHAT.md](QUICKSTART_CHAT.md)** - Chat interface guide
- **[AGENTS.md](AGENTS.md)** - Production workflow
- **[CLAUDE.md](CLAUDE.md)** - Developer documentation
- **[PRD_Frontend_Interface.md](PRD_Frontend_Interface.md)** - Product requirements

## 🆚 Interface Comparison

| Feature | Chat UI | Classic UI |
|---------|---------|------------|
| **Launch** | One-click | Manual setup |
| **Input** | Natural language | Forms/buttons |
| **Learning Curve** | Minimal | Moderate |
| **Guidance** | Conversational | Tooltips |
| **Best For** | Non-technical users | Power users |

**Both interfaces use the same forecasting engine and produce identical results.**

## 🤖 Example Chat Interactions

```
You: Forecast Spring 2026
Bot: I'll generate a forecast. Please upload your enrollment data first.

You: [uploads CSV]
Bot: Successfully loaded enrollment_data.csv!
     - 150 enrollment records
     - 12 unique courses

You: Forecast all courses for Spring 2026
Bot: Forecast complete for 12 courses in Spring 2026.
     Results are displayed on the right.

You: Set capacity to 25 students
Bot: Setting section capacity to 25 students.

You: Download the results
Bot: You can download the forecast results using the CSV button.
```

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
