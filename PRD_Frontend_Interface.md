# Product Requirements Document (PRD)
## SCAD Forecast Tool - Chat-Based Frontend Interface

**Version:** 1.0
**Date:** January 29, 2026
**Author:** Nathan Madrid
**Status:** Draft for Review

---

## 1. Executive Summary

### 1.1 Product Vision
Transform the SCAD FOUN Enrollment Forecasting Tool from a technical CLI/Streamlit application into an accessible, conversational interface that enables non-technical staff to generate enrollment forecasts through natural language interactions.

### 1.2 Problem Statement
The current Forecast Tool requires:
- Python environment setup knowledge
- Understanding of command-line interfaces
- Familiarity with configuration files (forecast_config.json)
- Knowledge of forecasting methodologies
- Manual file path management

This creates barriers for non-technical users (academic advisors, department chairs, enrollment planners) who need forecasting capabilities but lack technical expertise.

### 1.3 Proposed Solution
A chat-based desktop application with:
- **One-click installation** - No manual Python setup required
- **Conversational interface** - Natural language commands instead of CLI
- **Guided workflows** - Step-by-step assistance for complex tasks
- **Visual output** - Charts, tables, and downloadable reports
- **Smart file handling** - Auto-detection and validation of data files

### 1.4 Success Criteria
- Non-technical users can install and launch the app without IT support
- 80% reduction in time-to-first-forecast for new users
- Zero Python knowledge required to generate forecasts
- Same forecasting accuracy as current CLI tools

---

## 2. Target Users & Personas

### 2.1 Primary Persona: Academic Advisor
**Name:** Sarah Chen
**Role:** Academic Advisor, SCAD Foundation Studies
**Technical Skill:** Low (Microsoft Office proficient, no programming)
**Goals:**
- Forecast Spring 2026 FOUN section needs for advising planning
- Compare forecast scenarios (different capacity, progression rates)
- Generate reports for department meetings

**Pain Points:**
- Doesn't know how to use terminal/command line
- Struggles with Python installation and virtual environments
- Needs IT help to update forecast_config.json
- Can't troubleshoot errors in CLI scripts

**User Story:**
> "As an academic advisor, I want to forecast next term's FOUN enrollments by simply asking the system what I need, so I can plan advising resources without learning Python."

### 2.2 Secondary Persona: Department Chair
**Name:** Dr. Michael Rodriguez
**Role:** Chair, Foundation Studies Department
**Technical Skill:** Medium (Excel power user, basic scripting)
**Goals:**
- Weekly enrollment projections during registration period
- What-if analysis (capacity changes, new sections)
- Compare historical vs forecasted trends

**Pain Points:**
- Limited time to learn new tools
- Needs quick answers during meetings
- Wants to validate forecasts with different methods
- Requires professional-looking reports for administration

**User Story:**
> "As a department chair, I want to quickly generate and compare different forecasting scenarios during budget meetings, so I can make data-driven staffing decisions."

### 2.3 Tertiary Persona: Enrollment Planner
**Name:** Jessica Thompson
**Role:** Enrollment Planning Analyst
**Technical Skill:** Medium-High (SQL, Excel, some Python)
**Goals:**
- Multi-term forecasting (Spring, Summer, Fall pipeline)
- Cross-campus comparisons (Savannah vs SCADnow)
- Integration with admissions data

**Pain Points:**
- Existing Streamlit UI lacks chat guidance
- Switching between multiple scripts is inefficient
- Wants to automate recurring forecast workflows
- Needs audit trail of forecast parameters used

**User Story:**
> "As an enrollment planner, I want to automate recurring forecast workflows and access multiple methodologies through a single interface, so I can reduce manual work and increase forecasting consistency."

---

## 3. User Stories & Use Cases

### 3.1 Core User Stories

#### Epic 1: Installation & Setup
- **US-1.1:** As a new user, I want to install the app with a single double-click, so I don't need to configure Python environments manually
- **US-1.2:** As a new user, I want automatic dependency installation, so I don't have to run pip commands
- **US-1.3:** As a user on macOS, I want a native .app bundle I can drag to Applications folder

#### Epic 2: Basic Forecasting
- **US-2.1:** As an advisor, I want to ask "Forecast Spring 2026 enrollments" and get results, without knowing which script to run
- **US-2.2:** As an advisor, I want the system to auto-detect existing data files, so I don't need to know file paths
- **US-2.3:** As an advisor, I want to see forecast results in a table with charts, not raw CSV output
- **US-2.4:** As an advisor, I want to download forecast results as CSV or Excel for reporting

