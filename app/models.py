from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class Household(Base):
    __tablename__ = "households"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="My Kitchen")
    size: Mapped[int] = mapped_column(Integer, default=4)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    weekday_meals: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["breakfast", "lunch", "dinner"])
    weekend_meals: Mapped[list[str]] = mapped_column(
        JSON, default=lambda: ["breakfast", "lunch", "evening_snack", "dinner"]
    )
    auto_weekly_menu: Mapped[bool] = mapped_column(Boolean, default=True)
    grocery_reminder_days: Mapped[int] = mapped_column(Integer, default=2)
    chef_call_time: Mapped[str] = mapped_column(String(8), default="07:00")
    chef_call_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    chef_language: Mapped[str] = mapped_column(String(20), default="hinglish")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    members: Mapped[list["Member"]] = relationship(back_populates="household", cascade="all, delete-orphan")


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"), default=1)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(40), default="member")
    phone: Mapped[str] = mapped_column(String(20), default="")
    whatsapp_phone: Mapped[str] = mapped_column(String(20), default="")
    notify: Mapped[bool] = mapped_column(Boolean, default=True)
    is_cook: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    household: Mapped[Household] = relationship(back_populates="members")


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    name_hi: Mapped[str] = mapped_column(String(160), default="")
    cuisine: Mapped[str] = mapped_column(String(80), default="Indian")
    meal_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    base_servings: Mapped[int] = mapped_column(Integer, default=4)
    ingredients: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    instructions: Mapped[str] = mapped_column(Text, default="")
    hindi_script: Mapped[str] = mapped_column(Text, default="")


class WeeklyMenu(Base):
    __tablename__ = "weekly_menus"
    __table_args__ = (UniqueConstraint("week_start", name="uq_week_start"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    week_end: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="draft")
    source: Mapped[str] = mapped_column(String(40), default="manual")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    items: Mapped[list["MenuItem"]] = relationship(back_populates="weekly_menu", cascade="all, delete-orphan")


class MenuItem(Base):
    __tablename__ = "menu_items"
    __table_args__ = (UniqueConstraint("weekly_menu_id", "meal_date", "meal_slot", name="uq_menu_slot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    weekly_menu_id: Mapped[int] = mapped_column(ForeignKey("weekly_menus.id"))
    meal_date: Mapped[date] = mapped_column(Date, index=True)
    meal_slot: Mapped[str] = mapped_column(String(40))
    recipe_id: Mapped[int | None] = mapped_column(ForeignKey("recipes.id"), nullable=True)
    custom_name: Mapped[str] = mapped_column(String(160), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    servings: Mapped[int] = mapped_column(Integer, default=4)

    weekly_menu: Mapped[WeeklyMenu] = relationship(back_populates="items")
    recipe: Mapped[Recipe | None] = relationship()


class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    weekly_menu_id: Mapped[int | None] = mapped_column(ForeignKey("weekly_menus.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    items: Mapped[list["ShoppingItem"]] = relationship(back_populates="shopping_list", cascade="all, delete-orphan")


class ShoppingItem(Base):
    __tablename__ = "shopping_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shopping_list_id: Mapped[int] = mapped_column(ForeignKey("shopping_lists.id"))
    name: Mapped[str] = mapped_column(String(160))
    quantity: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(40), default="")
    category: Mapped[str] = mapped_column(String(80), default="other")
    needed_by: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchased: Mapped[bool] = mapped_column(Boolean, default=False)

    shopping_list: Mapped[ShoppingList] = relationship(back_populates="items")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_notification_idempotency"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel: Mapped[str] = mapped_column(String(40))
    recipient_name: Mapped[str] = mapped_column(String(120), default="")
    recipient_phone: Mapped[str] = mapped_column(String(20), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="pending")
    error: Mapped[str] = mapped_column(Text, default="")
    provider_id: Mapped[str] = mapped_column(String(120), default="")
    idempotency_key: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ChefCall(Base):
    __tablename__ = "chef_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    menu_date: Mapped[date] = mapped_column(Date, index=True)
    cook_name: Mapped[str] = mapped_column(String(120), default="")
    cook_phone: Mapped[str] = mapped_column(String(20), default="")
    script: Mapped[str] = mapped_column(Text, default="")
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="scheduled")
    response_text: Mapped[str] = mapped_column(Text, default="")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    provider_call_id: Mapped[str] = mapped_column(String(120), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    intent: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class JobRun(Base):
    __tablename__ = "job_runs"
    __table_args__ = (UniqueConstraint("job_name", "run_key", name="uq_job_run"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_name: Mapped[str] = mapped_column(String(80))
    run_key: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="success")
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
