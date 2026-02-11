#!/bin/bash
#
# SCAD FOUN Enrollment Forecasting Tool - Stop All Servers
# Double-click this file to shut down the backend and frontend.
#

echo "=========================================="
echo "  Stopping Forecast Tool..."
echo "=========================================="
echo ""

STOPPED=0

# Kill processes on port 8000 (FastAPI backend)
PIDS_8000=$(lsof -ti:8000 2>/dev/null)
if [ -n "$PIDS_8000" ]; then
    echo "$PIDS_8000" | xargs kill 2>/dev/null
    echo "Stopped backend server (port 8000)."
    STOPPED=1
fi

# Kill processes on port 3000 (Next.js frontend)
PIDS_3000=$(lsof -ti:3000 2>/dev/null)
if [ -n "$PIDS_3000" ]; then
    echo "$PIDS_3000" | xargs kill 2>/dev/null
    echo "Stopped frontend server (port 3000)."
    STOPPED=1
fi

echo ""
if [ "$STOPPED" -eq 1 ]; then
    echo "All servers stopped."
else
    echo "No running servers found."
fi
echo ""
