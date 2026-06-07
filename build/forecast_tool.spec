# PyInstaller spec for the SCAD Forecast Tool desktop app.
import os
import sys

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Resolve everything against the spec's own directory so paths do not depend
# on the working directory PyInstaller is invoked from. SPECPATH is injected
# by PyInstaller and points at this file's folder (build/).
ROOT_DIR = os.path.abspath(os.path.join(SPECPATH, ".."))
API_DIR = os.path.join(ROOT_DIR, "api")

# Make the app's own modules importable while this spec is evaluated, so
# collect_submodules() below can introspect forecast_tool.
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, API_DIR)

block_cipher = None

# The backend modules live as top-level modules in api/ and are imported by
# desktop/app.py via a runtime sys.path insert that PyInstaller's static
# analysis cannot see. List them explicitly so they are bundled.
app_modules = ["main", "paths", "forecaster", "adjustments", "llm_service"]

hiddenimports = (
    app_modules
    + collect_submodules("forecast_tool")
    + collect_submodules("statsmodels")
    + collect_submodules("pandas")
    + collect_submodules("uvicorn")
)
datas = (
    [(os.path.join(ROOT_DIR, "frontend", "out"), "web")]
    + [(os.path.join(ROOT_DIR, "build", "seed"), "seed")]
    + [(os.path.join(ROOT_DIR, "build", "seed_config"), "seed_config")]
    + collect_data_files("statsmodels")
)

a = Analysis(
    [os.path.join(ROOT_DIR, "desktop", "app.py")],
    pathex=[ROOT_DIR, API_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["prophet", "cmdstanpy", "tkinter", "matplotlib"],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="SCAD Forecast Tool",
          console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="SCAD Forecast Tool")
app = BUNDLE(coll, name="SCAD Forecast Tool.app",
             bundle_identifier="edu.scad.forecasttool")
