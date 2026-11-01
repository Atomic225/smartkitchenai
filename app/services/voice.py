from __future__ import annotations

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


def voice_status() -> dict:
    settings = get_settings()
    configured = settings.voice_configured()
    if settings.twilio_configured():
        name = "Twilio Voice"
        mode = f"live (Hindi {settings.twilio_voice})"
        detail = "Twilio credentials present. Outbound calls will speak directly to the cook in Hindi."
    elif settings.exotel_configured():
        name = "Exotel Voice"
        mode = "live"
        detail = "Exotel credentials present. Outbound calls will connect via Exotel."
    else:
        name = "Exotel Voice"
        mode = "mock_not_called"
        detail = "Not configured. Outbound chef calls are logged, but no phone call is placed."

    return {
        "name": name,
        "configured": configured,
        "mode": mode,
        "detail": detail,
        "required_fields": [
            "TWILIO_ACCOUNT_SID (or EXOTEL_SID)",
            "TWILIO_AUTH_TOKEN (or EXOTEL_API_KEY)",
            "TWILIO_PHONE_NUMBER (or EXOTEL_CALLER_ID)",
        ],
    }


def place_call(cook_phone: str, script_text: str = "") -> CallResult:
    """Place an outbound voice call to the cook with the Hindi menu script."""
    settings = get_settings()
    target_phone = cook_phone.strip()
    if not target_phone:
        return CallResult(False, False, "skipped", "Cook has no phone number registered. Call was NOT placed.")

    # 1. Twilio Voice with Native Hindi Polly TTS
    if settings.twilio_configured():
        clean_text = script_text.strip() or "Namaste bhaiya, aaj ka kitchen menu tayar hai."
        safe_script = (
            clean_text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            '<Pause length="1"/>'
            f'<Say language="{settings.twilio_language}" voice="{settings.twilio_voice}">{safe_script}</Say>'
            '<Pause length="1"/>'
            f'<Say language="{settings.twilio_language}" voice="{settings.twilio_voice}">Dhanyawad!</Say>'
            '</Response>'
        )

        url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid.strip()}/Calls.json"
        auth = (settings.twilio_account_sid.strip(), settings.twilio_auth_token.strip())
        data = {
            "To": target_phone if target_phone.startswith("+") else f"+91{target_phone.lstrip('0')}",
            "From": settings.twilio_phone_number.strip(),
            "Twiml": twiml,
        }

        try:
            resp = httpx.post(url, auth=auth, data=data, timeout=20)
            if resp.status_code in (200, 201):
                payload = resp.json()
                call_sid = str(payload.get("sid") or "")
                return CallResult(True, True, "initiated", "Twilio accepted call request with Hindi voice.", call_sid)
            return CallResult(
                True,
                False,
                "failed",
                f"Twilio rejected call ({resp.status_code}): {resp.text[:300]}",
            )
        except Exception as exc:
            return CallResult(True, False, "failed", f"Network error calling Twilio: {exc}")

    # 2. Exotel Fallback
    if settings.exotel_configured():
        from app.services.exotel import place_call as exotel_call
        return exotel_call(target_phone)

    # 3. Unconfigured fallback
    return CallResult(
        attempted=False,
        placed=False,
        status="not_configured",
        detail="Voice credentials missing (neither Twilio nor Exotel configured). Call was NOT placed.",
    )
