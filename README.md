# Smart Kitchen AI

Household kitchen manager: weekly menus, grocery lists, WhatsApp reminders, and chef phone calls.

The first version runs fully on your computer with a FastAPI backend, Streamlit dashboard, and SQLite database. External services stay **disconnected until you add credentials**. The app will not mark a WhatsApp message as sent or a phone call as completed unless the provider actually accepted it.

## Run it

```powershell
cd C:\Users\shubh\OneDrive\Documents\Desktop\smartkitchenai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Then open:

- Dashboard: http://localhost:8501
- API docs: http://127.0.0.1:8000/docs

Keep `python run.py` running for Sunday menu generation, grocery reminders, and chef-call retries. Those jobs use **Asia/Kolkata** and live in the backend process, not in the browser tab.

## What works without any API keys

- English / Hinglish chat using a built-in parser (OpenAI optional)
- Weekly menu generation with weekday vs weekend meal slots
- Editing or deleting individual meals
- Grocery consolidation and household-size scaling
- Member management
- Automation job history
- Honest logs for WhatsApp and Exotel (`not_configured` means nothing went out)

## Credentials you will need later

Copy `.env.example` to `.env` or use the Settings page, then **restart** the app.

| Feature | Account | Environment variables |
| --- | --- | --- |
| Smarter chat | [OpenAI API](https://platform.openai.com) | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| Grocery WhatsApp | Meta WhatsApp Cloud API | `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` |
| Chef outbound calls | [Exotel](https://exotel.com) | `EXOTEL_SID`, `EXOTEL_API_KEY`, `EXOTEL_API_TOKEN`, `EXOTEL_CALLER_ID`, `EXOTEL_APP_ID` |

WhatsApp numbers must include country code without `+` (example: `9198xxxxxxxx`). Exotel needs a public callback URL for live call-status updates (`EXOTEL_STATUS_CALLBACK_URL` → `/webhooks/exotel`).

## Tests

```powershell
python -m pytest -q
```
