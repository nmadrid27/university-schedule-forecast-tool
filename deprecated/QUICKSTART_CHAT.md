# Quick Start Guide - Chat Interface

## One-Click Launch (macOS)

**For Non-Technical Users:**

1. **Double-click** `Forecast_Tool_Launcher.command`
2. The app will:
   - Check Python installation
   - Create virtual environment (first time only)
   - Install dependencies (first time only)
   - Launch Streamlit in your browser
3. Start chatting with the forecasting tool!

## What to Expect

### First Launch
- Takes 2-5 minutes to set up environment
- Installs Python packages automatically
- Opens browser at http://localhost:8501

### Subsequent Launches
- Opens in ~5 seconds
- No installation needed

## Using the Chat Interface

### Example Conversations

**Basic Forecast:**
```
You: Forecast Spring 2026
Bot: I'll generate a forecast. Please upload your enrollment data first.

[Upload CSV file]

You: Forecast Spring 2026 for all courses
Bot: I'll forecast all available courses.
[Generates forecast and displays results]
```

**Configure Settings:**
```
You: Set capacity to 25 students
Bot: Setting section capacity to 25 students.

You: Increase buffer to 15%
Bot: Setting capacity buffer to 15%.
```

**Compare Methods:**
```
You: Compare Prophet vs ETS forecasting
Bot: I'll compare these forecasting methods: prophet, ets.
[Shows side-by-side comparison]
```

**Download Results:**
```
You: Download the forecast
Bot: You can download the forecast results as a CSV file using
     the download button below the results table.
```

## Interface Layout

```
┌──────────────────┬────────────────────────────────┐
│  💬 Chat         │  📊 Results & Data             │
│                  │                                │
│  [Chat history]  │  📁 Upload Enrollment Data     │
│  [Chat input]    │  ⚙️  Forecast Settings         │
│                  │  📈 Forecast Results           │
│                  │  📥 Download CSV               │
└──────────────────┴────────────────────────────────┘
```

**Left Panel (Chat):**
- Natural language input
- Conversation history
- Suggested commands

**Right Panel (Results):**
- File upload
- Configuration settings
- Forecast tables
- Interactive charts
- Download buttons

## Data Format

Your CSV or Excel file should have these columns:

| Column | Required | Example |
|--------|----------|---------|
| Term | Yes | "Fall 2025", "Spring 2026" |
| Course | Yes | "FOUN 110", "FOUN 112" |
| Enrollment | Yes | 75, 82, 68 |
| Waitlist | Optional | 5, 0, 2 |

**Sample CSV:**
```csv
Term,Course,Enrollment,Waitlist
Fall 2023,FOUN 110,75,5
Winter 2024,FOUN 110,68,2
Spring 2024,FOUN 110,72,0
```

## Troubleshooting

### "Python 3 required" Error
- Install Python 3.9+ from https://www.python.org/downloads/
- Restart your computer
- Try launching again

### Browser Doesn't Open
- Manually open: http://localhost:8501
- Check if another Streamlit app is running (close it first)

### "Module not found" Error
- Delete the `.venv` folder
- Re-run `Forecast_Tool_Launcher.command`
- This will recreate the environment

### Forecast Generation Fails
- **Check data:** Upload must have required columns
- **Minimum data:** Need at least 2 quarters per course
- **Valid terms:** Use format "Season YYYY" (e.g., "Spring 2026")

## Configuration Options

Available in the **right sidebar**:

| Setting | Default | Description |
|---------|---------|-------------|
| Students per Section | 20 | Section capacity |
| Capacity Buffer (%) | 10 | Extra capacity for late adds |
| Quarters to Forecast | 2 | Number of future quarters |
| Prophet Weight | 0.6 | Model weighting (0.0-1.0) |
| Include Waitlist | Off | Add waitlist to demand |
| Target Growth % | 0 | Adjust forecast by % |

## Natural Language Examples

**Forecasting:**
- "Forecast Spring 2026"
- "Predict enrollment for FOUN 110"
- "Show me forecasts for all courses"
- "Generate forecast for next term"

**Data Management:**
- "Upload new data"
- "Load historical data"
- "Include data from Data folder"

**Configuration:**
- "Set capacity to 25"
- "Change buffer to 15%"
- "Forecast 4 quarters ahead"
- "Apply 5% growth"

**Analysis:**
- "Compare Prophet and Sequence methods"
- "Show me the difference between models"
- "Which method is more accurate?"

**Help:**
- "Help"
- "What can you do?"
- "Show me available commands"

## Tips for Best Results

1. **Upload Quality Data:**
   - At least 4-8 quarters of history
   - Consistent course codes
   - Clean enrollment numbers

2. **Adjust Settings First:**
   - Set capacity before forecasting
   - Consider buffer for high-demand courses
   - Use growth % for expansion planning

3. **Review Results:**
   - Check forecast table for anomalies
   - Compare lower/upper bounds
   - Validate section counts

4. **Download Results:**
   - Save CSV for record keeping
   - Compare with previous forecasts
   - Share with stakeholders

## Advanced Usage

### Include Historical Data
Enable "Include Historical Data" checkbox to merge:
- Uploaded files
- Historical data from `Data/FOUN_Historical.csv`
- Improves forecast accuracy

### Summer Forecasting
The tool automatically:
- Calculates Summer/Spring ratios
- Applies ratio-based adjustments
- Accounts for seasonal patterns

### Multi-File Upload
Upload multiple files to combine:
- Different terms
- Different data sources
- Incremental updates

## Getting Help

**In the App:**
- Ask "help" in the chat
- Click "Show Help" button

**Documentation:**
- README.md - Original Streamlit UI
- AGENTS.md - Production workflow
- CLAUDE.md - Developer guide
- PRD_Frontend_Interface.md - Product requirements

**Common Issues:**
- Clear chat history if confused
- Re-upload data if forecast fails
- Check sidebar settings
- Restart app if unresponsive

## Keyboard Shortcuts

- **Enter** - Send message
- **Shift+Enter** - New line in chat
- **⌘+R / Ctrl+R** - Reload page
- **⌘+W / Ctrl+W** - Close tab

## What's Next?

After generating a forecast:

1. **Review Results** - Check forecast accuracy
2. **Adjust Settings** - Fine-tune parameters
3. **Download CSV** - Save for records
4. **Share Results** - Export to stakeholders
5. **Plan Sections** - Use section recommendations

## Comparison: Chat UI vs Original UI

| Feature | Original UI | Chat UI |
|---------|-------------|---------|
| Input Method | Forms/Buttons | Natural Language |
| Learning Curve | Moderate | Minimal |
| Flexibility | Fixed workflow | Conversational |
| Speed | Click-heavy | Type and go |
| Guidance | Tooltips | Contextual help |

Both interfaces use the **same forecasting engine** and produce **identical results**.

---

**Version:** 2.0.0
**Last Updated:** January 2026
**Support:** See CLAUDE.md for developer contact