#### Epic 3: Data Upload & Management
- **US-3.1:** As a user, I want to upload new enrollment data by dragging a file into the chat, not editing config files
- **US-3.2:** As a user, I want immediate validation feedback if my uploaded file has errors
- **US-3.3:** As a user, I want to see a preview of uploaded data before running forecasts
- **US-3.4:** As a user, I want the system to remember my most recent data files

#### Epic 4: Guided Workflows
- **US-4.1:** As a new user, I want step-by-step guidance for my first forecast, so I understand the process
- **US-4.2:** As a user, I want suggested next actions after completing a forecast (e.g., "Would you like to compare with last term?")
- **US-4.3:** As a user, I want to ask "How do I..." questions and get contextual help

#### Epic 5: Advanced Features
- **US-5.1:** As a planner, I want to compare Prophet vs Sequence-based forecasting side-by-side
- **US-5.2:** As a chair, I want what-if analysis (e.g., "What if we increase capacity to 25 students?")
- **US-5.3:** As a planner, I want to run forecasts for multiple terms in one conversation
- **US-5.4:** As a user, I want to save and recall custom forecast configurations

#### Epic 6: Error Recovery
- **US-6.1:** As a user, I want clear error messages in plain English, not Python tracebacks
- **US-6.2:** As a user, I want suggested fixes when errors occur (e.g., "Try uploading Fall 2025 enrollment data")
- **US-6.3:** As a user, I want to retry failed operations without restarting the app

### 3.2 Detailed Use Cases

#### Use Case 1: Quick Forecast (Existing Data)
**Actor:** Academic Advisor
**Precondition:** Fall 2025 and Winter 2026 data files exist in Data/ folder
**Trigger:** User asks "Show me Spring 2026 forecast"

**Main Flow:**
1. System detects existing data files (FAll25.csv, Winter26.csv)
2. System displays: "I found Fall 2025 and Winter 2026 enrollment data. Would you like me to forecast Spring 2026 FOUN sections using the sequence-based method?"
3. User confirms: "Yes"
4. System loads data, applies sequencing logic, runs forecast
5. System displays:
   - Results table (course, campus, projected seats, sections)
   - Enrollment trend chart
   - "Forecast complete! 15 FOUN courses, 78 sections recommended"
6. System offers: "Download CSV | Compare Methods | Adjust Parameters"
7. User downloads CSV

**Alternate Flow 1a: Missing Data**
- Step 2: System says "I don't see Winter 2026 data. Would you like to upload it or proceed with Fall data only?"
- User uploads Winter26.csv via file uploader
- Return to Step 4

**Postcondition:** User has downloadable forecast results

---

#### Use Case 2: Upload New Enrollment Data
**Actor:** Enrollment Planner
**Precondition:** User has new enrollment CSV from SCAD system
**Trigger:** User says "I want to upload new enrollment data"

**Main Flow:**
1. System displays file uploader: "Please upload your enrollment CSV or Excel file"
2. User drags file into upload area
3. System validates file:
   - Checks for required columns (course, enrollment, campus/room, etc.)
   - Detects term from filename or data
   - Validates data types and ranges
4. System shows preview:
   - "Detected: Fall 2025 enrollments, 1,247 records, 89 unique courses"
   - Data table preview (first 10 rows)
5. System asks: "Does this look correct?"
6. User confirms: "Yes"
7. System saves file to Data/ folder with timestamp
8. System: "Data uploaded successfully! You can now run forecasts using this data."

**Alternate Flow 2a: Invalid File Format**
- Step 3: System detects missing columns
- System: "This file is missing required columns: 'enrollment'. Please upload a file with these columns: course, enrollment, campus"
- Return to Step 1

**Alternate Flow 2b: Ambiguous Term**
- Step 3: System can't detect term from data
- System: "I couldn't determine which term this data is for. Is this: Fall 2025 | Winter 2026 | Other"
- User selects "Fall 2025"
- Continue to Step 4

**Postcondition:** New enrollment data is validated and ready for forecasting

---

#### Use Case 3: Compare Forecasting Methods
**Actor:** Department Chair
**Precondition:** Historical enrollment data exists (4+ quarters)
**Trigger:** User asks "Compare Prophet and sequence-based forecasting for FOUN 110"

**Main Flow:**
1. System: "I'll compare two methods for FOUN 110:
   - Prophet + Exponential Smoothing (historical trends)
   - Sequence-based (Fall/Winter enrollment progression)

   This will take about 10 seconds. Continue?"
2. User: "Yes"
3. System runs both forecasts in parallel
4. System displays side-by-side comparison:

   | Metric | Prophet | Sequence | Difference |
   |--------|---------|----------|------------|
   | Projected Enrollment | 142 | 156 | +14 (+9.9%) |
   | Recommended Sections | 8 | 8 | 0 |
   | Confidence Interval | 128-156 | N/A | - |

