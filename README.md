# SCAD FOUN Enrollment Forecasting Tool

Predicts Foundation course enrollment and calculates section needs for upcoming terms. Default method: Auto (same-season historical when enough post-rollout history exists, with a sequence-map fallback for first-time seasons). Alternatives: explicit sequence-map forecasting and a 3-model ensemble (OLS + ETS + ARIMA).

## Desktop App (recommended)

The scheduling admin installs a double-click app: a `.dmg` on macOS, or a `.exe` installer on Windows. No Homebrew, Python, or Node required.

The app runs fully offline. Your data stays on the machine in an app-data folder:

- macOS: `~/Library/Application Support/SCAD Forecast Tool/`
- Windows: `%APPDATA%\SCAD Forecast Tool\`

To load data, click the in-app **Import Master Schedule…** button and pick the PZSMSCP export. In **Auto** mode, the app uses prior same-season history when available (for example, Fall 2025 to forecast Fall 2026) and falls back to the sequence map when a season has no post-rollout history yet (for example, Spring 2026 needs Fall 2025 and Winter 2026 feeders). Optionally use **Import Admits (optional)…** to load the PZSAAPF accepted-applicants report for new-student demand. The app copies files into the data folder for you.

The first launch shows a one-time security prompt because v1 is unsigned. On macOS, right-click the app and choose **Open**. On Windows, click **More info**, then **Run anyway**.

### Building the installers (for maintainers)

- macOS: run `build/build_mac.sh` on an Apple Silicon Mac to produce the `.dmg`.
- Windows: the `.exe` is built by the GitHub Actions workflow `.github/workflows/build-windows.yml`. Run it from the Actions tab, then download the artifact.

## Run From Source (developers)

This path is for development, not for the end-user admin (who uses the desktop app above).

### First time? Run the installer:

1. Double-click **`install.command`**
2. **macOS will block it** — go to **System Settings > Privacy & Security**, scroll down, and click **Open Anyway** next to the blocked file
3. Wait for "Installation Complete!" (5-10 minutes on first run)

This installs Homebrew, Python, Node.js, and all dependencies. Safe to run again if needed.

> **Note:** You only need to approve the file once in Privacy & Security. The same applies to `Forecast_Tool_Launcher.command` and `stop.command` on first run.

### Launch the tool:

1. Double-click **`Forecast_Tool_Launcher.command`**
2. Wait for "Forecast Tool is running!" — your browser opens automatically
3. Type a forecast request in the chat, e.g. "Forecast Spring 2026"

### Stop the tool:

Double-click **`stop.command`**, or close the Terminal window.

### Full user guide:

See **[docs/HANDOFF_GUIDE.md](docs/HANDOFF_GUIDE.md)** for detailed instructions, troubleshooting, and FAQ.

## Troubleshooting

### "macOS cannot verify the developer"

Go to **System Settings > Privacy & Security**, find the blocked file, and click **Open Anyway**.

### Turbopack Database Error

If you encounter a "Failed to open database" error:
1. Double-click `stop.command` to stop everything
2. Delete the folder `frontend/.next`
3. Double-click `Forecast_Tool_Launcher.command` to restart

### Port Already in Use

Double-click `stop.command` to kill any leftover processes, then relaunch.

### Something Else?

See the full troubleshooting section in [docs/HANDOFF_GUIDE.md](docs/HANDOFF_GUIDE.md#troubleshooting).

## Architecture

Three-tier application: Next.js frontend, FastAPI backend, Python forecasting engine.

### Frontend (`frontend/`)

- **Framework**: Next.js 16, React 19, TypeScript
- **Styling**: Tailwind CSS 4, Radix UI
- **Dev server**: http://localhost:3000

### Backend (`api/`)

- **Framework**: FastAPI (Python)
- **Endpoints**: Chat (regex + optional LLM), forecast, config, adjustments, terms
- **Server**: http://localhost:8000

### Forecasting Engine

- **Default**: Auto (same-season historical first, sequence-map fallback when needed)
- **Historical**: course-level same-season projection from post-rollout PZSMSCP history
- **Sequence**: major sequencing guides project demand from feeder courses
- **Fallback**: Ratio-based (historical enrollment ratios, used for terms without sequencing data)
- **Alternative**: 3-model ensemble (OLS 40%, ETS 35%, ARIMA 25%)

### Key Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Section Capacity | 20 | Students per section |
| Progression Rate | 0.95 | Retention rate per term gap |
| Buffer | 10% | Extra capacity for late adds |

Edit via the Configuration sidebar in the UI, or directly in `forecast_config.json`.

### Cognos Data Input

The tool consumes a single Cognos report: **PZSMSCP - Flexible Master Schedule of Classes with Power Prompts**. Drop the export at `Data/Master Schedule of Classes.xlsx` (or `.csv`); both formats are supported. The xlsx and CSV loaders dedupe co-instructor rows by CRN, filter by SCAD term codes, and can forecast from ACT enrollment, scheduled max enrollment, or ACT + waitlist demand.

The companion `PZSAAPF-SL31` admits report (already wired) provides next-term applicant demand. No other Cognos reports are required.

## Documentation

- **[docs/HANDOFF_GUIDE.md](docs/HANDOFF_GUIDE.md)** — User guide with setup, usage, and troubleshooting
- **[docs/DEVELOPMENT_HISTORY.md](docs/DEVELOPMENT_HISTORY.md)** — Technical build chronicle
- **[docs/ADJUSTMENTS_POLICY.md](docs/ADJUSTMENTS_POLICY.md)**: Manual adjustment policy
- **[CLAUDE.md](CLAUDE.md)** — Developer reference (architecture, domain logic, endpoints)
- **[AGENTS.md](AGENTS.md)** — CLI forecasting runbook

## CLI Usage

The per-term CLI scripts (`forecast_spring26_from_sequence_guides.py` and siblings) are deprecated and have been removed from the repo. They no longer run. Run forecasts through the desktop app or the API endpoint `POST /api/forecast`.

The CLI runbook in [AGENTS.md](AGENTS.md) is retained as legacy reference only.
