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

## Installing the Desktop App

This is the recommended way to use the tool. You install a regular double-click app, and everything runs on your own computer. No setup beyond the installer is required.

### macOS

1. Open the `.dmg` file you received.
2. Drag **SCAD Forecast Tool** into the **Applications** folder.
3. The first time you open it, right-click (or Control-click) the app in Applications and choose **Open**, then click **Open** again in the dialog. This clears a one-time security warning, because version 1 is unsigned.
4. After that first time, open the app normally (double-click).

### Windows

1. Run **`SCAD-Forecast-Tool-Setup.exe`**.
2. If a blue **"Windows protected your PC"** screen appears, click **More info**, then **Run anyway**. This is a one-time step, because version 1 is unsigned.
3. If the app window is blank when it opens, install the **Microsoft Edge WebView2 Runtime** (a free Microsoft download), then reopen the app. WebView2 is already present on Windows 11 and on most updated Windows 10 machines, so you may not need this step.

### Where Your Data Lives

The app keeps your data on your own computer:

- macOS: `~/Library/Application Support/SCAD Forecast Tool/`
- Windows: `%APPDATA%\SCAD Forecast Tool\`

You normally do not need to open this folder.

### Loading Data Each Quarter

Click **Import Master Schedule…** inside the app and pick your PZSMSCP export. The app copies it into place; there is no need to move files by hand.

**The tool forecasts each course from last year's same term,** so the export should include the **prior year's same quarter**: to forecast Fall 2026, include Fall 2025. If that term is missing, the app says so instead of returning a screen of zeros. Brand-new courses with no prior history are flagged for a manual estimate.

If you switch to the older sequence-map method, a different rule applies. **That method's export must include the two quarters *before* the term you want to forecast,** because the model projects forward from those feeder terms. To forecast Spring, the file must contain that year's Fall and Winter (term codes `202610` and `202620`) alongside Spring. Do **not** import the term's own final actuals; that is the result you are trying to predict, and the app will now stop and tell you the feeder term is missing instead of returning a screen of zeros.

Optionally, click **Import Admits (optional)…** and pick the **PZSAAPF — Accepted Applicants** report. It feeds new-student demand into the intro courses (FOUN 110/111); without it, those courses read low.

### Updating the App

When a new version is provided, download and run the new installer. There is no auto-update in this version.

---

## Run From Source (developers)

This path is only for developers running the tool from source. If you are the scheduling admin, use the desktop app described above instead.

You only need to do this once. These steps install the software that the tool needs to run.

### Step 1: Unzip the Tool

1. Locate the ZIP file you received (e.g., `forecast-tool.zip`)
2. Double-click it to unzip
3. You should see a folder called `forecast-tool`

### Step 2: Run the Installer

1. Open the `forecast-tool` folder
2. Double-click **`install.command`**
3. **macOS will likely block it** the first time. If you see a security warning:
   - Open **System Settings > Privacy & Security**
   - Scroll down to find the blocked file message
   - Click **Open Anyway**
   - You only need to do this once per `.command` file
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

> **Desktop app users:** the steps below describe the run-from-source launcher. If you installed the desktop app, just open **SCAD Forecast Tool** like any other app; it opens its own window, and there is no Terminal, separate browser tab, or launcher script to run.

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

The tool consumes **one Cognos report** for term-to-term updates: the **PZSMSCP — Flexible Master Schedule of Classes with Power Prompts** export. When a new term begins, refresh this single file and you are done.

### Pulling the Master Schedule from Cognos

1. Log in to Cognos and run the report named **`PZSMSCP - Flexible Master Schedule of Classes with Power Prompts`**.
2. In the prompt screen, select all terms relevant to the forecast (typically: the previous Fall, current Winter, and upcoming Spring — e.g. `202610`, `202620`, `202630`).
3. Run the report and **export to Excel (.xlsx)**. CSV also works if you prefer.
4. Save the file to `Data/Master Schedule of Classes.xlsx` (or `.csv`) inside the `forecast-tool` folder. **Keep the filename as `Master Schedule of Classes.xlsx`** — the tool looks for this name. If you previously had a `.csv` version, you can leave it; just update `forecast_config.json`'s `enrollment_source` to point at the new file.

The xlsx loader handles the Cognos quirks automatically:
- Skips the ~16 rows of report metadata above the headers
- Dedupes co-taught sections (the report emits one row per instructor per CRN)
- Filters by SCAD term code

### Adding New Enrollment Snapshots (Optional)

If you have a one-off snapshot CSV in the older format (`Course`, `Enrollment`, `Section #`, `Room` columns), drop it in `Data/`. The tool detects the format automatically.

### Updating the Sequencing Map

If major sequencing guides change:
1. Update `Data/FOUN_sequencing_map_by_major.csv`
2. The format: columns for `campus`, `fall`, `winter`, `spring`, `summer` with FOUN course codes

### What you do NOT need

The tool used to consume an additional **Cognos enrollment-by-major report** to weight prerequisite enrollment by program. **This feature is disabled in production** because the underlying report requires student-level data access that the institutional planning role does not have. You do not need to pull or maintain this file. (`forecast_config.json` ships with `"enrollmentByMajorFile": null`.)

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

**Forecasting methods:**

1. **Auto** (default): Uses same-season historical data when the prior year's same quarter exists, then falls back to the sequence-map method when that history does not exist yet.

2. **Same-season historical**: Forecasts each course from its own prior same-season enrollment. This is best once the FOUN curriculum has at least one prior instance of that quarter.

3. **Sequence-based**: Uses SCAD sequencing guides to trace prerequisite enrollment into target FOUN courses. This is still useful for first post-rollout seasons such as Spring 2026.

4. **Ratio-based** (fallback): When sequencing data is unavailable, applies historical enrollment ratios. For example, if Summer enrollment is historically 12% of Spring, it scales accordingly.

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
- Historical mode is selected but the prior year's same quarter is not in the imported Master Schedule
- Sequence mode is selected but the two feeder quarters are not in the imported Master Schedule
- The sequencing map doesn't have mappings for that quarter

**Solution:** Use Auto mode when unsure. If a method-specific error appears, import the missing PZSMSCP term named in the message.

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
A: Yes. The desktop app ships for both macOS and Windows; see "Installing the Desktop App" above. The older `.command` launcher scripts are macOS-only and belong to the run-from-source path for developers.

**Q: Do I need an internet connection?**
A: No. The desktop app runs entirely offline once installed; you only need to be online to download the installer or a new version. (The run-from-source path needs internet for first-time dependency setup and updates, but forecasting itself is always offline.)

**Q: How accurate are the forecasts?**
A: Treat the forecast as a planning estimate, not a guarantee. Auto mode now uses course-level same-season history when available and sequence-map routing when history is not available. The app also includes a backtest endpoint (`POST /api/backtest`) for comparing a forecast against later PZSMSCP ACT/MAX/waitlist ground truth. For Spring 2026, existing calibration docs show that the sequence-map method is directionally useful but misallocates demand by course and campus; use the Planning Metric selector (ACT, MAX, or ACT + waitlist) and backtests to choose the right planning target.

**Q: Can I forecast more than one term ahead?**
A: The tool forecasts one term at a time. For multi-term planning, run forecasts sequentially (e.g., forecast Spring first, then use that to forecast Summer).

**Q: What if I need to change the section capacity for just one course?**
A: The current tool uses a single capacity across all courses. To handle per-course capacity, edit the results CSV manually after downloading.

**Q: Who do I contact for help?**
A: Contact Nathan Madrid for technical support or questions about the forecasting methodology.