5. System displays dual-axis chart showing both forecasts
6. System explains: "Sequence-based forecast is 9.9% higher because it includes new Winter enrollments. Prophet relies on historical patterns."
7. System offers: "Which method would you like to use for your report?"

**Alternate Flow 3a: Insufficient Historical Data**
- Step 3: System detects only 2 quarters of data
- System: "Prophet requires at least 4 quarters of data. You only have 2 quarters. Would you like to proceed with sequence-based method only?"
- User confirms
- System runs sequence-based forecast only

**Postcondition:** User understands differences between methods and can choose preferred approach

---

#### Use Case 4: What-If Scenario Analysis
**Actor:** Department Chair
**Precondition:** Base forecast exists
**Trigger:** User asks "What if we increase section capacity to 25 students?"

**Main Flow:**
1. System: "Current forecast uses 20 students/section. I'll recalculate with 25 students/section."
2. System re-runs section calculation with new capacity
3. System displays before/after comparison:

   **Impact of Capacity Increase (20 → 25 students/section)**

   | Course | Current Sections | New Sections | Change |
   |--------|------------------|--------------|--------|
   | FOUN 110 SAV | 8 | 6 | -2 (-25%) |
   | FOUN 110 NOW | 1 | 1 | 0 (0%) |
   | FOUN 112 SAV | 6 | 5 | -1 (-17%) |
   | **Total** | **78** | **63** | **-15 (-19%)** |

4. System: "Increasing capacity to 25 would reduce total sections from 78 to 63 (15 fewer sections needed)."
5. System asks: "Would you like to save this as your new configuration or compare another scenario?"

**Alternate Flow 4a: Multiple Parameters**
- User: "What if we increase capacity to 25 AND add 10% buffer?"
- System adjusts both parameters
- Shows compound impact

**Postcondition:** User has data to make capacity decisions

---

## 4. Functional Requirements

### 4.1 Installation & Environment Management

| Req ID | Priority | Requirement |
|--------|----------|-------------|
| FR-1.1 | P0 | System SHALL provide a one-click launcher (macOS .command script or .app bundle) |
| FR-1.2 | P0 | Launcher SHALL auto-create Python virtual environment on first run |
| FR-1.3 | P0 | Launcher SHALL auto-install all dependencies (streamlit, prophet, pandas, etc.) |
| FR-1.4 | P0 | Launcher SHALL open default web browser to Streamlit app automatically |
| FR-1.5 | P1 | System SHALL display installation progress (creating venv, installing packages) |
| FR-1.6 | P1 | Launcher SHALL detect if Python 3.9+ is installed; prompt user if not |
| FR-1.7 | P2 | System SHALL support macOS .app bundle with embedded Python (no external Python required) |

### 4.2 Chat Interface

| Req ID | Priority | Requirement |
|--------|----------|-------------|
| FR-2.1 | P0 | System SHALL provide a chat input field for natural language commands |
| FR-2.2 | P0 | System SHALL display conversation history in chronological order |
| FR-2.3 | P0 | System SHALL respond to basic forecast commands (e.g., "Forecast Spring 2026") |
| FR-2.4 | P0 | System SHALL display typing indicator while processing requests |
| FR-2.5 | P1 | System SHALL support file upload through chat interface (drag-and-drop or button) |
| FR-2.6 | P1 | System SHALL provide suggested prompts/commands for new users |
| FR-2.7 | P1 | System SHALL maintain conversation context across multiple turns |
| FR-2.8 | P2 | System SHALL support conversation history export (save chat log) |
| FR-2.9 | P2 | System SHALL allow clearing conversation and starting fresh |

### 4.3 Natural Language Understanding

| Req ID | Priority | Requirement |
|--------|----------|-------------|
| FR-3.1 | P0 | System SHALL parse forecast commands (e.g., "Forecast Spring 2026", "Show me FOUN 110 enrollments") |
| FR-3.2 | P0 | System SHALL extract course codes from natural language (e.g., "FOUN 110", "foundation courses") |
| FR-3.3 | P0 | System SHALL recognize term identifiers (Spring 2026, Fall 25, etc.) |
| FR-3.4 | P1 | System SHALL recognize forecasting methods (Prophet, sequence-based, demand-based) |
| FR-3.5 | P1 | System SHALL handle ambiguous requests with clarifying questions |
| FR-3.6 | P1 | System SHALL recognize configuration changes (capacity, buffer, progression rate) |
| FR-3.7 | P2 | System SHALL support synonyms (e.g., "predict" = "forecast", "estimate" = "forecast") |

### 4.4 Forecasting Engine Integration

