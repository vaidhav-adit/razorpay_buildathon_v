"""
config.py
─────────
Central settings module. All configuration is read once at startup from the
.env file using pydantic-settings. Every other module should import from here
instead of calling os.getenv() directly — this keeps configuration in one place
and makes it easy to validate and document.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All application settings, loaded from environment variables or a .env file.
    Fields with defaults are optional; fields without defaults are required and
    will raise a validation error at startup if missing.
    """

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str  # Required — e.g. postgresql://user:pass@host:5432/dbname

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

    # ── LLM ───────────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""

    # ── Policy thresholds ────────────────────────────────────────────────────
    # Minimum bank name-match score (0-100) to pass auto-approval
    MIN_NAME_MATCH_SCORE: int = 85

    # Tell pydantic-settings to load from a .env file in the backend/ directory
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# Singleton instance — import this everywhere rather than re-instantiating
settings = Settings()
