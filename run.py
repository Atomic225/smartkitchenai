"""Start the FastAPI backend and Streamlit dashboard together."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((host, port)) == 0


def main() -> None:
    settings = get_settings()
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(ROOT / "frontend"), env.get("PYTHONPATH", "")])
    api_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        settings.api_host,
        "--port",
        str(settings.api_port),
    ]
    ui_port = os.environ.get("PORT", "8501")
    ui_cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(ROOT / "frontend" / "streamlit_app.py"),
        "--server.headless",
        "true",
        "--server.port",
        str(ui_port),
        "--server.address",
        "0.0.0.0",
        "--browser.gatherUsageStats",
        "false",
    ]
    print(f"Starting API on http://{settings.api_host}:{settings.api_port}")
    api = subprocess.Popen(api_cmd, cwd=str(ROOT), env=env)
    try:
        for _ in range(50):
            if _port_open(settings.api_host, settings.api_port):
                break
            if api.poll() is not None:
                raise SystemExit("API process exited before it became ready.")
            time.sleep(0.2)
        print(f"Starting dashboard on port {ui_port}...")
        ui = subprocess.Popen(ui_cmd, cwd=str(ROOT), env=env)
        try:
            while True:
                if api.poll() is not None:
                    ui.terminate()
                    raise SystemExit(f"API exited with {api.returncode}")
                if ui.poll() is not None:
                    api.terminate()
                    raise SystemExit(f"Dashboard exited with {ui.returncode}")
                time.sleep(0.5)
        finally:
            ui.terminate()
    finally:
        api.terminate()


if __name__ == "__main__":
    main()
