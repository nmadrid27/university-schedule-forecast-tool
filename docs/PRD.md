# Product Requirements Document: SCAD FOUN Enrollment Forecasting Tool

**Version:** 1.0
**Date:** February 2026
**Author:** Nathan Madrid
**Status:** Shipped

---

## 1. Problem Statement

Savannah College of Art and Design (SCAD) offers Foundation (FOUN) courses that serve as prerequisites across all majors. Each quarter, academic planners must determine how many sections of each FOUN course to offer at each campus (Savannah and SCADnow/online). This process is currently manual, relying on institutional knowledge and spreadsheet analysis.

**Pain points:**
- Section planning happens quarterly under time pressure with no standardized methodology
- Planners lack visibility into how prerequisite enrollment flows into FOUN demand
- Over-projecting wastes instructor resources; under-projecting leaves students unable to register
- No systematic way to account for cross-campus differences or student attrition between terms
- Historical enrollment data exists but is not structured for forward-looking analysis

## 2. Product Vision

A self-contained forecasting tool that any SCAD staff member can run on their Mac to predict FOUN section needs for any upcoming quarter, using real enrollment data and SCAD's own major sequencing guides as the primary methodology.

## 3. Target Users

### Primary: Academic Planners / Registrar Staff
- Non-technical Mac users
- Familiar with SCAD's academic calendar and course structure
- Need actionable section counts, not statistical outputs
- Work with CSV exports from Banner (SCAD's SIS)

### Secondary: Department Chairs / Academic Leadership
- Consume forecast results for resource allocation decisions
- May want to adjust parameters (capacity, buffer) for scenario planning

## 4. Goals and Success Metrics

| Goal | Metric | Target |
|------|--------|--------|
| Reduce manual forecasting effort | Time from data export to section recommendation | < 5 minutes (vs. hours) |
| Improve forecast accuracy | Forecast vs. actual enrollment variance | < 15% per course per campus |
| Enable scenario planning | Ability to adjust capacity/buffer and see updated sections | Instant recalculation |
| Zero-install friction | Steps from ZIP to working tool | 2 double-clicks |
| Self-contained operation | External dependencies at runtime | None (fully offline) |

## 5. Functional Requirements

### 5.1 Forecasting Engine

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| F-1 | Forecast FOUN section needs for any SCAD quarter (Fall, Winter, Spring, Summer) | P0 | Done |
| F-2 | Use SCAD major sequencing guides as primary forecasting input | P0 | Done |
| F-3 | Detect and separate Savannah vs. SCADnow campus demand | P0 | Done |
| F-4 | Apply configurable progression rate per term gap | P0 | Done |
| F-5 | Calculate section counts from projected enrollment and capacity | P0 | Done |
| F-6 | Handle "CHOICE" entries (split demand evenly across course options) | P0 | Done |
| F-7 | Fall back to ratio-based forecasting when sequencing data is unavailable | P1 | Done |
| F-8 | Compute historical enrollment ratios for ratio-based fallback | P1 | Done |
| F-9 | Provide 3-model time-series ensemble as alternative methodology | P2 | Done |
| F-10 | Support ensemble weight optimization via cross-validation | P2 | Done |
| F-11 | Run stationarity and seasonality diagnostics on historical data | P2 | Done |
| F-12 | Compare current forecast to previous forecast (change deltas) | P1 | Done |

### 5.2 Web Interface

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| W-1 | Chat-based interaction for requesting forecasts | P0 | Done |
| W-2 | Display forecast results in a data table (course, campus, seats, sections) | P0 | Done |
| W-3 | Show summary metrics (total students, sections, courses forecasted) | P0 | Done |
| W-4 | Download forecast results as CSV | P0 | Done |
| W-5 | Adjust capacity, progression rate, and buffer via sidebar controls | P1 | Done |
| W-6 | Parse natural language commands (e.g., "Forecast Spring 2026") | P1 | Done |
| W-7 | Work in mock/offline mode when backend is unavailable | P1 | Done |
| W-8 | Dark theme UI | P2 | Done |
| W-9 | Conversation history sidebar | P2 | Done |

### 5.3 API

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| A-1 | Health check endpoint | P0 | Done |
| A-2 | Forecast endpoint with real data (not mock) | P0 | Done |
| A-3 | List available and forecastable terms | P0 | Done |
| A-4 | Read/write forecast configuration | P1 | Done |
| A-5 | List data files in Data/ directory | P1 | Done |
| A-6 | Ensemble forecast endpoint with optional weight optimization | P2 | Done |
| A-7 | Diagnostics endpoint (stationarity + seasonality) | P2 | Done |
| A-8 | Natural language chat parsing | P1 | Done |

### 5.4 Delivery and Operations

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| D-1 | One-time installer that sets up all dependencies on macOS | P0 | Done |
| D-2 | Full-stack launcher (backend + frontend) via double-click | P0 | Done |
| D-3 | Clean shutdown script | P0 | Done |
| D-4 | Non-technical user guide | P0 | Done |
| D-5 | Deliverable as a single ZIP file (< 20MB) | P0 | Done |
| D-6 | Idempotent installer (safe to run multiple times) | P1 | Done |
| D-7 | Automatic browser open on launch | P1 | Done |
| D-8 | Health check before declaring backend ready | P1 | Done |
| D-9 | Graceful cleanup on exit (kill both servers) | P1 | Done |

## 6. Non-Functional Requirements

| Category | Requirement | Target |
|----------|-------------|--------|
| **Performance** | Forecast response time for a single term | < 5 seconds |
| **Performance** | Ensemble forecast with 3 models | < 30 seconds |
| **Reliability** | ARIMA model convergence failures | Handled via cascading fallback |
| **Reliability** | Missing data for a term/course | Graceful fallback, not crash |
| **Portability** | Operating system | macOS (Apple Silicon and Intel) |
| **Portability** | Offline operation | Full functionality without internet |
| **Data** | Max Master Schedule size | 9+ MB CSV supported |
| **Security** | Network exposure | localhost only (no external access) |
| **Usability** | Technical knowledge required | None for daily use |

## 7. Architecture

### System Diagram

```
User
 |
 +------ Double-click .command scripts ------+
 |                                           |
 v                                           v
Browser (localhost:3000)              Terminal (background)
 |                                           |
 v                                           v
Next.js Frontend                     FastAPI Backend
(React 19, Tailwind CSS 4)          (localhost:8000)
 |                                           |
 +-------------- HTTP/JSON -----------------+
                     |
                     v
          Python Forecasting Engine
          (forecast_tool/ package)
                     |
          +----------+-----------+
          |          |           |
       Prophet     ETS        ARIMA
          |          |           |
          +----+-----+-----+----+
               |           |
          Ensemble    Diagnostics
               |
               v
          Data Layer
       (CSV files in Data/)
```

### Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | Next.js | 16.1.6 |
| Frontend | React | 19 |
| Frontend | Tailwind CSS | 4 |
| Frontend | TypeScript | 5 |
| Frontend | Radix UI | Latest |
| Backend | FastAPI | 0.109+ |
| Backend | Uvicorn | 0.27+ |
| Backend | Python | 3.11+ |
| Forecasting | Prophet | 1.1.4+ |
| Forecasting | statsmodels | 0.14+ |
| Forecasting | pandas | 2.0+ |
| Forecasting | numpy | 1.24+ |

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `install.command` | One-time dependency installation (Homebrew, Python, Node, venv, npm) |
| `Forecast_Tool_Launcher.command` | Start backend + frontend, health check, open browser, cleanup on exit |
| `stop.command` | Kill processes on ports 3000 and 8000 |
| `api/main.py` | HTTP API routes, request validation, response formatting |
| `api/forecaster.py` | Pure forecasting functions (sequence-based, ratio-based, term resolution) |
| `forecast_tool/forecasting/` | Prophet, ETS, ARIMA models + ensemble logic |
| `forecast_tool/validation/` | Temporal cross-validation |
| `forecast_tool/diagnostics/` | Stationarity and seasonality analysis |
| `forecast_tool/data/` | CSV loading, data transformation |
| `frontend/src/hooks/useChat.ts` | Chat state management, API calls, mock fallback |
| `frontend/src/app/page.tsx` | 3-panel layout orchestration |

## 8. Data Requirements

### Input Data

| File | Format | Source | Required |
|------|--------|--------|----------|
| `FOUN_sequencing_map_by_major.csv` | CSV | Academic Affairs | Yes (primary method) |
| `Master Schedule of Classes.csv` | CSV | Banner SIS export | Yes |
| Term enrollment snapshots (e.g., `FAll25.csv`) | CSV | Banner SIS export | Yes (for active terms) |
| `FOUN_Historical.csv` | CSV | Compiled from Master Schedule | For ensemble/diagnostics |

### Sequencing Map Schema

| Column | Description |
|--------|-------------|
| `campus` | Campus or "GENERAL" for both |
| `fall` | Fall quarter FOUN courses (may include "CHOICE") |
| `winter` | Winter quarter FOUN courses |
| `spring` | Spring quarter FOUN courses |
| `summer` | Summer quarter FOUN courses |

### Enrollment Snapshot Schema (simple format)

| Column | Description |
|--------|-------------|
| `Course` | Course code (e.g., "FOUN 110") |
| `Enrollment` | Number of enrolled students |
| `Section #` | Section identifier (N-prefix = SCADnow) |
| `Room` | Room code (OLNOW = SCADnow) |

### Master Schedule Schema

| Column | Description |
|--------|-------------|
| `TERM` | SCAD term code (YYYYQQ format) |
| `SUBJ` | Subject (e.g., "FOUN") |
| `CRS NUMBER` | Course number (e.g., "110") |
| `ACT ENR` | Actual enrollment |
| `CAMPUS` | Campus code (SAV / NOW) |

### Output Data

| Field | Description |
|-------|-------------|
| `course` | FOUN course code |
| `campus` | Savannah or SCADnow |
| `projected_seats` | Forecasted enrollment |
| `sections` | Sections needed (`ceil(seats / capacity)`) |
| `method` | Forecasting method used |

## 9. Forecasting Methodology

### Method 1: Sequence-Based (Primary)

**When used:** Any quarter where the sequencing map has data for the target quarter's column.

**Algorithm:**
1. Parse `FOUN_sequencing_map_by_major.csv` to build prerequisite-to-target mappings per campus
2. Load current enrollment from feeder terms (the two preceding quarters)
3. Apply progression rate: `enrollment * rate^(term_gap)` where gap = 1 (closer feeder) or 2 (farther feeder)
4. Distribute enrollment across target courses using mapping weights
5. For CHOICE entries, split demand evenly: `weight = 1/N` where N = number of options
6. Sum demand from both feeder terms per course per campus
7. Calculate sections: `ceil(projected_seats / capacity)`

**Accuracy:** High for quarters with comprehensive sequencing data (Fall, Winter, Spring).

### Method 2: Ratio-Based (Fallback)

**When used:** Automatically when sequence-based returns no results (e.g., Summer quarter has no sequencing guide entries).

**Algorithm:**
1. Compute historical `target_enrollment / feeder_enrollment` ratios per course from `FOUN_Historical.csv`
2. Average ratios across available academic years
3. Load the closest feeder quarter's existing forecast CSV
4. Apply: `projected = feeder_seats * historical_ratio`
5. Default ratio (0.12) used when insufficient historical data

**Accuracy:** Moderate; depends on historical pattern stability.

### Method 3: 3-Model Ensemble (Alternative)

**When used:** On-demand via `/api/forecast/ensemble` endpoint. Requires 4+ quarters of historical data per course.

**Models:**
- **Prophet** (40% default weight): Handles trends and seasonality, robust to missing data
- **ETS** (35% default weight): Exponential smoothing for short-term patterns
- **ARIMA** (25% default weight): Autoregressive with cascading fallback: (1,1,1) → (1,1,0) → (0,1,1) → naive mean

**Weight optimization:** Optional grid search at 5% increments over expanding-window temporal cross-validation. Minimizes RMSE (or MAE/MAPE) across folds.

**NaN handling:** If a model fails, its weight is redistributed proportionally to models that produced valid predictions.

## 10. SCAD-Specific Domain Logic

### Term Code Format
```
YYYYQQ where:
  YYYY = academic year
  QQ   = 10 (Fall), 20 (Winter), 30 (Spring), 40 (Summer)

Academic year starts with Fall:
  Fall 2025   = 202610
  Winter 2026 = 202620
  Spring 2026 = 202630
  Summer 2026 = 202640
```

### Quarter Cycle (feeder relationships)
```
Target    Closer Feeder    Farther Feeder
Spring  ← Winter         ← Fall
Summer  ← Spring         ← Winter
Fall    ← Summer         ← Spring
Winter  ← Fall           ← Summer
```

### Campus Detection
- **SCADnow (online):** Room = `OLNOW` OR section number starts with `N`
- **Savannah:** `CAMPUS` column = `SAV` in Master Schedule
- **SCADnow:** `CAMPUS` column = `NOW` in Master Schedule
- **GENERAL** campus in sequencing map: applies to both campuses

### Configuration Defaults

| Parameter | Default | Description |
|-----------|---------|-------------|
| `capacity` | 20 | Students per section |
| `progression_rate` | 0.95 | Per-term retention rate |
| `buffer_percent` | 0.0 | Extra capacity cushion (%) |
| `default_term` | Spring 2026 | Default forecast target |

## 11. API Specification

### Endpoints

| Method | Path | Request Body | Response |
|--------|------|-------------|----------|
| `GET` | `/api/health` | — | `{status, timestamp}` |
| `POST` | `/api/chat` | `{message, context?}` | `{message, parsedCommand}` |
| `POST` | `/api/forecast` | `{term, method?, config?}` | `{results[], summary}` |
| `GET` | `/api/terms` | — | `{available_terms[], forecastable_terms[]}` |
| `GET` | `/api/config` | — | `{capacity, progressionRate, bufferPercent, ...}` |
| `PUT` | `/api/config` | `ConfigModel` | `{success, config}` |
| `GET` | `/api/data/files` | — | `{files[]}` |
| `POST` | `/api/forecast/ensemble` | `{course?, campus?, periods, optimize_weights?, config?}` | `{results[], summary}` |
| `GET` | `/api/diagnostics` | — | `{results, summary}` |

### Forecast Result Schema

```json
{
  "course": "FOUN 110",
  "campus": "Savannah",
  "projectedSeats": 142.5,
  "sections": 8,
  "change": 12.5,
  "changePercent": 9.6
}
```

## 12. UI Specification

### Layout

```
+--------+------------------+------------------------+--------+
|        |                  |                        |        |
|History |   Chat Window    |    Results Panel       | Config |
|Sidebar |     (40%)        |       (60%)            |Sidebar |
|        |                  |                        |        |
|  New   | Message bubbles  | Summary metrics cards  |Capacity|
|  Chat  | with AI/user     | Data table             | Buffer |
|  List  | distinction      | Download button        |  Rate  |
|        |                  | Compare button         |        |
|        | Input box        |                        |        |
|        | + Send button    |                        |        |
+--------+------------------+------------------------+--------+
```

### Chat Commands (parsed via regex)

| Intent | Example Phrases |
|--------|----------------|
| `forecast` | "Forecast Spring 2026", "Predict Fall enrollment", "Show sections" |
| `help` | "Help", "What can you do", "Commands" |
| `settings` | "Settings", "Show config", "Change capacity" |
| `compare` | "Compare methods", "Prophet vs sequence" |
| `upload` | "Upload data", "Import CSV" |

## 13. Constraints and Assumptions

### Constraints
- macOS only (`.command` launcher scripts are macOS-specific)
- Localhost only (no network deployment, no multi-user access)
- Single-user, single-machine operation
- No persistent database (CSV files on disk)
- No authentication or authorization

### Assumptions
- SCAD term code format remains `YYYYQQ`
- Sequencing guides are maintained and updated by Academic Affairs
- Master Schedule CSV export format from Banner is stable
- Section capacity is uniform across all FOUN courses (configurable globally, not per-course)
- Progression rate is uniform across all courses and campuses

## 14. Future Roadmap

| Feature | Priority | Complexity | Description |
|---------|----------|------------|-------------|
| Per-course capacity | Medium | Low | Allow different section sizes per FOUN course |
| Multi-term batch forecast | Medium | Medium | Forecast multiple sequential terms in one run |
| Data upload via UI | Medium | Medium | Upload new CSV files through the web interface instead of manually placing in `Data/` |
| Forecast comparison view | Low | Medium | Side-by-side comparison of two forecast runs |
| Historical accuracy tracking | Low | High | Compare past forecasts to actuals and report accuracy over time |
| Test suite | Low | Medium | Unit and integration tests for forecasting logic |
| CI/CD pipeline | Low | Medium | Automated testing and deployment |
| Windows/Linux support | Low | Low | Replace `.command` scripts with cross-platform launcher |
| Per-course progression rates | Low | Medium | Different attrition rates by course difficulty |
| Retake estimation | Low | High | Model students retaking FOUN courses |
