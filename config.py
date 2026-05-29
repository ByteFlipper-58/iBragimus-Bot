from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    BOT_TOKEN: str = Field(..., description="Telegram Bot token from @BotFather")
    ADMIN_ID: int = Field(..., description="Telegram User ID of the bot administrator")

    AI_PROVIDER: str = Field(default="google", description="AI provider: openai, anthropic, or google")

    OPENAI_API_KEY: str | None = Field(default=None, description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4.1-mini", description="OpenAI model used for AI replies")

    ANTHROPIC_API_KEY: str | None = Field(default=None, description="Anthropic API key")
    ANTHROPIC_MODEL: str = Field(default="claude-sonnet-4-20250514", description="Anthropic model used for AI replies")

    GEMINI_API_KEY: str | None = Field(default=None, description="Google Gemini API key")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash", description="Gemini model used for AI replies")

    LOG_LEVEL: str = Field(default="INFO", description="Standard logging level")

    DB_BACKEND: str = Field(
        default="sqlite",
        description="Database backend: 'sqlite' (default) or 'postgres'",
    )
    DB_PATH: str = Field(default="data.db", description="Path to the SQLite database file")
    DATABASE_URL: str | None = Field(
        default=None,
        description=(
            "Connection DSN for external databases. Required when DB_BACKEND=postgres. "
            "Format: postgresql://user:password@host:5432/dbname"
        ),
    )

    TELEGRAM_API_ID: int = Field(..., description="Telegram API ID for the connected account client")
    TELEGRAM_API_HASH: str = Field(..., description="Telegram API hash for the connected account client")

    @field_validator("BOT_TOKEN")
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        if not v or "YOUR_TELEGRAM_BOT_TOKEN" in v:
            raise ValueError("BOT_TOKEN must be set to a valid Telegram Bot token.")
        return v

    @field_validator("ADMIN_ID")
    @classmethod
    def validate_admin_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("ADMIN_ID must be a positive Telegram user ID.")
        return v

    @field_validator("AI_PROVIDER")
    @classmethod
    def validate_ai_provider(cls, v: str) -> str:
        provider = v.strip().lower()
        allowed = {"openai", "anthropic", "google", "gemini"}
        if provider not in allowed:
            raise ValueError(f"AI_PROVIDER must be one of: {', '.join(sorted(allowed))}.")
        return "google" if provider == "gemini" else provider

    @field_validator("TELEGRAM_API_HASH")
    @classmethod
    def validate_telegram_api_hash(cls, v: str) -> str:
        if not v or "YOUR_TELEGRAM_API_HASH" in v:
            raise ValueError("TELEGRAM_API_HASH must be set to a valid Telegram API hash.")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        level = v.upper()
        if level not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(sorted(allowed))}.")
        return level

    @field_validator("DB_BACKEND")
    @classmethod
    def validate_db_backend(cls, v: str) -> str:
        backend = v.strip().lower()
        allowed = {"sqlite", "postgres", "postgresql"}
        if backend not in allowed:
            raise ValueError(f"DB_BACKEND must be one of: {', '.join(sorted(allowed))}.")
        return "postgres" if backend == "postgresql" else backend

    @model_validator(mode="after")
    def validate_database_url(self) -> "Settings":
        if self.DB_BACKEND == "postgres":
            if not self.DATABASE_URL or not self.DATABASE_URL.strip():
                raise ValueError(
                    "DATABASE_URL must be set when DB_BACKEND=postgres "
                    "(e.g. postgresql://user:password@host:5432/dbname)."
                )
            dsn = self.DATABASE_URL.strip()
            if not (dsn.startswith("postgres://") or dsn.startswith("postgresql://")):
                raise ValueError(
                    "DATABASE_URL must start with 'postgres://' or 'postgresql://'."
                )
        return self

settings = Settings()
