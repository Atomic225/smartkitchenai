from datetime import timedelta

from app.database import SessionLocal
from app.services.grocery import build_shopping_list
from app.services.menu import generate_weekly_menu, get_week
from app.services.ai_chat import TOOLS, _is_read_only_request, _tool_show_menu
from app.services.notify import send_grocery_reminders
from app.services.timeutil import today, week_bounds


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_integrations_are_honest_when_unconfigured(client):
    items = {row["name"]: row for row in client.get("/api/integrations").json()}
    # Gemini is now the primary AI provider name (when unconfigured it shows "AI Provider")
    ai_item = items.get("AI Provider") or items.get("Google Gemini AI") or items.get("OpenAI (legacy)")
    assert ai_item is not None, f"Expected an AI provider entry, got keys: {list(items.keys())}"
    assert ai_item["configured"] is False
    assert "GEMINI_API_KEY" in ai_item["detail"] or "parser" in ai_item["detail"].lower()

    assert items["WhatsApp Business Cloud API"]["configured"] is False
    assert "NOT sent" in items["WhatsApp Business Cloud API"]["detail"]
    assert items["Exotel Voice"]["configured"] is False
    assert "not configured" in items["Exotel Voice"]["detail"].lower()


def test_generate_menu_and_edit_meal(client):
    generated = client.post("/api/menus/generate").json()
    assert generated["items"]
    weekday_slots = {item["meal_slot"] for item in generated["items"] if item["meal_date"] == generated["week_start"]}
    assert "breakfast" in weekday_slots
    assert "dinner" in weekday_slots
    meal_date = generated["week_start"]
    updated = client.put(
        "/api/menus/items",
        json={"meal_date": meal_date, "meal_slot": "lunch", "custom_name": "Paneer Bhurji", "recipe_id": None},
    ).json()
    assert updated["dish_name"] == "Paneer Bhurji"
    deleted = client.delete("/api/menus/items", params={"meal_date": meal_date, "meal_slot": "lunch"})
    assert deleted.status_code == 200


def test_chat_hinglish_set_and_clarify(client):
    clarify = client.post("/api/chat", json={"message": "dinner change kar do"}).json()
    assert clarify["needs_clarification"] is True
    assert clarify["used_openai"] is False
    set_meal = client.post("/api/chat", json={"message": "Monday lunch ko rajma rakh do"}).json()
    assert set_meal["needs_clarification"] is False
    assert any(action["name"] == "set_meal" for action in set_meal["actions"])


def test_grocery_merges_and_scales(client):
    client.post("/api/menus/generate")
    listing = client.post("/api/grocery/rebuild").json()
    assert listing["items"]
    onion = [item for item in listing["items"] if item["name"].lower() == "onion"]
    assert len(onion) == 1
    assert onion[0]["quantity"] > 1
    rice = [item for item in listing["items"] if "rice" in item["name"].lower()]
    assert rice


def test_whatsapp_reminder_not_sent_without_credentials(client):
    db = SessionLocal()
    try:
        start, _ = week_bounds(today())
        generate_weekly_menu(db, start, source="test")
        listing = build_shopping_list(db, start)
        assert listing.items
        listing.items[0].needed_by = today() + timedelta(days=2)
        db.commit()
        rows = send_grocery_reminders(db, today())
        assert rows
        assert all(row.status == "not_configured" for row in rows)
        assert all(row.sent_at is None for row in rows)
        again = send_grocery_reminders(db, today())
        assert {row.id for row in again} == {row.id for row in rows}
    finally:
        db.close()


def test_chef_call_not_placed_without_exotel(client):
    scheduled = client.post("/api/chef-calls/schedule")
    assert scheduled.status_code == 200
    call_id = scheduled.json()["id"]
    ran = client.post(f"/api/chef-calls/{call_id}/run").json()
    assert ran["status"] == "not_configured"
    assert "NOT placed" in ran["error"]
    assert ran["provider_call_id"] == ""


def test_household_members_crud(client):
    created = client.post(
        "/api/members",
        json={"name": "Neha", "phone": "919800000009", "whatsapp_phone": "919800000009", "notify": True},
    ).json()
    assert created["name"] == "Neha"
    client.delete(f"/api/members/{created['id']}")
    names = [m["name"] for m in client.get("/api/members").json()]
    assert "Neha" not in names


def test_menu_exists_in_database(client):
    db = SessionLocal()
    try:
        assert get_week(db, today()) is not None
    finally:
        db.close()


def test_gemini_tool_schemas_are_non_empty_and_consistent():
    names = set()
    for tool in TOOLS:
        function = tool["function"]
        names.add(function["name"])
        parameters = function["parameters"]
        assert parameters["type"] == "object"
        assert parameters["properties"], f"{function['name']} has an empty parameter schema"
        required = parameters.get("required", [])
        assert set(required).issubset(parameters["properties"])
    assert names == {
        "generate_weekly_menu", "set_meal", "delete_meal", "delete_weekly_menu",
        "show_menu", "rebuild_grocery_list", "list_recipes", "add_household_member",
    }


def test_show_menu_without_date_reads_latest_full_week(client):
    generated = client.post("/api/menus/generate").json()
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        result = _tool_show_menu(db)
        assert result["ok"] is True
        assert result["week_start"] == generated["week_start"]
        assert len(result["meals"]) == len(generated["items"])
        assert {item["meal_date"] for item in result["meals"]}
    finally:
        db.close()


def test_explicit_read_only_instruction_is_detected():
    assert _is_read_only_request("Show me my weekly menu. Do not modify anything.")
    assert _is_read_only_request("Generate a draft but do not save until I approve.")
    assert not _is_read_only_request("Change Monday lunch to Rajma.")

def test_flat_passcode_auth(client):
    # Incorrect passcode
    bad = client.post("/api/auth/verify", json={"passcode": "wrongcode"}).json()
    assert bad["ok"] is False

    # Correct passcode
    good = client.post("/api/auth/verify", json={"passcode": "chakna302x"}).json()
    assert good["ok"] is True


def test_cook_calling_schedule_and_hindi_script(client):
    # Verify customizable timings in household
    put_res = client.put(
        "/api/household",
        json={
            "chef_call_weekday_time": "08:15",
            "chef_call_weekend_lunch_time": "10:00",
            "chef_call_weekend_dinner_time": "17:30",
        },
    )
    assert put_res.status_code == 200
    data = put_res.json()
    assert data["chef_call_weekday_time"] == "08:15"
    assert data["chef_call_weekend_lunch_time"] == "10:00"
    assert data["chef_call_weekend_dinner_time"] == "17:30"

    # Verify preview scripts endpoint
    preview = client.get("/api/chef-calls/preview").json()
    assert "scripts" in preview
    assert "weekday" in preview["scripts"]
    assert "weekend_lunch" in preview["scripts"]
    assert "weekend_dinner" in preview["scripts"]
    assert "Namaste" in preview["scripts"]["weekday"]
    assert "Namaste" in preview["scripts"]["weekend_lunch"]
    assert "Namaste" in preview["scripts"]["weekend_dinner"]
    assert "Dhanyawad" in preview["scripts"]["weekday"]
