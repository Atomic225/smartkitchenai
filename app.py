"""Root entrypoint for Streamlit cloud platforms (Hugging Face Spaces Streamlit SDK, Streamlit Community Cloud).

Loads secrets into os.environ, starts the FastAPI backend, then launches the Streamlit dashboard.
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


def _clean_val(v: object) -> str:
    s = str(v).strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()
    return s


def _load_streamlit_secrets() -> None:
    """Read Streamlit Cloud secrets and inject into os.environ so FastAPI sees them."""
    # 1. Try reading from st.secrets if available
    try:
        import streamlit as st
        for k in st.secrets:
            v = st.secrets[k]
            if isinstance(v, (str, int, float, bool)):
                os.environ[str(k)] = _clean_val(v)
    except Exception:
        pass

    # 2. Try reading from secrets.toml files on disk
    candidates = [
        ROOT / ".streamlit" / "secrets.toml",
        Path.home() / ".streamlit" / "secrets.toml",
    ]
    for p in candidates:
        if not p.is_file():
            continue
        try:
            import tomllib
            with open(p, "rb") as f:
                data = tomllib.load(f)
            for k, v in data.items():
                if isinstance(v, (str, int, float, bool)):
                    os.environ[str(k)] = _clean_val(v)
        except Exception:
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = _clean_val(v)
            except Exception:
                pass


def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def _ensure_backend_running() -> None:
    """Start uvicorn in the background if port 8000 is not yet listening."""
    _load_streamlit_secrets()

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
