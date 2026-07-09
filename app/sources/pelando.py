"""Pelando aggregator source.

Pelando's site is client-rendered (Astro) — the deals come from its internal
REST feed at api-web.pelando.com.br. That endpoint just needs an anonymous
visitor id header (`x-sosho-unlogged-id`, any UUID) plus the site Origin/Referer;
no login. So we call it directly with httpx — no browser needed.

Verified live schema: title / price / discountPercentage / slug / sourceUrl /
store{name} / kind. Coupon-only entries have price=null and are skipped.
"""

from __future__ import annotations

import logging
import uuid

import httpx

from app.config import get_settings
from app.models import Deal
from app.sources.base import Source

log = logging.getLogger(__name__)

API_URL = "https://api-web.pelando.com.br/feed/highlights"
BASE = "https://www.pelando.com.br"
# One anonymous visitor id per process is plenty.
_VISITOR_ID = str(uuid.uuid4())


def _headers() -> dict:
    s = get_settings()
    return {
        "User-Agent": s.user_agent,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Origin": BASE,
        "Referer": BASE + "/",
        "x-sosho-unlogged-id": _VISITOR_ID,
    }


def _to_deal(d: dict) -> Deal | None:
    price = d.get("price")
    title = d.get("title")
    slug = d.get("slug")
    if price is None or not title or not slug:
        return None
    try:
        price = float(price)
    except (TypeError, ValueError):
        return None
    if price < 1.0:  # sentinel / coupon-style entry
        return None

    disc = d.get("discountPercentage")
    list_price = None
    if isinstance(disc, (int, float)) and 0 < disc < 100:
        list_price = round(price / (1 - disc / 100), 2)

    store = d.get("store") or {}
    store_name = store.get("name") if isinstance(store, dict) else ""

    # Prefer the outbound store link (lets us price-confirm on ML/Amazon);
    # fall back to the Pelando deal page.
    link = d.get("sourceUrl") or f"{BASE}/d/{slug}"

    return Deal(
        title=str(title).strip(),
        store=str(store_name or "").strip(),
        url=str(link),
        price=price,
        list_price=list_price,
        coupon=d.get("code") or None,
        source="pelando",
        raw_id=str(d.get("id") or slug),
    )


class Pelando:
    name = "pelando"

    def fetch(self) -> list[Deal]:
        s = get_settings()
        try:
            resp = httpx.get(
                API_URL,
                params={"scenario": "Main-Feed", "limit": 30},
                headers=_headers(),
                timeout=s.request_timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            log.warning("pelando fetch failed: %s", exc)
            return []

        data = payload.get("data") if isinstance(payload, dict) else None
        items = data.get("deals") if isinstance(data, dict) else None
        if not isinstance(items, list):
            log.warning("pelando: unexpected payload shape (API changed?)")
            return []

        deals: dict[str, Deal] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            deal = _to_deal(item)
            if deal and deal.key not in deals:
                deals[deal.key] = deal

        log.info("pelando: %d candidate deals", len(deals))
        return list(deals.values())


_source: Source = Pelando()


def fetch() -> list[Deal]:
    return _source.fetch()
