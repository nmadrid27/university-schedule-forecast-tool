#!/bin/bash
#
# SCAD FOUN Enrollment Forecasting Tool - One-Time Installer
# Double-click this file to install all dependencies on a fresh Mac.
# Safe to run multiple times (idempotent).
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "=========================================="
echo "  SCAD Forecast Tool - Installer"
echo "=========================================="
echo ""
echo "This will install all required software."
echo "It may take 5-10 minutes on first run."
echo ""

# ---------- Homebrew ----------
echo "[1/5] Checking Homebrew..."
if command -v brew &> /dev/null; then
    echo "       Homebrew already installed."
else
    echo "       Installing Homebrew (you may be prompted for your password)..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add brew to PATH for Apple Silicon Macs
    if [ -f /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
fi
echo ""

# ---------- Python ----------
echo "[2/5] Checking Python..."
# Prefer python3 from brew, fall back to system
if command -v python3 &> /dev/null; then
    PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
        echo "       Python $PY_VERSION already installed."
    else
        echo "       Python $PY_VERSION found but 3.11+ is recommended."
        echo "       Installing Python via Homebrew..."
        brew install python@3.13
    fi
else
    echo "       Python not found. Installing via Homebrew..."
    brew install python@3.13
fi
echo ""

# ---------- Node.js ----------
echo "[3/5] Checking Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    NODE_MAJOR=$(echo "$NODE_VERSION" | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_MAJOR" -ge 18 ]; then
        echo "       Node.js $NODE_VERSION already installed."
    else
        echo "       Node.js $NODE_VERSION found but v18+ required."
        echo "       Installing Node.js via Homebrew..."
        brew install node
    fi
else
    echo "       Node.js not found. Installing via Homebrew..."
    brew install node
fi
echo ""

# ---------- Python Virtual Environment & Packages ----------
echo "[4/5] Setting up Python environment..."
if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    echo "       Virtual environment already exists."
else
    echo "       Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

echo "       Installing Python packages..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet
pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
deactivate
echo "       Python packages installed."
echo ""

# ---------- Node.js Dependencies ----------
echo "[5/5] Installing frontend dependencies..."
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "       ERROR: frontend/ directory not found."
    echo "       Expected at: $FRONTEND_DIR"
    osascript -e 'display dialog "Installation failed: frontend/ directory not found." buttons {"OK"} default button 1 with icon stop' 2>/dev/null || true
    exit 1
fi

cd "$FRONTEND_DIR"
npm install --silent
echo "       Frontend dependencies installed."
echo ""

# ---------- Done ----------
echo "=========================================="
echo "  Installation Complete!"
echo "=========================================="
echo ""
echo "You can now double-click Forecast_Tool_Launcher.command"
echo "to start the application."
echo ""

osascript -e 'display dialog "Installation complete! You can now launch the Forecast Tool by double-clicking Forecast_Tool_Launcher.command." buttons {"OK"} default button 1 with icon note' 2>/dev/null || true
