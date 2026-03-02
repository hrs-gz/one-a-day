from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = "sqlite:///./oad.db"
    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"
    scrape_rate_limit_seconds: float = 2.0
    scraper_user_agent: str = "OneADay/1.0 (+https://yoursite.com/bot-info)"
    openai_api_key: str | None = None
    openrouter_api_key: str | None = None
    openrouter_model: str = "mistralai/mistral-small-3.1-24b-instruct:free"
    sentry_dsn: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