| Req ID | Priority | Requirement |
|--------|----------|-------------|
| FR-4.1 | P0 | System SHALL execute sequence-based forecasting (forecast_spring26_from_sequence_guides.py) |
| FR-4.2 | P0 | System SHALL execute Prophet + Exponential Smoothing forecasting (app.py logic) |
| FR-4.3 | P0 | System SHALL apply default configuration (capacity=20, progression_rate=0.95) |
| FR-4.4 | P1 | System SHALL allow users to override default configuration through chat |
| FR-4.5 | P1 | System SHALL support demand-based forecasting (spring_2026_demand_forecast.py) |
| FR-4.6 | P1 | System SHALL support summer forecasting (forecast_summer26_foun.py) |
| FR-4.7 | P1 | System SHALL run multiple forecasting methods in parallel for comparison |
| FR-4.8 | P2 | System SHALL remember user's preferred forecasting method |

### 4.5 Data Management

| Req ID | Priority | Requirement |
|--------|----------|-------------|
| FR-5.1 | P0 | System SHALL auto-detect existing data files in Data/ folder |
| FR-5.2 | P0 | System SHALL validate uploaded CSV/Excel files for required columns |
| FR-5.3 | P0 | System SHALL display data preview (first 10 rows) before processing |
| FR-5.4 | P0 | System SHALL save uploaded files to Data/ folder with timestamp |
| FR-5.5 | P1 | System SHALL detect term from filename or data content |
| FR-5.6 | P1 | System SHALL validate data types (enrollment = numeric, course = string) |
| FR-5.7 | P1 | System SHALL check for missing data and warn user |
| FR-5.8 | P2 | System SHALL support data file versioning (keep previous uploads) |

### 4.6 Output Display

| Req ID | Priority | Requirement |
|--------|----------|-------------|
| FR-6.1 | P0 | System SHALL display forecast results in a formatted table |
| FR-6.2 | P0 | System SHALL show key metrics (total seats, total sections, courses forecasted) |
| FR-6.3 | P0 | System SHALL provide CSV download button for results |
| FR-6.4 | P1 | System SHALL display enrollment trend charts (historical + forecast) |
| FR-6.5 | P1 | System SHALL show confidence intervals for Prophet forecasts |
| FR-6.6 | P1 | System SHALL support Excel export with formatted tables |
| FR-6.7 | P1 | System SHALL display campus-specific breakdowns (Savannah vs SCADnow) |
| FR-6.8 | P2 | System SHALL support PDF report export with charts and tables |

### 4.7 Workflow Guidance

| Req ID | Priority | Requirement |
|--------|----------|-------------|
| FR-7.1 | P0 | System SHALL provide first-time user tutorial on initial launch |
| FR-7.2 | P1 | System SHALL offer suggested next actions after completing tasks |
| FR-7.3 | P1 | System SHALL provide contextual help when user asks "How do I..." |
| FR-7.4 | P1 | System SHALL detect missing prerequisites (e.g., missing data) and guide user |
| FR-7.5 | P2 | System SHALL remember user's workflow preferences |
| FR-7.6 | P2 | System SHALL provide workflow templates (e.g., "Standard Spring Forecast") |

### 4.8 Error Handling

| Req ID | Priority | Requirement |
|--------|----------|-------------|
| FR-8.1 | P0 | System SHALL display user-friendly error messages (no Python tracebacks) |
| FR-8.2 | P0 | System SHALL suggest corrective actions for common errors |
| FR-8.3 | P1 | System SHALL validate inputs before executing forecasts |
| FR-8.4 | P1 | System SHALL handle file upload errors gracefully (wrong format, corrupt file) |
| FR-8.5 | P1 | System SHALL allow retrying failed operations |
| FR-8.6 | P2 | System SHALL log errors for debugging (hidden from user) |

---

## 5. Non-Functional Requirements

### 5.1 Performance

| Req ID | Priority | Requirement |
|--------|----------|-------------|
| NFR-1.1 | P0 | App launch (with existing venv) SHALL complete in ≤5 seconds |
| NFR-1.2 | P0 | File upload validation SHALL complete in ≤2 seconds for typical CSV (50-100 courses) |
| NFR-1.3 | P0 | Sequence-based forecast SHALL complete in ≤10 seconds for typical term |
| NFR-1.4 | P1 | Prophet forecast SHALL complete in ≤30 seconds for all courses |
| NFR-1.5 | P1 | Chat response latency SHALL be ≤1 second for text responses |
| NFR-1.6 | P2 | System SHALL support concurrent forecasts without blocking UI |

### 5.2 Usability

| Req ID | Priority | Requirement |
|--------|----------|-------------|
| NFR-2.1 | P0 | Non-technical users SHALL be able to install and launch without IT support |
| NFR-2.2 | P0 | Users SHALL generate first forecast within 5 minutes of installation |
| NFR-2.3 | P1 | Chat interface SHALL use plain language (no technical jargon) |
| NFR-2.4 | P1 | Error messages SHALL be actionable (tell user what to do next) |
| NFR-2.5 | P2 | Interface SHALL support keyboard shortcuts for common actions |

