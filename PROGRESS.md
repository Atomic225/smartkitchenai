# Smart Kitchen AI — Development Progress

> Last updated: 2026-10-31 | Agent: Antigravity

---

## Project Architecture

`
smartkitchenai/
├── app/                     ← FastAPI backend (Python)
│   ├── main.py              ← FastAPI app, CORS, lifespan
│   ├── config.py            ← Settings via pydantic-settings / .env
│   ├── database.py          ← SQLAlchemy SQLite engine
│   ├── models.py            ← ORM models (10 tables)
│   ├── schemas.py           ← Pydantic request/response schemas
│   ├── scheduler.py         ← APScheduler background jobs
│   ├── seed.py              ← 20 Indian recipes + demo household
│   ├── routers/             ← API route handlers
│   │   ├── chat.py          ← POST /api/chat, GET /api/chat/history
│   │   ├── menus.py         ← CRUD menus + calendar + recipes
│   │   ├── grocery.py       ← Shopping list + notifications
│   │   ├── household.py     ← Household & member management
│   │   ├── chef.py          ← Chef call scheduling & webhook
│   │   └── system.py        ← Integrations, automation, settings, webhooks
│   └── services/
│       ├── ai_chat.py       ← Gemini function-calling + offline Hinglish parser
│       ├── menu.py          ← Weekly menu generation logic
│       ├── grocery.py       ← Shopping list builder + reminder formatter
│       ├── notify.py        ← WhatsApp notification dispatch + idempotency
│       ├── chef.py          ← Chef call scripts (Hinglish) + Exotel dispatch
│       ├── whatsapp.py      ← Meta WhatsApp Cloud API integration
│       ├── exotel.py        ← Exotel outbound voice call integration
│       ├── household.py     ← Household/member CRUD
│       ├── jobs.py          ← Scheduled job logic (weekly menu, reminders, calls)
│       └── timeutil.py      ← IST timezone helpers
├── frontend/                ← Streamlit dashboard (Python)
│   ├── streamlit_app.py     ← Home page: chat + today at a glance
│   ├── api.py               ← HTTP client for backend API
│   ├── ui.py                ← Shared theme + integration status bar
│   └── pages/
│       ├── 1_Weekly_Menu.py ← Full week calendar editor
│       ├── 2_Grocery.py     ← Shopping list viewer + mark purchased
│       ├── 3_Household.py   ← Add/edit members & settings
│       ├── 4_Chef_Calls.py  ← Chef call log + manual trigger
│       ├── 5_Automation.py  ← Scheduler status + manual job runs
│       └── 6_Settings.py    ← API key entry form (Gemini primary)
├── tests/
│   ├── conftest.py
│   └── test_app.py
├── Dockerfile               ← Container build for free cloud hosting
├── .dockerignore
├── run.py                   ← Launcher: starts API + Streamlit together (with PORT support)
├── requirements.txt
├── .env.example
└── .venv/                   ← Python virtual environment (already installed)
`

---

## Feature Status

| Feature | Status | Notes |
|---|---|---|
| FastAPI backend | ✅ Complete | All routes working, clean imports |
| SQLite database + ORM | ✅ Complete | 10 tables, auto-created on startup |
| 20 Indian recipes (seed data) | ✅ Complete | With Hindi names + shopping ingredients |
| Weekly menu generation | ✅ Complete | Weekday/weekend rotation, auto on Sunday 6 pm |
| Grocery list builder | ✅ Complete | Scales ingredients by household size |
| **AI chatbot (Gemini)** | ✅ Complete | **Google Gemini via OpenAI-compatible endpoint; function-calling with 8 tools; English + Hinglish** |
| Offline Hinglish parser | ✅ Complete | Works without any API key (fallback) |
| WhatsApp notification | ✅ Complete | Real Meta Cloud API; gracefully mocks if unconfigured |
| Exotel chef calls | ✅ Complete | Outbound call placed; Hinglish script generated |
| APScheduler automation | ✅ Complete | Menu on Sunday, reminders hourly, calls every 10 min |
| Streamlit dashboard | ✅ Complete | 7 pages (home + 6 sub-pages) |
| Member management UI | ✅ Complete | Add/edit/delete members with phone numbers |
| Settings UI (API keys) | ✅ Complete | Gemini key entry; writes to .env file, live reload |
| Webhook: WhatsApp verify | ✅ Complete | GET /api/webhooks/whatsapp |
| Webhook: Exotel callback | ✅ Complete | POST /webhooks/exotel |
| Job history logging | ✅ Complete | Idempotency keys prevent duplicate sends |
| All 9 tests passing | ✅ Verified | pytest 9 passed, 0 failed |

