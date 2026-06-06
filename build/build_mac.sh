#!/bin/bash
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[1/4] Building frontend (static export)..."
corepack enable
(cd frontend && NEXT_PUBLIC_API_URL='' pnpm install --frozen-lockfile && pnpm run build)

echo "[2/4] Installing desktop build deps..."
python3.13 -m venv .venv-build 2>/dev/null || true
source .venv-build/bin/activate
pip install --upgrade pip
pip install -r requirements-desktop.txt

echo "[3/4] Running PyInstaller..."
pyinstaller --noconfirm --clean --workpath .pyi-build --distpath dist build/forecast_tool.spec

echo "[4/4] Building .dmg..."
pip install dmgbuild
dmgbuild -s build/dmg_settings.py "SCAD Forecast Tool" "dist/SCAD Forecast Tool.dmg"

echo "Done. App at dist/SCAD Forecast Tool.app"
