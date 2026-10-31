from dataclasses import dataclass

import httpx

from app.config import get_settings


@dataclass
class SendResult:
    attempted: bool
    sent: bool
    status: str
    detail: str
    provider_id: str = ""


def whatsapp_status() -> dict:
    settings = get_settings()
    configured = settings.whatsapp_configured()
    return {
        "name": "WhatsApp Business Cloud API",
        "configured": configured,
        "mode": "live" if configured else "mock_not_sent",
        "detail": (
            "Credentials present. Messages will be posted to Meta Graph API."
            if configured
            else "Not configured. Grocery reminders are logged, but WhatsApp messages are NOT sent."
        ),
        "required_fields": [
            "WHATSAPP_ACCESS_TOKEN",
            "WHATSAPP_PHONE_NUMBER_ID",
        ],
    }


def send_text(phone: str, body: str) -> SendResult:
    settings = get_settings()
    if not phone.strip():
        return SendResult(False, False, "skipped", "No phone number on the recipient.")
    if not settings.whatsapp_configured():
        return SendResult(
            attempted=False,
            sent=False,
            status="not_configured",
            detail="WhatsApp credentials missing. Message was NOT sent.",
        )

    url = f"https://graph.facebook.com/v21.0/{settings.whatsapp_phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": phone.strip().lstrip("+"),
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=20)
    except httpx.HTTPError as exc:
        return SendResult(True, False, "failed", f"Network error talking to WhatsApp API: {exc}")

    if response.status_code >= 400:
        return SendResult(
            True,
            False,
            "failed",
            f"WhatsApp API rejected the request ({response.status_code}): {response.text[:500]}",
        )
    data = response.json()
    message_id = ""
    messages = data.get("messages") or []
    if messages:
        message_id = str(messages[0].get("id") or "")
    return SendResult(True, True, "sent", "WhatsApp API accepted the message.", message_id)