---

## Bugs Fixed

### 2026-10-31 (Session 1)
1. **rontend/ui.py import error** — rom frontend.api import ApiError, get would fail at runtime because Streamlit adds rontend/ to sys.path, so pi is directly importable. Fixed to rom api import ApiError, get.

2. **Chat message JSON serialization crash** — When the AI chat sets a meal, the action result includes meal_date as a Python date object. SQLAlchemy's JSON column cannot serialize date objects, causing a TypeError crash when saving the intent. Fixed by adding _json_safe() helper in i_chat.py that converts all date/datetime objects to ISO strings before saving. All 9 tests now pass.

### 2026-10-31 (Session 2 — Gemini migration + model correction)
3. **OpenAI → Gemini migration** — Replaced _openai_handle with _gemini_handle in i_chat.py. Gemini is now the primary AI provider using Google's OpenAI-compatible REST endpoint (https://generativelanguage.googleapis.com/v1beta/openai/). The existing openai Python SDK is reused with a custom ase_url. Full tool-calling preserved for all 8 kitchen functions. Legacy OpenAI key path kept as fallback. Offline Hinglish parser retained as second fallback.

4. **IntegrationStatus.required_fields missing** — The i_status() function was missing the 
equired_fields field required by the Pydantic schema. Fixed by adding "required_fields": ["GEMINI_API_KEY"] to all return paths.

5. **Settings page updated** — 6_Settings.py now shows Gemini as the primary AI provider with a direct link to Google AI Studio. OpenAI section moved into a collapsed expander.

---

## Credentials Needed (from you)

The app runs fully in mock/offline mode without any keys. To enable real integrations:

| Credential | Service | Where to enter |
|---|---|---|
| GEMINI_API_KEY | **Google Gemini AI (primary chatbot)** | Dashboard → Settings page, or .env file |
| GEMINI_MODEL | Gemini model name | .env (default: gemini-3.5-flash-lite) |
| WHATSAPP_ACCESS_TOKEN | Meta WhatsApp Cloud API | Dashboard → Settings page, or .env file |
| WHATSAPP_PHONE_NUMBER_ID | Meta WhatsApp Cloud API | Dashboard → Settings page, or .env file |
| EXOTEL_SID | Exotel voice calls to cook | Dashboard → Settings page, or .env file |
| EXOTEL_API_KEY | Exotel voice calls to cook | Dashboard → Settings page, or .env file |
| EXOTEL_API_TOKEN | Exotel voice calls to cook | Dashboard → Settings page, or .env file |
| EXOTEL_CALLER_ID | Exotel voice calls to cook | Dashboard → Settings page, or .env file |
| EXOTEL_APP_ID | Exotel ExoML (menu playback) | Dashboard → Settings page, or .env file |

**Get a free Gemini API key at:** https://aistudio.google.com/app/apikey

---

## How to Run

`powershell
# From the project folder:
cd "C:\Users\shubh\OneDrive\Documents\Desktop\smartkitchenai"
.venv\Scripts\python.exe run.py
`

- API: http://127.0.0.1:8000
- Dashboard: http://localhost:8501
- API docs: http://127.0.0.1:8000/docs

### Adding your Gemini key (one-time setup)

