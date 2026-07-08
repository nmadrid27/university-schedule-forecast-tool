import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import paths


def test_ensure_seeded_copies_missing_files(monkeypatch, tmp_path):
    bundle = tmp_path / "bundle"
    appdata = tmp_path / "appdata"
    (bundle / "seed").mkdir(parents=True)
    (bundle / "seed" / "FOUN_sequencing_map_by_major.csv").write_text("col\n1\n")
    (bundle / "seed_config").mkdir(parents=True)
    (bundle / "seed_config" / "forecast_config.json").write_text("{}")

    monkeypatch.setattr(paths, "is_frozen", lambda: True)
    monkeypatch.setattr(paths, "bundle_dir", lambda: bundle)
    monkeypatch.setattr(paths, "app_data_dir", lambda: appdata)

    paths.ensure_seeded()
    assert (appdata / "Data" / "FOUN_sequencing_map_by_major.csv").is_file()
    assert (appdata / "forecast_config.json").is_file()


def test_ensure_seeded_does_not_overwrite(monkeypatch, tmp_path):
    bundle = tmp_path / "bundle"
    appdata = tmp_path / "appdata"
    (bundle / "seed").mkdir(parents=True)
    (bundle / "seed" / "x.csv").write_text("new\n")
    (appdata / "Data").mkdir(parents=True)
    (appdata / "Data" / "x.csv").write_text("user-edited\n")

    monkeypatch.setattr(paths, "is_frozen", lambda: True)
    monkeypatch.setattr(paths, "bundle_dir", lambda: bundle)
    monkeypatch.setattr(paths, "app_data_dir", lambda: appdata)

    paths.ensure_seeded()
    assert (appdata / "Data" / "x.csv").read_text() == "user-edited\n"
