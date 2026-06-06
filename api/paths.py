"""Filesystem path resolution for dev and packaged (frozen) runs.

In dev, everything resolves under the project root so tests and the existing
workflow are unchanged. When frozen by PyInstaller, writable state lives in an
OS-specific user app-data folder, and read-only seed files live in the bundle.
"""

import os
import shutil
import sys
from pathlib import Path

APP_NAME = "SCAD Forecast Tool"

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundle_dir() -> Path:
    """Read-only resources. In frozen mode this is the PyInstaller temp dir."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return _PROJECT_ROOT


def app_data_dir() -> Path:
    """Writable base directory. Project root in dev; OS app-data when frozen."""
    if not is_frozen():
        return _PROJECT_ROOT
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    target = base / APP_NAME
    target.mkdir(parents=True, exist_ok=True)
    return target


def data_dir() -> Path:
    return app_data_dir() / "Data"


def config_path() -> Path:
    return app_data_dir() / "forecast_config.json"


def settings_path() -> Path:
    return app_data_dir() / "settings.json"


def ensure_seeded() -> None:
    """Copy bundled read-only seed files into the writable data dir on first run.

    No-op in dev (the repo files are used directly). Never overwrites existing
    user data.
    """
    if not is_frozen():
        return
    dst = data_dir()
    dst.mkdir(parents=True, exist_ok=True)
    seed_root = bundle_dir() / "seed"
    if seed_root.is_dir():
        for src in seed_root.rglob("*"):
            if src.is_file():
                rel = src.relative_to(seed_root)
                out = dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                if not out.exists():
                    shutil.copy2(src, out)
    cfg = config_path()
    seed_cfg = bundle_dir() / "seed_config" / "forecast_config.json"
    if not cfg.exists() and seed_cfg.is_file():
        shutil.copy2(seed_cfg, cfg)
