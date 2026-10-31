from dataclasses import dataclass

import httpx

from app.config import get_settings


@dataclass
class CallResult:
    attempted: bool
    placed: bool
    status: str
    detail: str
    provider_id: str = ""


def exotel_status() -> dict:
    settings = get_settings()
    configured = settings.exotel_configured()
    missing_app = configured and not settings.exotel_app_id.strip()
    detail = "Not configured. Outbound chef calls are logged, but no phone call is placed."
    if configured and missing_app:
        detail = (
            "Account credentials are present, but EXOTEL_APP_ID is empty. "
            "The app will attempt a connect call to the cook using CallerId only."
        )
    elif configured:
        detail = "Credentials present. Calls will be placed through Exotel."
    return {
        "name": "Exotel Voice",
        "configured": configured,
        "mode": "live" if configured else "mock_not_called",
        "detail": detail,
        "required_fields": [
            "EXOTEL_SID",
            "EXOTEL_API_KEY",
            "EXOTEL_API_TOKEN",
            "EXOTEL_CALLER_ID",
            "EXOTEL_APP_ID (recommended for menu playback)",
        ],
    }


def place_call(cook_phone: str) -> CallResult:
    settings = get_settings()
    if not cook_phone.strip():
        return CallResult(False, False, "skipped", "Cook has no phone number. Call was NOT placed.")
    if not settings.exotel_configured():
        return CallResult(
            attempted=False,
            placed=False,
            status="not_configured",
            detail="Exotel credentials missing. Call was NOT placed.",
        )

    url = (
        f"https://{settings.exotel_api_key}:{settings.exotel_api_token}"
        f"@{settings.exotel_subdomain}/v1/Accounts/{settings.exotel_sid}/Calls/connect.json"
    )
    form: dict[str, str] = {
        "From": cook_phone.strip().lstrip("+"),
        "CallerId": settings.exotel_caller_id.strip(),
    }
    if settings.exotel_app_id.strip():
        form["Url"] = f"http://my.exotel.com/exoml/start_voice/{settings.exotel_app_id.strip()}"
    if settings.exotel_status_callback_url.strip():
        form["StatusCallback"] = settings.exotel_status_callback_url.strip()

    try:
        response = httpx.post(url, data=form, timeout=20)
    except httpx.HTTPError as exc:
        return CallResult(True, False, "failed", f"Network error talking to Exotel: {exc}")

    if response.status_code >= 400:
        return CallResult(
            True,
            False,
            "failed",
            f"Exotel rejected the request ({response.status_code}): {response.text[:500]}",
        )
    provider_id = ""
    try:
        data = response.json()
        call = data.get("Call") or data
        provider_id = str(call.get("Sid") or call.get("sid") or "")
    except ValueError:
        provider_id = ""
    return CallResult(True, True, "initiated", "Exotel accepted the outbound call request.", provider_id)
