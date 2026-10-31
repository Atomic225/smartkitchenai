"""Root entrypoint for Streamlit cloud platforms (Hugging Face Spaces Streamlit SDK, Streamlit Community Cloud).

Starts the FastAPI backend if not already running, then loads the Streamlit dashboard.
"""

from __future__ import annotations

import os
import runpy
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "frontend") not in sys.path:
    sys.path.insert(0, str(ROOT / "frontend"))


def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def _ensure_backend_running() -> None:
    """Start uvicorn in the background if port 8000 is not yet listening."""
    if _is_port_open("127.0.0.1", 8000):
        return

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(ROOT / "frontend"), env.get("PYTHONPATH", "")])

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    subprocess.Popen(cmd, cwd=str(ROOT), env=env)

    # Wait up to 5 seconds for backend to become ready
    for _ in range(25):
        if _is_port_open("127.0.0.1", 8000):
            break
        time.sleep(0.2)


_ensure_backend_running()

# Run the frontend dashboard
runpy.run_path(str(ROOT / "frontend" / "streamlit_app.py"), run_name="__main__")
