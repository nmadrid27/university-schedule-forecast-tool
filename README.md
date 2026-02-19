# SCAD FOUN Enrollment Forecasting Tool

Predicts Foundation course enrollment and calculates section needs for upcoming terms. Primary method: sequence-based forecasting from major sequencing guides. Alternative: 3-model ensemble (Prophet + ETS + ARIMA).

## Quick Start (macOS)

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

- **Primary**: Sequence-based — uses major sequencing guides to project demand from feeder courses
- **Fallback**: Ratio-based — historical enrollment ratios (used for Summer and terms without sequencing data)
- **Alternative**: 3-model ensemble (Prophet 40%, ETS 35%, ARIMA 25%)

### Key Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Section Capacity | 20 | Students per section |
| Progression Rate | 0.95 | Retention rate per term gap |
| Buffer | 10% | Extra capacity for late adds |

Edit via the Configuration sidebar in the UI, or directly in `forecast_config.json`.

## Documentation

- **[docs/HANDOFF_GUIDE.md](docs/HANDOFF_GUIDE.md)** — User guide with setup, usage, and troubleshooting
- **[docs/DEVELOPMENT_HISTORY.md](docs/DEVELOPMENT_HISTORY.md)** — Technical build chronicle
- **[CLAUDE.md](CLAUDE.md)** — Developer reference (architecture, domain logic, endpoints)
- **[AGENTS.md](AGENTS.md)** — CLI forecasting runbook

## CLI Usage

For automated/batch forecasting without the UI:

```bash
source .venv/bin/activate
python3 forecast_spring26_from_sequence_guides.py --config forecast_config.json
```

See [AGENTS.md](AGENTS.md) for the full CLI workflow.
