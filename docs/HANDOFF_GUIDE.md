# SCAD FOUN Enrollment Forecasting Tool — User Guide

A tool that predicts how many sections of Foundation (FOUN) courses SCAD will need for upcoming terms, based on current enrollment data and student sequencing guides.

---

## What This Tool Does

The tool answers the question: **"How many FOUN sections do we need next quarter?"**

It works by:
1. Looking at how many students are enrolled in prerequisite courses right now
2. Using SCAD's major sequencing guides to determine which FOUN courses those students will need next
3. Applying a progression rate (95% of students continue per term) to account for attrition
4. Calculating how many sections are needed based on a configurable section capacity (default: 20 students)

The tool supports all four SCAD quarters: Fall, Winter, Spring, and Summer.

---

## First-Time Setup

You only need to do this once. These steps install the software that the tool needs to run.

### Step 1: Unzip the Tool

1. Locate the ZIP file you received (e.g., `forecast-tool.zip`)
2. Double-click it to unzip
3. You should see a folder called `forecast-tool`

### Step 2: Run the Installer

1. Open the `forecast-tool` folder
2. Double-click **`install.command`**
3. If macOS asks "Are you sure you want to open this?", click **Open**
4. A Terminal window will appear showing progress:
   ```
   [1/5] Checking Homebrew...
   [2/5] Checking Python...
   [3/5] Checking Node.js...
   [4/5] Setting up Python environment...
   [5/5] Installing frontend dependencies...
   ```
5. Wait for "Installation Complete!" to appear (5-10 minutes on first run)
6. Click **OK** on the success dialog

> **Note:** The installer is safe to run again if something goes wrong. It will skip anything already installed.

---

## Daily Usage

### Starting the Tool

1. Open the `forecast-tool` folder
2. Double-click **`Forecast_Tool_Launcher.command`**
3. A Terminal window will appear. Wait for:
   ```
   Forecast Tool is running!

   Frontend:  http://localhost:3000
   Backend:   http://localhost:8000
   ```
4. Your web browser will open automatically to the tool

> **Keep the Terminal window open** while using the tool. Closing it will shut down the servers.

### Running a Forecast

1. In the chat area (center of the screen), type a message like:
   - `"Forecast Spring 2026"`
   - `"Show me Fall 2026 projections"`
   - `"Predict Summer 2026 enrollment"`
2. Press Enter or click Send
3. Results appear in the right panel showing:
   - **Course**: FOUN course number (e.g., FOUN 110)
   - **Campus**: Savannah or SCADnow
   - **Projected Seats**: Expected enrollment
   - **Sections**: Number of sections needed
   - **Change %**: How this compares to the previous forecast (if available)
4. Summary cards at the top show totals for students, sections, and courses forecasted

### Adjusting Settings

The right sidebar has controls for:

| Setting | What It Does | Default |
|---------|-------------|---------|
| **Capacity** | Students per section | 20 |
| **Progression Rate** | % of students who continue each term | 95% |
| **Buffer** | Extra capacity to add as cushion | 10% |

Change these and re-run your forecast to see updated results.

### Downloading Results

Click the **Download** button in the results panel to save a CSV file of the current forecast. The file will be named something like `forecast_spring_2026.csv`.

### Stopping the Tool

**Option A:** Close the Terminal window that opened when you launched the tool.

**Option B:** Double-click **`stop.command`** in the `forecast-tool` folder.

---

## Updating the Tool

When a new version of the tool is released, you can update with one double-click:

1. Open the `forecast-tool` folder
2. Double-click **`update.command`**
3. Wait for "Update Complete!" to appear
4. Click **OK** on the dialog

The updater pulls the latest code from GitHub and reinstalls any changed dependencies. It's safe to run anytime — it won't break a working installation.

> **Note:** The launcher also checks for updates automatically on startup. If you're online, it will pull new changes before starting the servers. To skip this, pass `--no-update` when running from the command line.

> **Tip:** If you don't have a `.git` folder (e.g., you received a plain ZIP), the updater will skip the code update step. Ask Nathan for a git-enabled copy to enable automatic updates.

### Dock Access (Optional)

For one-click access from your Dock:
1. Find **`SCAD Forecast Tool.app`** in the `forecast-tool` folder
2. Drag it to your Dock
3. Click it anytime to launch the tool (opens the same Terminal-based launcher)

> **Important:** Keep the `.app` inside the `forecast-tool` folder — it needs the other files to work.

---

## Updating Data for New Terms

When a new term starts and you have updated enrollment data:

### Adding New Enrollment Snapshots

1. Open the `Data/` folder inside `forecast-tool`
2. Drop in your new CSV file (e.g., `Spring26.csv`)
3. The file should have columns: `Course`, `Enrollment`, `Section #`, `Room`
   (or Master Schedule format: `SUBJ`, `CRS NUMBER`, `ACT ENR`, `CAMPUS`, `TERM`)