### 5.3 Reliability

| Req ID | Priority | Requirement |
|--------|----------|-------------|
| NFR-3.1 | P0 | System SHALL handle invalid user inputs without crashing |
| NFR-3.2 | P0 | Forecasting errors SHALL not require app restart |
| NFR-3.3 | P1 | System SHALL preserve conversation history if app crashes |
| NFR-3.4 | P1 | Data uploads SHALL be validated before processing |
| NFR-3.5 | P2 | System SHALL auto-save user preferences |

### 5.4 Compatibility

| Req ID | Priority | Requirement |
|--------|----------|-------------|
| NFR-4.1 | P0 | System SHALL run on macOS 11+ (Big Sur and later) |
| NFR-4.2 | P1 | System SHALL work with Python 3.9, 3.10, 3.11, 3.12 |
| NFR-4.3 | P2 | System SHALL support Windows 10/11 (future phase) |
| NFR-4.4 | P2 | Launcher script SHALL work with system Python and Homebrew Python |

### 5.5 Maintainability

| Req ID | Priority | Requirement |
|--------|----------|-------------|
| NFR-5.1 | P0 | Codebase SHALL reuse existing forecasting logic (minimal refactoring) |
| NFR-5.2 | P1 | Chat interface SHALL be separable from forecasting engine |
| NFR-5.3 | P1 | Configuration SHALL be centralized (not scattered across files) |
| NFR-5.4 | P2 | Code SHALL follow PEP 8 style guide |

---

## 6. User Interface Requirements

### 6.1 Layout

**Two-Column Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  SCAD Forecast Tool                              [?][×] │
├──────────────────────┬──────────────────────────────────┤
│  CHAT WINDOW (40%)   │  OUTPUT WINDOW (60%)             │
│                      │                                  │
│  ┌────────────────┐  │  ┌────────────────────────────┐ │
│  │ Conversation   │  │  │ Forecast Results           │ │
│  │ History        │  │  │                            │ │
│  │                │  │  │ [Table]                    │ │
│  │ System: Welcome│  │  │                            │ │
│  │ User: Forecast │  │  │ [Chart]                    │ │
│  │ System: ...    │  │  │                            │ │
│  │                │  │  │ [Download CSV]             │ │
│  └────────────────┘  │  └────────────────────────────┘ │
│                      │                                  │
│  ┌────────────────┐  │                                  │
│  │ Type message.. │  │                                  │
│  │ [📎][Send]     │  │                                  │
│  └────────────────┘  │                                  │
│                      │                                  │
│  Suggestions:        │                                  │
│  • Forecast Spring   │                                  │
│  • Upload data       │                                  │
│  • Compare methods   │                                  │
└──────────────────────┴──────────────────────────────────┘
```

### 6.2 Chat Window Components

#### 6.2.1 Conversation Display
- Messages displayed in chronological order (newest at bottom)
- User messages: right-aligned, blue background
- System messages: left-aligned, gray background
- Timestamps on hover
- Auto-scroll to latest message
- Scrollable history (last 100 messages visible)

#### 6.2.2 Input Area
- Text input field (multi-line support)
- Send button (keyboard shortcut: Enter)
- File attachment button (📎) for uploads
- Character count (optional)
- Placeholder text: "Ask me to forecast enrollments..."

#### 6.2.3 Suggested Prompts
- 3-4 context-aware suggestions below input
- Examples:
  - "Forecast Spring 2026"
  - "Upload enrollment data"
  - "Compare forecasting methods"
  - "Show me FOUN 110 trends"
- Updates based on current context

### 6.3 Output Window Components

#### 6.3.1 Results Display
- Tabbed interface:
  - **Table**: Forecast results in sortable table
  - **Charts**: Visual trends
  - **Summary**: Key metrics and insights
  - **Config**: Parameters used for forecast

#### 6.3.2 Table View
- Sortable columns (click header to sort)
- Columns: Course | Campus | Projected Seats | Sections | Change vs Last Term
- Pagination if > 50 rows
- Search/filter functionality
- Export button (CSV, Excel)

#### 6.3.3 Chart View
- Line chart: Historical + Forecasted enrollment trends
- Bar chart: Sections by course
- Comparison chart: Multiple methods side-by-side
- Interactive tooltips
- Zoom/pan controls
- Export as PNG

#### 6.3.4 Summary Panel
- Key metrics card:
  - Total Projected Enrollment: 1,456 students
  - Total Sections: 78 sections
  - Courses Forecasted: 15 courses
  - Forecasting Method: Sequence-based
  - Last Updated: Jan 29, 2026 2:45 PM

### 6.4 Visual Design

#### 6.4.1 Color Palette
- Primary: SCAD Gold (#FFCB05)
- Secondary: SCAD Black (#000000)
- Background: Light Gray (#F5F5F5)
- Text: Dark Gray (#333333)
- Success: Green (#28A745)
- Warning: Orange (#FFC107)
- Error: Red (#DC3545)

#### 6.4.2 Typography
- Headers: Sans-serif (Helvetica, Arial)
- Body: Sans-serif (Helvetica, Arial)
- Code/Data: Monospace (Courier, Monaco)
- Font sizes:
  - H1: 24px
  - H2: 20px
  - Body: 14px
  - Small: 12px

#### 6.4.3 Icons
- Material Icons or Font Awesome
- Consistent icon usage:
  - 📊 Forecast results
  - 📁 File upload
  - ⚙️ Settings
  - ❓ Help
  - ⬇️ Download

### 6.5 Responsive Behavior
- Minimum window size: 1024x768
- Column widths adjustable (drag divider)
- Chat window collapsible for full-screen output view
- Tables scroll horizontally if needed

---

## 7. Technical Requirements

### 7.1 Technology Stack

**Frontend Framework:**
- Streamlit 1.28+ (existing, proven)
- st.chat_message, st.chat_input for chat UI

**Backend:**
- Python 3.9+
- Existing forecasting scripts (minimal refactoring)

**Dependencies:**
- prophet>=1.1.4 (time series forecasting)
- statsmodels>=0.14.0 (exponential smoothing)
- pandas>=2.0.0 (data processing)
- numpy>=1.24.0 (numerical operations)
- openpyxl>=3.1.0 (Excel support)
- plotly>=5.18.0 (interactive charts)

**Optional:**
- anthropic>=0.18.0 (Claude API for NL parsing)

**Installation/Packaging:**
- py2app (macOS .app bundle) OR
- Shell script launcher with venv management

### 7.2 Architecture

**Modular Structure:**
```
forecast_tool/
├── chat/
│   ├── command_parser.py      # NL → structured commands
│   ├── conversation.py         # Chat state management
│   └── responses.py            # Response formatting
├── ui/
│   ├── chat_window.py          # Left panel
│   └── output_window.py        # Right panel
├── forecasting/
│   ├── prophet_forecast.py     # Prophet model
│   ├── ets_forecast.py         # Exponential smoothing
│   ├── sequence_forecast.py    # Sequence-based
│   └── ensemble.py             # Model combination
├── data/
│   ├── loaders.py              # CSV/Excel loading
│   ├── validators.py           # Data validation
│   └── transformers.py         # Data transformation
└── config/
    └── settings.py             # Configuration management
