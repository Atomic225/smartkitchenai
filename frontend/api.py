from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx

API_URL = os.environ.get("SMARTKITCHEN_API", "http://127.0.0.1:8000")


class ApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _auto_start_local_backend() -> bool:
    try:
        from app.launcher import ensure_backend_running
        return ensure_backend_running(max_wait_seconds=25.0)
    except Exception:
        return False


def request(method: str, path: str, **kwargs) -> Any:
    url = f"{API_URL}{path}"
    try:
        response = httpx.request(method, url, timeout=60, **kwargs)
    except httpx.HTTPError as exc:
        # If localhost and refused, try auto-starting the backend and retry once
        if "127.0.0.1" in API_URL or "localhost" in API_URL:
            if _auto_start_local_backend():
                try:
                    response = httpx.request(method, url, timeout=60, **kwargs)
                except httpx.HTTPError as retry_exc:
                    exc = retry_exc
                else:
                    return _handle_response(response)

        # Read last lines of uvicorn.log if available to provide useful diagnostics
        log_snippet = ""
        log_file = Path(__file__).resolve().parent.parent / "data" / "uvicorn.log"
        if log_file.is_file():
            try:
                lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
                if lines:
                    last_few = "\n".join(lines[-10:])
                    log_snippet = f"\nRecent backend log:\n{last_few}"
            except Exception:
                pass

        raise ApiError(
            f"Cannot reach the Smart Kitchen API at {API_URL}. Start it with python run.py. ({exc}){log_snippet}"
        ) from exc

    return _handle_response(response)


def _handle_response(response: httpx.Response) -> Any:
    if response.status_code >= 400:
        detail = response.text
        try:
            detail = response.json().get("detail", detail)
        except Exception:
            pass
        raise ApiError(str(detail), response.status_code)
    if response.status_code == 204 or not response.content:
        return None
    return response.json()


def get(path: str, **kwargs) -> Any:
    return request("GET", path, **kwargs)


def post(path: str, **kwargs) -> Any:
    return request("POST", path, **kwargs)


def put(path: str, **kwargs) -> Any:
    return request("PUT", path, **kwargs)


def delete(path: str, **kwargs) -> Any:
    return request("DELETE", path, **kwargs)