### Updating the Master Schedule

1. Replace `Data/Master Schedule of Classes.csv` with the updated version
2. Keep the same filename — the tool looks for this exact name

### Updating the Sequencing Map

If major sequencing guides change:
1. Update `Data/FOUN_sequencing_map_by_major.csv`
2. The format: columns for `campus`, `fall`, `winter`, `spring`, `summer` with FOUN course codes

---

## How the Tool Works (Simplified)

```
  Sequencing Guides          Enrollment Data
  (which courses              (how many students
   students take next)         are enrolled now)
         |                          |
         +----------+---------------+
                    |
            Forecasting Engine
           (applies progression
            rate & calculates
             sections needed)
                    |
         +----------+---------------+
         |                          |
   Forecast Results            CSV Export
   (in the browser)           (downloadable)
```

**Two forecasting methods:**

1. **Sequence-based** (primary): Uses SCAD sequencing guides to trace prerequisite enrollment into target FOUN courses. Most accurate for quarters with good sequencing data (Fall, Winter, Spring).

2. **Ratio-based** (fallback): When sequencing data is unavailable (e.g., Summer), applies historical enrollment ratios. For example, if Summer enrollment is historically 12% of Spring, it scales accordingly.

---

## File & Folder Reference

```
forecast-tool/
|
|-- install.command              <-- Run once to set up
|-- Forecast_Tool_Launcher.command  <-- Run to start the tool
|-- update.command               <-- Run to pull latest updates
|-- stop.command                 <-- Run to stop the tool
|-- SCAD Forecast Tool.app       <-- Drag to Dock for quick access
|
|-- Data/                        <-- Your enrollment data goes here
|   |-- Master Schedule of Classes.csv
|   |-- FOUN_sequencing_map_by_major.csv
|   |-- FAll25.csv, Winter26.csv, Spring25.csv, Summer25.csv
|   |-- FOUN_Historical.csv
|   |-- *_Forecast*.csv          <-- Generated forecast outputs
|
|-- frontend/                    <-- Web interface (don't modify)
|-- api/                         <-- Backend server (don't modify)
|-- forecast_tool/               <-- Forecasting engine (don't modify)
|-- forecast_config.json         <-- Settings file (editable)
|
|-- docs/                        <-- Documentation
    |-- HANDOFF_GUIDE.md         <-- This file
    |-- DEVELOPMENT_HISTORY.md   <-- Technical build history
```

---

## Troubleshooting

### "Node.js is not installed" or "Python environment not found"

**Solution:** Run `install.command` again. It will install any missing components.

### The browser opens but shows a blank page

**Likely cause:** The servers haven't finished starting yet.

**Solution:** Wait 10-15 seconds and refresh the page. Check the Terminal window for error messages.

### "Port already in use" error

**Cause:** A previous session didn't shut down cleanly.

**Solution:** Double-click `stop.command`, then try launching again.

### The forecast returns no results

**Possible causes:**
- The term you requested doesn't have enrollment data in the `Data/` folder
- The sequencing map doesn't have mappings for that quarter

**Solution:** Check that the relevant CSV files exist in `Data/`. For Summer forecasts, ensure a Spring forecast CSV exists (the ratio method needs it as input).

### "Failed to open database" error from the frontend

**Cause:** Turbopack (the frontend build tool) sometimes corrupts its cache.

**Solution:**
1. Stop the tool
2. Delete the folder `frontend/.next`
3. Restart with `Forecast_Tool_Launcher.command`

### Backend API isn't responding

**Check:** Open a web browser and go to `http://localhost:8000/docs` — you should see the API documentation page. If not, the backend hasn't started.

**Solution:** Stop everything, then restart. Check the Terminal for Python error messages.

---

## FAQ

**Q: Can I use this on a Windows computer?**
A: The tool is designed for macOS. The `.command` launcher scripts are macOS-specific. The underlying code (Python + Node.js) works on Windows, but you'd need to start the servers manually from the command line.

**Q: Do I need an internet connection?**
A: Only for the first-time setup (to download dependencies) and to receive updates. The forecasting itself runs entirely offline on your computer. If you're offline when launching, the auto-update check is skipped automatically.

**Q: How accurate are the forecasts?**
A: The sequence-based method is highly accurate for terms with good sequencing data because it directly traces enrolled students to their next courses. Ratio-based forecasts (used for Summer) are rougher estimates based on historical patterns.

**Q: Can I forecast more than one term ahead?**
A: The tool forecasts one term at a time. For multi-term planning, run forecasts sequentially (e.g., forecast Spring first, then use that to forecast Summer).

**Q: What if I need to change the section capacity for just one course?**
A: The current tool uses a single capacity across all courses. To handle per-course capacity, edit the results CSV manually after downloading.

**Q: Who do I contact for help?**
A: Contact Nathan Madrid for technical support or questions about the forecasting methodology.