```

### 7.3 Data Flow

```
User Input (Chat)
    ↓
Command Parser (NL → Intent + Entities)
    ↓
Conversation Manager (Context + Validation)
    ↓
Forecasting Orchestrator (Execute)
    ↓
Results Formatter (Tables + Charts)
    ↓
Output Display (UI)
```

### 7.4 State Management

**Streamlit Session State:**
- `st.session_state.messages` - Chat history
- `st.session_state.forecast_config` - Current configuration
- `st.session_state.current_data` - Uploaded data
- `st.session_state.latest_forecast` - Most recent results

### 7.5 Configuration

**Default Configuration:**
```python
{
    "capacity": 20,              # Students per section
    "progression_rate": 0.95,    # Term-to-term retention
    "buffer_percent": 10,        # Extra capacity %
    "quarters_to_forecast": 2,   # Forecast horizon
    "prophet_weight": 0.6,       # Ensemble weighting
    "growth_pct": 0              # Target growth %
}
```

---

## 8. Success Metrics

### 8.1 Adoption Metrics
- **Target:** 80% of FOUN advisors using tool within 2 months
- **Measure:** Unique users per week
- **Baseline:** 0 (new tool)

### 8.2 Usability Metrics
- **Time-to-First-Forecast:** ≤5 minutes for new users
- **Measure:** Time from launch to first forecast download
- **Target:** 80% of users complete first forecast in ≤5 minutes

### 8.3 Efficiency Metrics
- **Forecast Generation Time:** Reduce from 15 minutes (CLI) to ≤2 minutes (chat)
- **Measure:** Average time to generate standard Spring forecast
- **Target:** 85% reduction in time

### 8.4 Error Metrics
- **Installation Success Rate:** ≥95%
- **Measure:** Successful app launches / total launch attempts
- **Target:** ≥95% success rate on first launch

### 8.5 Satisfaction Metrics
- **Net Promoter Score (NPS):** ≥50
- **Measure:** User survey after 1 month of use
- **Target:** ≥50 NPS (world-class product)

### 8.6 Quality Metrics
- **Forecasting Accuracy:** Same as current CLI tools (±5%)
- **Measure:** Forecast vs actual enrollment (next term)
- **Target:** ≤5% variance from CLI method

---

## 9. Assumptions & Dependencies

### 9.1 Assumptions
- Users have macOS 11+ (initial release)
- Users have internet access during installation (for pip)
- Users can install software (admin rights not required)
- SCAD enrollment data format remains stable
- Sequencing guide (FOUN_sequencing_map_by_major.csv) is maintained
- Python 3.9+ is available (system or Homebrew)

### 9.2 Dependencies
- Existing forecasting scripts continue to work
- Streamlit maintains chat components in future versions
- Prophet library compatibility with macOS
- Access to SCAD enrollment data exports
- No breaking changes to data file formats

### 9.3 Risks
- **Risk:** Prophet installation fails on some macOS versions
  - **Mitigation:** Bundle pre-compiled Prophet wheels
- **Risk:** Users don't have Python installed
  - **Mitigation:** Provide .app bundle with embedded Python (Phase 2)
- **Risk:** Natural language parsing is inaccurate
  - **Mitigation:** Start with keyword-based parsing, enhance with Claude API later
- **Risk:** Large enrollment datasets cause performance issues
  - **Mitigation:** Implement caching (@st.cache_data) and pagination

---

## 10. Out of Scope

### 10.1 Explicitly Excluded (This Release)
- ❌ Multi-user collaboration (shared forecasts)
- ❌ Cloud-based storage (all data local)
- ❌ Role-based access control
- ❌ Automated email reports
- ❌ Integration with SCAD Banner system
- ❌ Mobile app (iOS/Android)
- ❌ Real-time enrollment tracking
- ❌ Student-level forecasting (only aggregate)
- ❌ Windows/Linux support (macOS only initially)
- ❌ API for external systems

### 10.2 Future Phases
- **Phase 2:** Windows/Linux support
- **Phase 3:** Cloud sync and collaboration
- **Phase 4:** API and Banner integration
- **Phase 5:** Automated scheduling and notifications

---

## 11. Release Plan

### 11.1 Phase 1: MVP (Weeks 1-3)
**Scope:**
- One-click shell script launcher
- Basic chat interface (keyword-based parsing)
- Sequence-based forecasting (primary method)
- File upload and validation
- Table and basic chart output
- CSV download

**Success Criteria:**
- Users can install and run first forecast without help
- Sequence-based forecasting works with chat commands
- Data upload and validation functional

### 11.2 Phase 2: Enhanced Features (Weeks 4-5)
**Scope:**
- Prophet + ETS forecasting integration
- Method comparison
- What-if scenario analysis
- Enhanced charts (Plotly)
- Guided workflows and suggestions
- macOS .app bundle (optional)

**Success Criteria:**
- All forecasting methods accessible via chat
- Comparison features work correctly
- Professional-looking charts

### 11.3 Phase 3: Polish (Week 6)
**Scope:**
- User documentation and video tutorials
- Error message improvements
- Performance optimization
- Beta testing with 5-10 users
- Bug fixes

**Success Criteria:**
- Documentation complete
- Performance targets met
- Beta users provide positive feedback

### 11.4 Phase 4: General Release (Week 7+)
**Scope:**
- Release to all FOUN advisors and planners
- Training sessions
- Monitoring and support
- Iterative improvements based on feedback

---

## 12. Acceptance Criteria

### 12.1 Installation
- ✅ User can double-click launcher and app opens without errors
- ✅ First-time installation completes in ≤2 minutes
- ✅ No manual Python setup required

### 12.2 Core Forecasting
- ✅ User can ask "Forecast Spring 2026" and receive results
- ✅ Results match existing CLI tool output (±1% variance)
- ✅ Forecast completes in ≤10 seconds

### 12.3 Data Upload
- ✅ User can upload CSV and see validation feedback
- ✅ Invalid files show clear error messages
- ✅ Data preview displays correctly

### 12.4 Output Quality
- ✅ Results table is sortable and readable
- ✅ Charts are interactive and professional
- ✅ CSV download contains correct data

### 12.5 Usability
- ✅ Non-technical user completes first forecast in ≤5 minutes (observed)
- ✅ User can recover from errors without restarting app
- ✅ Help and suggestions are contextually relevant

---

## 13. Open Questions

1. **Claude API Integration:**
   - Should we use Claude API for NL parsing or stick with keyword-based?
   - Budget: ~$0.01 per forecast with Claude Haiku
   - Decision: Start with keywords, add Claude API as optional enhancement

2. **Data Privacy:**
   - Can enrollment data be cached locally?
   - Are there FERPA concerns with local storage?
   - Decision: All data stays local (user's machine), no cloud upload

3. **Update Mechanism:**
   - How will users update to new versions?
   - Decision: Manual download initially, auto-update in Phase 2

4. **Cross-Platform Priority:**
   - Should Windows support be in Phase 1 or Phase 2?
   - Decision: macOS only for Phase 1 (primary user base)

5. **Forecasting Method Priority:**
   - Which methods are most important for MVP?
   - Decision: Sequence-based (P0), Prophet (P1), Others (P2)

---

## 14. Appendix

### 14.1 Sample Conversation Flow

```
System: Welcome to SCAD Forecast Tool! I can help you forecast FOUN
        course enrollments for Spring and Summer 2026.

        What would you like to do?
        • Forecast Spring 2026 enrollments
        • Upload new enrollment data
        • Learn about forecasting methods

