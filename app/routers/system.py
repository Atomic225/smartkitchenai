from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.config import ROOT_DIR, get_settings
from app.database import get_db
from app.scheduler import get_scheduler
from app.schemas import AutomationStatus, IntegrationStatus
from app.services.ai_chat import ai_status  # previously openai_status
from app.services.exotel import exotel_status
from app.services.jobs import job_chef_calls, job_generate_weekly_menu, job_grocery_reminders, recent_job_runs
from app.services.whatsapp import whatsapp_status

router = APIRouter(prefix="/api", tags=["system"])


def _integrations() -> list[IntegrationStatus]:
    return [
        IntegrationStatus(**ai_status()),
        IntegrationStatus(**whatsapp_status()),
        IntegrationStatus(**exotel_status()),
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


@router.get("/settings/env")
def env_status():
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "timezone": settings.timezone,
        # Gemini (primary)
        "gemini_model": settings.gemini_model,
        "gemini_api_key_set": settings.gemini_configured(),
        # OpenAI (legacy)
        "openai_model": settings.openai_model,
        "openai_api_key_set": settings.openai_configured(),
        # Other integrations
        "whatsapp_set": settings.whatsapp_configured(),
        "exotel_set": settings.exotel_configured(),
        "whatsapp_phone_number_id": settings.whatsapp_phone_number_id,
        "exotel_sid": settings.exotel_sid,
        "exotel_caller_id": settings.exotel_caller_id,
        "exotel_app_id_set": bool(settings.exotel_app_id.strip()),
    }


@router.post("/settings/env")
def write_env(payload: dict):
    allowed = {
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


@router.post("/webhooks/whatsapp")
async def inbound_whatsapp(request: Request):
    body = await request.json()
    return {"ok": True, "received": True, "keys": list(body.keys())}
