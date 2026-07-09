"""Environment-backed settings. Loads a local .env if present."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"

    # Feature flags / tuning
    enable_checkout_sim: bool = False
    min_score: int = 70
    min_discount_pct: float = 10.0
    history_window_days: int = 90
    repost_cooldown_days: int = 7
    max_deals_per_run: int = 15

    # Scraper politeness
    request_timeout: float = 20.0
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
