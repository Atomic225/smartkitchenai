from datetime import date, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Notification, ShoppingItem
from app.services.grocery import format_list_message, items_due_for_reminder
from app.services.household import get_household, notify_members
from app.services.timeutil import now_local, today
from app.services.whatsapp import send_text


def _record(
    db: Session,
    *,
    channel: str,
    name: str,
    phone: str,
    body: str,
    key: str,
    result_status: str,
    error: str,
    provider_id: str,
    sent: bool,
) -> Notification | None:
    now = now_local().replace(tzinfo=None)
    row = Notification(
        channel=channel,
        recipient_name=name,
        recipient_phone=phone,
        body=body,
        scheduled_for=now,
        sent_at=now if sent else None,
        status=result_status,
        error=error,
        provider_id=provider_id,
        idempotency_key=key,
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        return db.query(Notification).filter(Notification.idempotency_key == key).first()


def send_grocery_reminders(db: Session, day: date | None = None) -> list[Notification]:
    household = get_household(db)
    reminder_days = household.grocery_reminder_days if household.grocery_reminder_days in (2, 3) else 2
    day = day or today()
    items = items_due_for_reminder(db, day, reminder_days)
    if not items:
        return []
    needed_by = items[0].needed_by or day
    body = format_list_message(items, needed_by)
    created: list[Notification] = []
    for member in notify_members(db):
        phone = member.whatsapp_phone or member.phone
        key = f"whatsapp:{member.id}:{needed_by.isoformat()}:d{reminder_days}"
        existing = db.query(Notification).filter(Notification.idempotency_key == key).first()
        if existing:
            created.append(existing)
            continue
        result = send_text(phone, body)
        row = _record(
            db,
            channel="whatsapp",
            name=member.name,
            phone=phone,
            body=body,
            key=key,
            result_status=result.status if not result.sent else "sent",
            error="" if result.sent else result.detail,
            provider_id=result.provider_id,
            sent=result.sent,
        )
        if row:
            created.append(row)
    return created


def catch_up_pending_reminders(db: Session) -> list[Notification]:
    """If the app was closed on reminder day, try once for recently missed needed_by dates."""
    results: list[Notification] = []
    for offset in range(0, 4):
        results.extend(send_grocery_reminders(db, today() - timedelta(days=offset)))
    return results


def list_notifications(db: Session, limit: int = 50) -> list[Notification]:
    return db.query(Notification).order_by(Notification.id.desc()).limit(limit).all()


def shopping_item_ids(items: list[ShoppingItem]) -> list[int]:
    return [item.id for item in items]
