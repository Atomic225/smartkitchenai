import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
# Gemini (primary)
os.environ["GEMINI_API_KEY"] = ""
os.environ["GEMINI_MODEL"] = "gemini-3.5-flash-lite"
# OpenAI (legacy)
os.environ["OPENAI_API_KEY"] = ""
# Twilio
os.environ["TWILIO_ACCOUNT_SID"] = ""
os.environ["TWILIO_AUTH_TOKEN"] = ""
os.environ["TWILIO_PHONE_NUMBER"] = ""
# Other integrations
os.environ["WHATSAPP_ACCESS_TOKEN"] = ""
os.environ["WHATSAPP_PHONE_NUMBER_ID"] = ""
os.environ["EXOTEL_SID"] = ""
os.environ["EXOTEL_API_KEY"] = ""
os.environ["EXOTEL_API_TOKEN"] = ""
os.environ["EXOTEL_CALLER_ID"] = ""

from app.config import get_settings

get_settings.cache_clear()

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
