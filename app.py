"""Root entrypoint for Streamlit cloud platforms (Hugging Face Spaces Streamlit SDK, Streamlit Community Cloud).

Loads secrets into os.environ and running FastAPI backend, starts uvicorn if needed, then launches Streamlit.
"""

from __future__ import annotations

import json
import os
import runpy
import socket
import subprocess
import sys
import time
import urllib.request
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


def _get_secrets_dict() -> dict[str, str]:
    """Extract secrets from st.secrets and secrets.toml."""
    res: dict[str, str] = {}
    try:
        import streamlit as st
        for k in st.secrets:
            v = st.secrets[k]
            if isinstance(v, (str, int, float, bool)):
                res[str(k)] = _clean_val(v)
    except Exception:
        pass

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
                if isinstance(v, (str, int, float, bool)) and str(k) not in res:
                    res[str(k)] = _clean_val(v)
        except Exception:
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() not in res:
                            res[k.strip()] = _clean_val(v)
            except Exception:
                pass
    return res


def _sync_secrets_to_env() -> dict[str, str]:
    """Inject secrets into os.environ and write them to ROOT/.env for pydantic."""
    secrets = _get_secrets_dict()
    for k, v in secrets.items():
        os.environ[k] = v

    # Write / update .env file so running backend can reload it
    env_path = ROOT / ".env"
    existing: dict[str, str] = {}
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()
    existing.update(secrets)
    lines = [f"{k}={v}" for k, v in existing.items()]
    try:
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass

    return secrets


def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def _update_live_backend(secrets: dict[str, str]) -> None:
    """Send updated secrets to the live running FastAPI backend via its settings endpoint."""
    if not secrets:
        return
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/settings/env",
            data=json.dumps(secrets).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            pass
    except Exception:
        pass


def _ensure_backend_running() -> None:
    """Ensure backend is running and up-to-date with current secrets."""
    secrets = _sync_secrets_to_env()

    if _is_port_open("127.0.0.1", 8000):
        # Backend is already running on port 8000: update its secrets in-memory without restarting!
        _update_live_backend(secrets)
        return

    # Backend is not running: start fresh uvicorn process
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
