#!/bin/bash
#
# SCAD FOUN Enrollment Forecasting Tool - Full-Stack Launcher
# Double-click this file to start the backend API and frontend UI.
# Press Ctrl+C or close this window to stop both servers.
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV_DIR="$SCRIPT_DIR/.venv"
API_DIR="$SCRIPT_DIR/api"
BACKEND_PID=""
FRONTEND_PID=""
SKIP_UPDATE=0

# ---------- Parse arguments ----------
for arg in "$@"; do
    case "$arg" in
        --no-update) SKIP_UPDATE=1 ;;
    esac
done

# ---------- Cleanup on exit ----------
cleanup() {
    echo ""
    echo "Shutting down..."
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null
        wait "$FRONTEND_PID" 2>/dev/null
    fi
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null
        wait "$BACKEND_PID" 2>/dev/null
    fi
    # Also kill anything still on our ports
    lsof -ti:8000 2>/dev/null | xargs kill 2>/dev/null || true
    lsof -ti:3000 2>/dev/null | xargs kill 2>/dev/null || true
    echo "All servers stopped."
}
trap cleanup EXIT INT TERM

echo "=========================================="
echo "  SCAD Forecast Tool"
echo "=========================================="
echo ""

# ---------- Auto-update check ----------
if [ "$SKIP_UPDATE" -eq 0 ] && [ -d "$SCRIPT_DIR/.git" ]; then
    echo "Checking for updates..."
    cd "$SCRIPT_DIR"
    # Quick connectivity check (5-second timeout)
    if git fetch origin --quiet 2>/dev/null; then
        LOCAL=$(git rev-parse HEAD 2>/dev/null)
        REMOTE=$(git rev-parse origin/master 2>/dev/null)
        if [ "$LOCAL" != "$REMOTE" ] && [ -n "$REMOTE" ]; then
            echo "Update available! Pulling latest changes..."
            git pull origin master --quiet 2>/dev/null
            if [ $? -eq 0 ]; then
                echo "Installing updated dependencies..."
                source "$VENV_DIR/bin/activate"
                pip install -r "$SCRIPT_DIR/requirements.txt" --quiet 2>/dev/null
                deactivate
                cd "$FRONTEND_DIR"
                npm install --silent 2>/dev/null
                cd "$SCRIPT_DIR"
                echo "Update applied."
            else
                echo "Update failed — continuing with current version."
            fi
        else
            echo "Already up to date."
        fi
    else
        echo "Offline — skipping update check."
    fi
    echo ""
fi

# ---------- Preflight checks ----------
if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "Python environment not found."
    echo "Please run install.command first."
    echo ""
    osascript -e 'display dialog "Python environment not set up. Please run install.command first." buttons {"OK"} default button 1 with icon stop' 2>/dev/null || true
    exit 1
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "Frontend dependencies not installed."
    echo "Please run install.command first."
    echo ""
    osascript -e 'display dialog "Frontend not set up. Please run install.command first." buttons {"OK"} default button 1 with icon stop' 2>/dev/null || true
    exit 1
fi

# ---------- Kill stale processes on our ports ----------
lsof -ti:8000 2>/dev/null | xargs kill 2>/dev/null || true
lsof -ti:3000 2>/dev/null | xargs kill 2>/dev/null || true
sleep 1

# ---------- Start FastAPI backend ----------
echo "Starting backend server (port 8000)..."
source "$VENV_DIR/bin/activate"
cd "$API_DIR"
python3 main.py &
BACKEND_PID=$!
cd "$SCRIPT_DIR"

# Wait for backend to be ready (up to 30 seconds)
echo "Waiting for backend to start..."
for i in $(seq 1 30); do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "Backend ready."
        echo ""
        break
    fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo ""
        echo "Backend failed to start. Check the error above."
        echo ""
        osascript -e 'display dialog "Backend server failed to start. Check the terminal for errors." buttons {"OK"} default button 1 with icon stop' 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# Verify backend is actually running
if ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "Backend did not respond within 30 seconds."
    echo ""
    osascript -e 'display dialog "Backend server timed out. Check the terminal for errors." buttons {"OK"} default button 1 with icon stop' 2>/dev/null || true
    exit 1
fi

# ---------- Start Next.js frontend ----------
echo "Starting frontend (port 3000)..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"

# Wait for frontend to be ready (up to 30 seconds)
echo "Waiting for frontend to start..."
for i in $(seq 1 30); do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        break
    fi
    sleep 1
done

# ---------- Open browser ----------
echo ""
echo "=========================================="
echo "  Forecast Tool is running!"
echo "=========================================="
echo ""
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "  Close this window or press Ctrl+C to stop."
echo ""

open http://localhost:3000

# Keep script alive — wait for frontend process
wait $FRONTEND_PID
