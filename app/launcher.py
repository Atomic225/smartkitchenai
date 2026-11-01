"""Standalone FastAPI launcher that works in all environments (local, Streamlit Cloud, Hugging Face).

Guaranteed not to import Streamlit UI or runpy, so it is 100% safe to import anywhere.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _clean_val(v: object) -> str:
    s = str(v).strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()
    return s


def get_secrets_dict() -> dict[str, str]:
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
                raw_lines = p.read_text(encoding="utf-8").splitlines()
                pending_key = None
                for line in raw_lines:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip()
                        if v:
                            if k not in res:
                                res[k] = _clean_val(v)
                            pending_key = None
                        else:
                            pending_key = k
                    elif pending_key:
                        res[pending_key] = _clean_val(line)
                        pending_key = None
            except Exception:
                pass
    return res


def sync_secrets_to_env() -> dict[str, str]:
    """Inject secrets into os.environ and write them to ROOT/.env for pydantic."""
    secrets = get_secrets_dict()
    for k, v in secrets.items():
        os.environ[k] = v

    env_path = ROOT / ".env"
    existing: dict[str, str] = {}
    if env_path.is_file():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    existing[k.strip()] = v.strip()
        except Exception:
            pass
    existing.update(secrets)
    lines = [f"{k}={v}" for k, v in existing.items()]
    try:
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass

    return secrets


def is_port_open(host: str = "127.0.0.1", port: int = 8000) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def update_live_backend(secrets: dict[str, str]) -> None:
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


_active_proc: subprocess.Popen | None = None


def ensure_backend_running(max_wait_seconds: float = 25.0) -> bool:
    """Ensure FastAPI backend is running and up-to-date with current secrets.
    
    Returns True if port 8000 is open and accepting connections.
    """
    global _active_proc
    secrets = sync_secrets_to_env()

    if is_port_open("127.0.0.1", 8000):
        update_live_backend(secrets)
        return True

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(ROOT / "frontend"), env.get("PYTHONPATH", "")])

    data_dir = ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    log_file = data_dir / "uvicorn.log"

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

    try:
        log_out = open(log_file, "a", encoding="utf-8")
        log_out.write(f"\n--- Starting uvicorn at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        log_out.flush()
        _active_proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            env=env,
            stdout=log_out,
            stderr=subprocess.STDOUT,
        )
    except Exception as exc:
        try:
            with open(log_file, "a", encoding="utf-8") as out:
                out.write(f"Failed to spawn uvicorn process: {exc}\n")
        except Exception:
            pass
        return False

    deadline = time.time() + max_wait_seconds
    while time.time() < deadline:
        if is_port_open("127.0.0.1", 8000):
            update_live_backend(secrets)
            return True
        if _active_proc and _active_proc.poll() is not None:
            # Process crashed immediately
            return False
        time.sleep(0.3)

    return is_port_open("127.0.0.1", 8000)
