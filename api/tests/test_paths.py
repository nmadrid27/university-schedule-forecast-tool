import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import paths

# The project root is two levels above the api/ package (api/tests/ -> api/ -> root).
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_dev_mode_uses_project_root():
    assert paths.is_frozen() is False
    assert paths.data_dir() == paths.app_data_dir() / "Data"
    assert paths.config_path() == paths.app_data_dir() / "forecast_config.json"
    assert paths.settings_path() == paths.app_data_dir() / "settings.json"


def test_app_data_dir_is_project_root_in_dev():
    assert paths.app_data_dir() == PROJECT_ROOT


def test_bundle_dir_is_project_root_in_dev():
    assert paths.bundle_dir() == PROJECT_ROOT
