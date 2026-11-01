from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Smart Kitchen AI"
    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    frontend_origin: str = "http://localhost:8501"
    database_url: str = "sqlite:///./data/smartkitchen.db"
    timezone: str = "Asia/Kolkata"
    flat_passcode: str = "chakna302x"

    # ---------- Gemini (primary AI provider) ----------
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"

    # ---------- OpenAI (kept for backward compatibility; Gemini takes priority) ----------
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # ---------- WhatsApp ----------
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_business_account_id: str = ""
    whatsapp_verify_token: str = "smartkitchen-verify"

    # ---------- Twilio Voice (Primary Cook Calling) ----------
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    twilio_voice: str = "Polly.Aditi"
    twilio_language: str = "hi-IN"

    # ---------- Exotel (Alternative Indian Telephony) ----------
    exotel_sid: str = ""
    exotel_api_key: str = ""
    exotel_api_token: str = ""
    exotel_subdomain: str = "api.exotel.com"
    exotel_caller_id: str = ""
    exotel_app_id: str = ""
    exotel_status_callback_url: str = ""

    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key.strip())

    def openai_configured(self) -> bool:
        """Legacy helper; Gemini is now the primary provider."""
        return bool(self.openai_api_key.strip())

    def ai_configured(self) -> bool:
        """True when ANY AI provider key is present."""
        return self.gemini_configured() or self.openai_configured()

    def whatsapp_configured(self) -> bool:
        return bool(self.whatsapp_access_token.strip() and self.whatsapp_phone_number_id.strip())

    def twilio_configured(self) -> bool:
        return bool(
            self.twilio_account_sid.strip()
            and self.twilio_auth_token.strip()
            and self.twilio_phone_number.strip()
        )

    def exotel_configured(self) -> bool:
        return bool(
            self.exotel_sid.strip()
            and self.exotel_api_key.strip()
            and self.exotel_api_token.strip()
            and self.exotel_caller_id.strip()
        )

    def voice_configured(self) -> bool:
        return self.twilio_configured() or self.exotel_configured()


@lru_cache
def get_settings() -> Settings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()
