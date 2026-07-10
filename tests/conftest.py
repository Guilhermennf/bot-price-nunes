"""Shared test setup: settings isolation + recorded-fixture helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.config import get_settings

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    """Every test gets deterministic settings regardless of the repo .env.

    get_settings() is lru_cached — clear before AND after so no test leaks
    its configuration into the next.
    """
    for key in (
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "SUPABASE_URL",
        "SUPABASE_KEY", "GEMINI_API_KEY", "SENTRY_DSN",
    ):
        monkeypatch.setenv(key, "")
    monkeypatch.setenv("TECH_ONLY", "true")
    monkeypatch.setenv(
        "ALLOWED_STORES", "amazon,mercadolivre,aliexpress,shopee,magalu"
    )
    monkeypatch.setenv("AMAZON_ASSOC_TAG", "")
    monkeypatch.setenv("ML_AFFILIATE_TOOL_ID", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class FakeResponse:
    def __init__(self, text: str = "", url: str = "", json_data=None, status: int = 200):
        self.text = text
        self.url = url
        self._json = json_data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


@pytest.fixture
def promobit_html() -> str:
    """The recorded __NEXT_DATA__ payload re-wrapped as a minimal page."""
    payload = (FIXTURES / "promobit_next_data.json").read_text(encoding="utf-8")
    return f'<html><body><script id="__NEXT_DATA__" type="application/json">{payload}</script></body></html>'


@pytest.fixture
def pelando_payload() -> dict:
    return json.loads((FIXTURES / "pelando_feed.json").read_text(encoding="utf-8"))
