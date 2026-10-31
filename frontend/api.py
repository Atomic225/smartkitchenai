from __future__ import annotations

import os
from typing import Any

import httpx

API_URL = os.environ.get("SMARTKITCHEN_API", "http://127.0.0.1:8000")


class ApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def request(method: str, path: str, **kwargs) -> Any:
    url = f"{API_URL}{path}"
    try:
        response = httpx.request(method, url, timeout=60, **kwargs)
    except httpx.HTTPError as exc:
        raise ApiError(
            f"Cannot reach the Smart Kitchen API at {API_URL}. Start it with python run.py. ({exc})"
        ) from exc
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
