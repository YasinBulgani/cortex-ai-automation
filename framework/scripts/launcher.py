"""
Cortex Dashboard Launcher
=========================
Packaged by PyInstaller into CortexDashboard.exe. In order:
  1. Start the dashboard server (Waitress, with Flask dev as fallback).
  2. Health-check the server.
  3. Open http://localhost:5001 in the default browser.
  4. Stream console output; clean shutdown on Ctrl+C.
"""
from __future__ import annotations

import os
import sys
import time
import threading
import webbrowser
from pathlib import Path
from urllib.request import urlopen


def resource_path(relative: str) -> Path:
    """Works in both PyInstaller bundle and dev environment."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / relative
    return Path(__file__).resolve().parent.parent / relative


def configure_environment() -> int:
    """Working dir + env."""
    bundle_root = resource_path(".")
    os.chdir(str(bundle_root))

    py_dir = resource_path("python_server")
    if str(py_dir) not in sys.path:
        sys.path.insert(0, str(py_dir))

    port = int(os.environ.get("DASHBOARD_PORT", "5001"))
    return port


def wait_for_health(port: int, timeout: int = 15) -> bool:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/api/health"
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1) as resp:  # noqa: S310
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.4)
    return False


def open_browser_when_ready(port: int) -> None:
    if wait_for_health(port):
        webbrowser.open(f"http://localhost:{port}")
    else:
        print("ERROR: dashboard health check failed.", file=sys.stderr)


def run_server(port: int) -> None:
    from flask_api import app  # type: ignore

    try:
        from waitress import serve
        print(f"[Cortex] Dashboard listening on port {port} (waitress)")
        serve(app, host="0.0.0.0", port=port, threads=8)
    except ImportError:
        print(f"[Cortex] Dashboard listening on port {port} (flask dev)")
        app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


def main() -> int:
    port = configure_environment()

    print("=" * 60)
    print("  Cortex Otomasyon Dashboard")
    print(f"  http://localhost:{port}")
    print("  Exit: Ctrl+C")
    print("=" * 60)

    threading.Thread(target=open_browser_when_ready, args=(port,), daemon=True).start()

    try:
        run_server(port)
    except KeyboardInterrupt:
        print("\n[Cortex] Shutdown.")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
