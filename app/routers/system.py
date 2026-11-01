from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.config import ROOT_DIR, get_settings
from app.database import get_db
from app.scheduler import get_scheduler
from app.schemas import AutomationStatus, IntegrationStatus
from app.models import Member
from app.services.ai_chat import ai_status
from app.services.flat_chat import process_incoming_group_message
from app.services.jobs import job_chef_calls, job_generate_weekly_menu, job_grocery_reminders, recent_job_runs
from app.services.voice import voice_status
from app.services.whatsapp import send_text, whatsapp_status

router = APIRouter(prefix="/api", tags=["system"])


def _integrations() -> list[IntegrationStatus]:
    return [
        IntegrationStatus(**ai_status()),
        IntegrationStatus(**whatsapp_status()),
        IntegrationStatus(**voice_status()),
    ]


@router.get("/integrations", response_model=list[IntegrationStatus])
def integrations():
    return _integrations()


@router.get("/automation", response_model=AutomationStatus)
def automation(db: Session = Depends(get_db)):
    settings = get_settings()
    scheduler = get_scheduler()
    jobs = []
    running = bool(scheduler and scheduler.running)
    if scheduler:
        for job in scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                }
            )
    return AutomationStatus(
        timezone=settings.timezone,
        scheduler_running=running,
        jobs=jobs,
        recent_runs=recent_job_runs(db),
        integrations=_integrations(),
    )


@router.post("/automation/run/{job_name}")
def run_job(job_name: str, db: Session = Depends(get_db)):
    mapping = {
        "weekly_menu": lambda: job_generate_weekly_menu(db, force=True),
        "grocery_reminders": lambda: job_grocery_reminders(db),
        "chef_calls": lambda: job_chef_calls(db),
    }
    fn = mapping.get(job_name)
    if fn is None:
        raise HTTPException(404, "Unknown job")
    return {"job": job_name, "result": fn()}


@router.post("/auth/verify")
def verify_passcode(payload: dict):
    settings = get_settings()
    expected = settings.flat_passcode.strip()
    if not expected:
        return {"ok": True, "required": False}
    entered = str(payload.get("passcode", "")).strip()
    return {"ok": entered == expected, "required": True}


@router.get("/settings/env")
def env_status():
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "timezone": settings.timezone,
        "flat_passcode": settings.flat_passcode,
        # Gemini (primary)
        "gemini_model": settings.gemini_model,
        "gemini_api_key_set": settings.gemini_configured(),
        # OpenAI (legacy)
        "openai_model": settings.openai_model,
        "openai_api_key_set": settings.openai_configured(),
        # Other integrations
        "whatsapp_set": settings.whatsapp_configured(),
        "voice_set": settings.voice_configured(),
        "twilio_set": settings.twilio_configured(),
        "exotel_set": settings.exotel_configured(),
        "whatsapp_phone_number_id": settings.whatsapp_phone_number_id,
        "twilio_phone_number": settings.twilio_phone_number,
        "exotel_sid": settings.exotel_sid,
        "exotel_caller_id": settings.exotel_caller_id,
        "exotel_app_id_set": bool(settings.exotel_app_id.strip()),
    }


@router.post("/settings/env")
def write_env(payload: dict):
    allowed = {
        # Flat auth
        "FLAT_PASSCODE",
        # Gemini
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        # OpenAI (legacy)
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        # WhatsApp
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_BUSINESS_ACCOUNT_ID",
        "WHATSAPP_VERIFY_TOKEN",
        # Twilio Voice
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_PHONE_NUMBER",
        # Exotel
        "EXOTEL_SID",
        "EXOTEL_API_KEY",
        "EXOTEL_API_TOKEN",
        "EXOTEL_SUBDOMAIN",
        "EXOTEL_CALLER_ID",
        "EXOTEL_APP_ID",
        "EXOTEL_STATUS_CALLBACK_URL",
    }
    env_path = ROOT_DIR / ".env"
    current: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.strip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            current[key.strip()] = value
    for key, value in payload.items():
        if key in allowed and value is not None:
            current[key] = str(value).strip()
    lines = [f"{key}={current[key]}" for key in current]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    get_settings.cache_clear()
    return {"ok": True, "restart_needed": True, "integrations": _integrations()}


@router.get("/webhooks/whatsapp")
def verify_whatsapp(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
):
    settings = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return int(hub_challenge or 0)
    raise HTTPException(403, "Verification token mismatch")


def _handle_flatmate_inbound(db: Session, sender_phone: str, text: str) -> str:
    """Process incoming WhatsApp message from a flatmate and broadcast the update."""
    clean_sender = sender_phone.replace("+", "").strip()
    last_10 = clean_sender[-10:] if len(clean_sender) >= 10 else clean_sender

    # Find which flatmate sent this
    members = db.query(Member).filter(Member.is_cook == False).all()
    sender_member = None
    for m in members:
        p = (m.whatsapp_phone or m.phone or "").replace("+", "").strip()
        if p.endswith(last_10):
            sender_member = m
            break

    sender_name = sender_member.name if sender_member else "Flatmate"

    # Process message through the meal decision state machine
    reply = process_incoming_group_message(db, text, sender_name)
    if reply and not get_settings().twilio_configured():
        send_text(sender_phone, reply)

    # If the message made a decisive change (like locking or choosing a dish), notify other flatmates
    text_lower = text.lower()
    if any(w in text_lower for w in ["yes", "lock", "ordered", "option", "change to", "done"]):
        broadcast_text = f"📢 *Kitchen Bot Update:*\n{sender_name}: \"{text}\"\n\n🤖 {reply}"
        for m in members:
            p = (m.whatsapp_phone or m.phone or "").replace("+", "").strip()
            if p and not p.endswith(last_10) and m.notify:
                send_text(p, broadcast_text)

    return reply


@router.post("/webhooks/whatsapp")
@router.post("/webhooks/whatsapp/")
@router.post("/webh")
@router.post("/webh/")
async def inbound_whatsapp(request: Request, db: Session = Depends(get_db)):
    content_type = request.headers.get("content-type", "")

    # 1. Twilio Inbound Webhook (form-urlencoded)
    if "form" in content_type:
        form = await request.form()
        sender = form.get("From", "")
        body_text = form.get("Body", "")
        clean_sender = sender.replace("whatsapp:", "").strip()
        if clean_sender and body_text:
            reply = _handle_flatmate_inbound(db, clean_sender, body_text)
            if reply:
                safe_reply = reply.replace("]]>", "]] >")
                twiml = (
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<Response>\n'
                    f'    <Message><Body><![CDATA[{safe_reply}]]></Body></Message>\n'
                    '</Response>'
                )
                return Response(content=twiml, media_type="text/xml; charset=utf-8")
        return Response(content='<?xml version="1.0" encoding="UTF-8"?><Response/>', media_type="text/xml; charset=utf-8")

    # 2. Meta Inbound Webhook (JSON)
    try:
        body = await request.json()
    except Exception:
        return {"ok": False, "error": "Invalid JSON"}

    try:
        entries = body.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                val = change.get("value", {})
                messages = val.get("messages", [])
                for msg in messages:
                    sender_phone = msg.get("from", "").strip()
                    if msg.get("type") == "text":
                        text = msg.get("text", {}).get("body", "").strip()
                        if sender_phone and text:
                            _handle_flatmate_inbound(db, sender_phone, text)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    return {"ok": True, "received": True}
