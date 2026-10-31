from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class MemberIn(BaseModel):
    name: str
    role: str = "member"
    phone: str = ""
    whatsapp_phone: str = ""
    notify: bool = True
    is_cook: bool = False


class MemberOut(MemberIn):
    id: int
    household_id: int

    model_config = {"from_attributes": True}


class HouseholdOut(BaseModel):
    id: int
    name: str
    size: int
    timezone: str
    weekday_meals: list[str]
    weekend_meals: list[str]
    auto_weekly_menu: bool
    grocery_reminder_days: int
    chef_call_time: str
    chef_call_enabled: bool
    chef_language: str

    model_config = {"from_attributes": True}


class HouseholdUpdate(BaseModel):
    name: str | None = None
    size: int | None = None
    weekday_meals: list[str] | None = None
    weekend_meals: list[str] | None = None
    auto_weekly_menu: bool | None = None
    grocery_reminder_days: int | None = None
    chef_call_time: str | None = None
    chef_call_enabled: bool | None = None
    chef_language: str | None = None


class RecipeOut(BaseModel):
    id: int
    name: str
    name_hi: str
    cuisine: str
    meal_types: list[str]
    tags: list[str]
    base_servings: int
    ingredients: list[dict[str, Any]]
    instructions: str
    hindi_script: str

    model_config = {"from_attributes": True}


class MenuItemIn(BaseModel):
    meal_date: date
    meal_slot: str
    recipe_id: int | None = None
    custom_name: str = ""
    notes: str = ""
    servings: int | None = None


class MenuItemOut(BaseModel):
    id: int
    weekly_menu_id: int
    meal_date: date
    meal_slot: str
    recipe_id: int | None
    recipe_name: str = ""
    custom_name: str
    dish_name: str = ""
    notes: str
    servings: int

    model_config = {"from_attributes": True}


class WeeklyMenuOut(BaseModel):
    id: int
    week_start: date
    week_end: date
    status: str
    source: str
    notes: str
    items: list[MenuItemOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    needs_clarification: bool = False
    actions: list[dict[str, Any]] = Field(default_factory=list)
    used_openai: bool = False


class ShoppingItemOut(BaseModel):
    id: int
    name: str
    quantity: float
    unit: str
    category: str
    needed_by: date | None
    purchased: bool

    model_config = {"from_attributes": True}


class ShoppingListOut(BaseModel):
    id: int
    weekly_menu_id: int | None
    status: str
    items: list[ShoppingItemOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class NotificationOut(BaseModel):
    id: int
    channel: str
    recipient_name: str
    recipient_phone: str
    body: str
    scheduled_for: datetime | None
    sent_at: datetime | None
    status: str
    error: str
    provider_id: str
    idempotency_key: str

    model_config = {"from_attributes": True}


class ChefCallOut(BaseModel):
    id: int
    menu_date: date
    cook_name: str
    cook_phone: str
    script: str
    scheduled_for: datetime | None
    status: str
    response_text: str
    attempts: int
    max_attempts: int
    provider_call_id: str
    error: str

    model_config = {"from_attributes": True}


class IntegrationStatus(BaseModel):
    name: str
    configured: bool
    mode: str
    detail: str
    required_fields: list[str]


class AutomationStatus(BaseModel):
    timezone: str
    scheduler_running: bool
    jobs: list[dict[str, Any]]
    recent_runs: list[dict[str, Any]]
    integrations: list[IntegrationStatus]
