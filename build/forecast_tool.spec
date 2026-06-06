# PyInstaller spec for the SCAD Forecast Tool desktop app.
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

hiddenimports = (
    collect_submodules("statsmodels")
    + collect_submodules("pandas")
    + collect_submodules("uvicorn")
)
datas = (
    [("../frontend/out", "web")]
    + [("../build/seed", "seed")]
    + [("../build/seed_config", "seed_config")]
    + collect_data_files("statsmodels")
)

a = Analysis(
    ["../desktop/app.py"],
    pathex=["../api"],
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
