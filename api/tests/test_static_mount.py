import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main


def test_health_still_works():
    from fastapi.testclient import TestClient
    client = TestClient(main.app)
    r = client.get("/api/health")
    assert r.status_code == 200


def test_mount_helper_exists():
    assert hasattr(main, "mount_static_ui")
    main.mount_static_ui()  # no-op when build dir is absent; must not raise
