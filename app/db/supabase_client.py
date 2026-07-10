"""Supabase access: price-history series + posted-deal dedupe.

All pipeline state lives here so the cron run itself stays stateless.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from supabase import Client, create_client

from app.config import get_settings


@dataclass
class PriceStats:
    count: int
    minimum: float | None
    median: float | None


_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        s = get_settings()
        if not s.supabase_url or not s.supabase_key:
            raise RuntimeError("SUPABASE_URL / SUPABASE_KEY not configured")
        _client = create_client(s.supabase_url, s.supabase_key)
    return _client


def _iso_days_ago(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


def record_price(product_key: str, price: float) -> None:
    """Append one observation to the price series for a product."""
    get_client().table("price_history").insert(
        {"product_key": product_key, "price": price}
    ).execute()


def get_price_stats(product_key: str, window_days: int) -> PriceStats:
    """Min + median of a product's prices within the trailing window."""
    resp = (
        get_client()
        .table("price_history")
        .select("price")
        .eq("product_key", product_key)
        .gte("captured_at", _iso_days_ago(window_days))
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    prices = [float(row["price"]) for row in rows if row.get("price") is not None]
    if not prices:
        return PriceStats(count=0, minimum=None, median=None)
    return PriceStats(count=len(prices), minimum=min(prices), median=statistics.median(prices))


def was_recently_posted(url_key: str, price: float, cooldown_days: int) -> bool:
    """True if this product was posted within the cooldown at a price <= now.

    Lets a genuinely-cheaper re-drop through while suppressing repeats.
    """
    resp = (
        get_client()
        .table("deals")
        .select("price")
        .eq("url_key", url_key)
        .gte("posted_at", _iso_days_ago(cooldown_days))
        .order("posted_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    if not rows:
        return False
    last_price = rows[0].get("price")
    if last_price is None:
        return True
    # Suppress unless the new price is meaningfully lower (>1% cheaper).
    return price >= float(cast(float, last_price)) * 0.99


def record_posted_deal(
    url_key: str, title: str, store: str, price: float | None,
    coupon: str | None, score: int | None, category: str | None = None,
) -> None:
    get_client().table("deals").insert(
        {
            "url_key": url_key,
            "title": title,
            "store": store,
            "price": price,
            "coupon": coupon,
            "score": score,
            "category": category,
        }
    ).execute()


def record_run(started_at: str, counters: dict, sources: dict) -> None:
    """Persist one pipeline-run summary row (dashboard health view)."""
    get_client().table("runs").insert(
        {"started_at": started_at, "sources": sources, **counters}
    ).execute()
