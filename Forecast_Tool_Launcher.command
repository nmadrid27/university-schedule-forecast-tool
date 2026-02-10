#!/bin/bash
#
# SCAD FOUN Enrollment Forecasting Tool - One-Click Launcher
# Automatically sets up Node.js dependencies and launches the Next.js frontend
#
# Usage: Double-click this file to launch the application
#

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo "=========================================="
echo "SCAD Forecast Tool Launcher"
echo "=========================================="
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed."
    echo ""
    echo "Please install Node.js from:"
    echo "https://nodejs.org/"
    echo ""
    osascript -e 'display dialog "Node.js required. Please install from nodejs.org" buttons {"OK"} default button 1 with icon stop'
    exit 1
fi

# Check if npm is available
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed."
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

# Check Node and npm versions
NODE_VERSION=$(node --version)
NPM_VERSION=$(npm --version)
echo "✓ Found Node.js $NODE_VERSION"
echo "✓ Found npm $NPM_VERSION"
echo ""

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ Frontend directory not found at:"
    echo "   $FRONTEND_DIR"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

# Navigate to frontend directory
cd "$FRONTEND_DIR"

# Install dependencies
echo "Installing dependencies..."
echo "(This may take a minute on first run)"
echo ""

npm install

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Failed to install dependencies."
    echo ""
    echo "Try running manually:"
    echo "  cd '$FRONTEND_DIR'"
    echo "  npm install"
    echo "  npm run dev"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

echo ""
echo "=========================================="
echo "Launching Forecast Tool..."
echo "=========================================="
echo ""
echo "The application will open in your browser at http://localhost:3000"
echo "To stop the application, close this window or press Ctrl+C"
echo ""

# Launch Next.js dev server
npm run dev

# Keep window open if there's an error
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Application stopped with an error."
    echo ""
    read -p "Press Enter to close..."
fi