User:   Forecast Spring 2026

System: I'll forecast Spring 2026 FOUN enrollments. Let me check what
        data I have...

        ✓ Found: Fall 2025 enrollments (FAll25.csv)
        ✓ Found: Winter 2026 enrollments (Winter26.csv)
        ✓ Found: Sequencing guide (FOUN_sequencing_map_by_major.csv)

        I'll use the sequence-based method to forecast how Fall and Winter
        students will progress into Spring FOUN courses.

        [Processing... 3 seconds]

        ✅ Forecast complete!

[Output Window displays:]

        Spring 2026 FOUN Forecast
        Total Projected Enrollment: 1,456 students
        Total Sections Recommended: 78 sections
        Courses Forecasted: 15 courses

        [Table showing course-by-course breakdown]
        [Chart showing enrollment trends]

        [Download CSV] button

System: Your forecast is ready! Key findings:
        • FOUN 110 SAV needs 8 sections (145 students)
        • FOUN 110 NOW needs 1 section (12 students)
        • Total capacity: 1,560 seats (104 seat buffer)

        Would you like to:
        • Download the full forecast as CSV
        • Compare with another forecasting method
        • Adjust parameters (capacity, buffer, etc.)

User:   What if we increase capacity to 25?

System: I'll recalculate sections with 25 students per section instead of 20.

        [Processing... 1 second]

        Impact of Capacity Increase:
        • Total sections: 63 (was 78) → 15 fewer sections needed
        • Section reduction: -19%
        • Most affected: FOUN 110 SAV (8 → 6 sections)

        [Updated table in Output Window]

        This would save 15 sections but increase average class size from
        18.7 to 23.1 students per section.

        Would you like to save this as your new configuration?

