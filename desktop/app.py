"""Desktop entry point: run FastAPI locally and show it in a native window."""

import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

# Make the api/ package importable both in dev and when frozen.
APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT / "api"))

import uvicorn

import main as api_main


def _free_port(preferred: int = 8000) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


class _Server:
    def __init__(self, port: int):
        config = uvicorn.Config(api_main.app, host="127.0.0.1", port=port, log_level="warning")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._server.should_exit = True


def _wait_for_health(port: int, timeout: float = 30.0) -> bool:
    url = f"http://127.0.0.1:{port}/api/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


class _Bridge:
    """JS-callable API exposed to the webview for native dialogs."""

    def create_file_dialog(self):
        import webview

        result = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=("Schedule exports (*.xlsx;*.xls;*.csv)", "All files (*.*)"),
        )
        return list(result) if result else None


def run() -> int:
    import webview

    port = _free_port(8000)
    server = _Server(port)
    server.start()
    if not _wait_for_health(port):
        server.stop()
        sys.stderr.write("Backend failed to start.\n")
        return 1
    webview.create_window(
        "SCAD Forecast Tool",
        f"http://127.0.0.1:{port}/",
        width=1400,
        height=900,
        js_api=_Bridge(),
    )
    webview.start()  # blocks until the window is closed
    server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
