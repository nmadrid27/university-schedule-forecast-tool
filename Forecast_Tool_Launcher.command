#!/bin/bash
#
# SCAD FOUN Enrollment Forecasting Tool - One-Click Launcher
# Automatically sets up Python environment and launches the chat interface
#
# Usage: Double-click this file to launch the application
#

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_MIN_VERSION="3.9"

echo "=========================================="
echo "SCAD Forecast Tool Launcher"
echo "=========================================="
echo ""

# Function to compare version numbers
version_ge() {
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed."
    echo ""
    echo "Please install Python 3.9 or later from:"
    echo "https://www.python.org/downloads/"
    echo ""
    osascript -e 'display dialog "Python 3 required. Please install from python.org" buttons {"OK"} default button 1 with icon stop'
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Found Python $PYTHON_VERSION"

if ! version_ge "$PYTHON_VERSION" "$PYTHON_MIN_VERSION"; then
    echo "⚠️  Python $PYTHON_MIN_VERSION or later is recommended."
    echo "   You have Python $PYTHON_VERSION"
    echo ""
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"

    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment."
        echo ""
        read -p "Press Enter to exit..."
        exit 1
    fi

    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip quietly
echo "Updating package installer..."
python3 -m pip install -q --upgrade pip

# Install/update dependencies
echo ""
echo "Installing dependencies..."
echo "(This may take a few minutes on first run)"
echo ""

if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    python3 -m pip install -q -r "$SCRIPT_DIR/requirements.txt"

    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies."
        echo ""
        echo "Try running manually:"
        echo "  cd '$SCRIPT_DIR'"
        echo "  source .venv/bin/activate"
        echo "  pip install -r requirements.txt"
        echo ""
        read -p "Press Enter to exit..."
        exit 1
    fi

    echo "✓ Dependencies installed"
else
    echo "⚠️  requirements.txt not found. Installing core packages..."
    python3 -m pip install -q streamlit prophet statsmodels pandas numpy openpyxl
fi

# Check if app_chat.py exists
if [ ! -f "$SCRIPT_DIR/app_chat.py" ]; then
    echo ""
    echo "❌ app_chat.py not found in:"
    echo "   $SCRIPT_DIR"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

# Launch Streamlit
echo ""
echo "=========================================="
echo "Launching Forecast Tool..."
echo "=========================================="
echo ""
echo "The application will open in your browser."
echo "To stop the application, close this window or press Ctrl+C"
echo ""

cd "$SCRIPT_DIR"

# Launch Streamlit with browser auto-open
python3 -m streamlit run app_chat.py --server.headless false --server.address localhost

# Keep window open if there's an error
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Application stopped with an error."
    echo ""
    read -p "Press Enter to close..."
fi
