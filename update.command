#!/bin/bash
#
# SCAD FOUN Enrollment Forecasting Tool - Update Script
# Double-click this file to pull the latest version and update dependencies.
# Safe to run anytime — will not break a working installation.
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "=========================================="
echo "  SCAD Forecast Tool - Updater"
echo "=========================================="
echo ""

ERRORS=0

# ---------- Step 1: Git pull ----------
echo "[1/3] Checking for updates..."

if [ ! -d "$SCRIPT_DIR/.git" ]; then
    echo "       No git repository found. Skipping code update."
    echo "       (To enable updates, clone from GitHub instead of using a plain ZIP.)"
    echo ""
else
    cd "$SCRIPT_DIR"
    # Check if remote is reachable (timeout after 5 seconds)
    if git ls-remote --exit-code origin HEAD > /dev/null 2>&1; then
        # Stash any local changes to prevent merge conflicts
        LOCAL_CHANGES=$(git status --porcelain 2>/dev/null | grep -v '^\?\?' | wc -l | tr -d ' ')
        if [ "$LOCAL_CHANGES" -gt 0 ]; then
            echo "       Stashing local changes..."
            git stash --quiet
            STASHED=1
        fi

        BEFORE=$(git rev-parse HEAD)
        git pull origin master --quiet 2>&1
        PULL_EXIT=$?
        AFTER=$(git rev-parse HEAD)

        if [ "$PULL_EXIT" -ne 0 ]; then
            echo "       Warning: git pull failed. Continuing with current version."
            ERRORS=1
        elif [ "$BEFORE" = "$AFTER" ]; then
            echo "       Already up to date."
        else
            COMMITS=$(git log --oneline "$BEFORE".."$AFTER" | wc -l | tr -d ' ')
            echo "       Updated! ($COMMITS new commit(s) pulled)"
        fi

        # Restore stashed changes
        if [ "${STASHED:-0}" -eq 1 ]; then
            echo "       Restoring local changes..."
            git stash pop --quiet 2>/dev/null || true
        fi
    else
        echo "       Cannot reach GitHub (offline?). Skipping code update."
    fi
    echo ""
fi

# ---------- Step 2: Python dependencies ----------
echo "[2/3] Updating Python packages..."

if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
    pip install -r "$SCRIPT_DIR/requirements.txt" --quiet 2>&1
    PIP_EXIT=$?
    deactivate
    if [ "$PIP_EXIT" -eq 0 ]; then
        echo "       Python packages up to date."
    else
        echo "       Warning: Some Python packages failed to install."
        ERRORS=1
    fi
else
    echo "       No virtual environment found. Run install.command first."
    ERRORS=1
fi
echo ""

# ---------- Step 3: Frontend dependencies ----------
echo "[3/3] Updating frontend packages..."

if [ -d "$FRONTEND_DIR" ]; then
    cd "$FRONTEND_DIR"
    npm install --silent 2>&1
    NPM_EXIT=$?
    if [ "$NPM_EXIT" -eq 0 ]; then
        echo "       Frontend packages up to date."
    else
        echo "       Warning: npm install had issues."
        ERRORS=1
    fi
else
    echo "       Frontend directory not found. Run install.command first."
    ERRORS=1
fi
echo ""

# ---------- Done ----------
echo "=========================================="
if [ "$ERRORS" -eq 0 ]; then
    echo "  Update Complete!"
    echo "=========================================="
    echo ""
    echo "You can now launch the tool with Forecast_Tool_Launcher.command"
    echo ""
    osascript -e 'display dialog "Update complete! The Forecast Tool is ready to launch." buttons {"OK"} default button 1 with icon note' 2>/dev/null || true
else
    echo "  Update Finished (with warnings)"
    echo "=========================================="
    echo ""
    echo "Some steps had issues. Check the messages above."
    echo "The tool may still work — try launching it."
    echo ""
    osascript -e 'display dialog "Update finished with some warnings. Check the terminal for details." buttons {"OK"} default button 1 with icon caution' 2>/dev/null || true
fi
