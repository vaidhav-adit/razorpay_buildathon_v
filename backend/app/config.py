"""
config.py
─────────
Central settings module. All configuration is read once at startup from the
.env file using pydantic-settings. Every other module should import from here
instead of calling os.getenv() directly — this keeps configuration in one place
and makes it easy to validate and document.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Dynamically locate the .env file in the backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """
    All application settings, loaded from environment variables or a .env file.
    Fields with defaults are optional; fields without defaults are required.
    """

    # ── Database ─────────────────────────────────────────────────────────────
    # Default fallback provided so modules/tests can load even before .env is populated
    DATABASE_URL: str = "postgresql://localhost:5432/razorpay_agent"

    # ── App ───────────────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # ── Razorpay ──────────────────────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # ── Zoho Books ────────────────────────────────────────────────────────────
    ZOHO_CLIENT_ID: str = ""
    ZOHO_CLIENT_SECRET: str = ""
    ZOHO_REDIRECT_URI: str = ""
    ZOHO_ORGANIZATION_ID: str = ""
    ZOHO_REFRESH_TOKEN: str = ""
    ZOHO_BASE_URL: str = "https://books.zoho.in/api/v3"
    ZOHO_ACCOUNTS_URL: str = "https://accounts.zoho.in/oauth/v2/token"

    # ── LLM ───────────────────────────────────────────────────────────────────
    LLM_PROVIDER: str = "gemini"  # "gemini", "openai", or "mock"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # ── Policy thresholds ────────────────────────────────────────────────────
    # Minimum bank name-match score (0-100) to pass auto-approval
    MIN_NAME_MATCH_SCORE: int = 85

    # Look for .env in current working dir, backend/, and absolute file path
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", str(ENV_PATH)),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Singleton instance — import this everywhere rather than re-instantiating
settings = Settings()