User:   Yes, download CSV

System: ✅ Downloaded: Spring_2026_Forecast_cap25_20260129.csv

        Anything else I can help with?
```

### 14.2 Error Handling Examples

**Example 1: Missing Data**
```
User:   Forecast Spring 2026

System: I need enrollment data to create a forecast. I don't see Fall 2025
        or Winter 2026 data in your Data folder.

        Would you like to:
        • Upload Fall 2025 enrollment file
        • Upload Winter 2026 enrollment file
        • Use historical data instead (Prophet method)
```

**Example 2: Invalid File**
```
User:   [uploads corrupted CSV]

System: ⚠️ I couldn't read this file. It appears to be corrupted or in an
        unsupported format.

        Please upload a file in one of these formats:
        • CSV (.csv)
        • Excel (.xlsx or .xls)

        Your file should have these columns:
        • course (e.g., "FOUN 110")
        • enrollment (number of students)
        • campus or room (to detect Savannah vs SCADnow)
```

**Example 3: Ambiguous Request**
```
User:   Show me forecast

System: I'd be happy to show you a forecast! Which term would you like to
        forecast?

        • Spring 2026
        • Summer 2026
        • Custom term
```

### 14.3 Glossary

- **FOUN Courses**: Foundation courses (FOUN 110-199) required for SCAD students
- **Sequence-Based Forecasting**: Method using Fall/Winter enrollments + sequencing guide to project Spring demand
- **Prophet**: Facebook's time series forecasting library
- **Exponential Smoothing (ETS)**: Statistical forecasting method for short-term patterns
- **Ensemble**: Weighted combination of multiple forecasting models
- **Progression Rate**: Percent of students who continue from one term to the next (default: 95%)
- **Section**: Class section with defined capacity (default: 20 students)
- **Capacity Buffer**: Extra seats per section for late adds (default: 10%)
- **SCADnow**: SCAD's online campus (vs. Savannah physical campus)
- **Sequencing Guide**: CSV mapping prerequisite courses to Spring FOUN courses by major

---

**Document Status:** Draft for Review
**Next Steps:** Review with stakeholders, finalize requirements, begin Phase 1 development
**Approval Required:** Nathan Madrid, SCAD Foundation Studies Department