**Option A — Settings page (recommended)**
1. Launch the app with 
un.py
2. Open http://localhost:8501 → sidebar → Settings
3. Paste your GEMINI_API_KEY and click **Save credentials to .env**
4. Restart 
un.py

**Option B — Edit .env directly**
Add this line to the .env file in the project root:
`
GEMINI_API_KEY=AIza...your-key-here...
`
Then restart 
un.py.

---

## AI Provider Priority

`
1. Google Gemini (GEMINI_API_KEY set)       → Full natural language + tool-calling
2. OpenAI legacy  (OPENAI_API_KEY set)      → Full natural language + tool-calling
3. Offline parser (no key)                  → Keyword-based Hinglish/English commands
`

All three paths produce structured tool-call results (set_meal, generate_weekly_menu, etc.).

---

## Automation Schedule (When Running 24/7)

| Job | Schedule | What it does |
|---|---|---|
| Weekly menu | Every Sunday at 6:00 PM IST | Generates next week's meal plan + grocery list |
| Grocery reminders | Every hour at :10 | Sends WhatsApp to all 
otify=True members when shopping is due (configurable: 2 or 3 days before meal date) |
| Chef calls | Every 10 minutes | Places Exotel outbound call to cook at configured time (default 7:00 AM IST), retries up to 3× |

---

## Next Tasks (Backlog)

### High Priority
- [ ] **Add GEMINI_API_KEY** — Get free key at https://aistudio.google.com/app/apikey and add via Settings page
- [ ] **Cloud deployment** — Host on Railway / Render / Google Cloud Run so it runs 24/7 without needing your computer on
- [ ] **WhatsApp message templates** — Meta requires pre-approved templates for business-initiated messages; current free-text works only for 24-hour reply window
- [ ] **Real household data setup** — Replace demo "Sharma Household" data with your actual family members and phone numbers (via UI)

### Medium Priority
- [ ] **Add more recipes** — Expand the seed recipe list with your household's preferred dishes via the chatbot
- [ ] **Inbound WhatsApp chat** — Parse incoming WhatsApp replies to update menu/confirm orders
- [ ] **Exotel ExoML script** — Create actual ExoML app on Exotel console that reads the menu aloud (TTS)
- [ ] **Push notifications test** — End-to-end test with real WhatsApp credentials

### Low Priority
- [ ] **Docker / docker-compose** — Containerize for easier cloud deploy
- [ ] **Recipe image upload** — Visual menu cards
- [ ] **Multi-household support** — Currently single household ID=1


## 2026-10-31 — Follow-up source review (ChatGPT)

Reviewed the source archive uploaded by the user. The actual Gemini 400 was not captured in server logs, so the precise HTTP response body is not known. Found and corrected a schema defect that can make the all-tools request invalid for Gemini: `rebuild_grocery_list` declared an empty `properties` object. It now accepts an optional `week_start` value and the handler uses the selected/latest saved menu week.

Also corrected the weekly menu read tool: `show_menu` without a date now returns the complete latest saved weekly menu; a supplied `meal_date` still returns one day. Updated agent instructions and added a server-side read-only guard so explicit preview/show/do-not-save requests cannot execute mutating tools. Destructive actions still require clear user intent. Fixed duplicate submission of the latest user message in Gemini chat history. Updated the test model from retired `gemini-2.0-flash` to `gemini-3.5-flash-lite` and improved fallback wording.

Added regression tests for non-empty Gemini tool schemas and retrieving all meals from the latest saved weekly menu. These changes have not yet been tested against the user's live API key; a real Gemini test is still required after applying the patch.


8. **Flat Passcode Lock Screen & Roommate Profile Switcher** — Secured all dashboard pages behind a shared flat passcode (`chakna302x`). Visitors are greeted with a clean lock screen. Once unlocked, an active flatmate selector appears in the sidebar to toggle between roommates (`Shubh`, `Aman`, etc.) with a 1-click "Lock Kitchen" sign-out button. Passcode can be re-configured on the Settings page anytime.
