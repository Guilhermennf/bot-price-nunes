"""Pelando aggregator source.

Same heuristic strategy as promobit.py: walk the Next.js payload for
deal-shaped objects. Field-name candidates below are the tuning point if
Pelando changes their internal schema.
"""

from __future__ import annotations

import logging

from app.models import Deal
from app.sources.base import (
    Source, first_key, get, iter_dicts, parse_brl, parse_next_data,
)

log = logging.getLogger(__name__)

LISTING_URL = "https://www.pelando.com.br/quente"
BASE = "https://www.pelando.com.br"


def _looks_like_deal(d: dict) -> bool:
    has_title = any(k in d for k in ("title", "name"))
    has_price = any(k in d for k in ("price", "newPrice", "currentPrice"))
    has_link = any(k in d for k in ("url", "sourceUrl", "link", "slug"))
    return has_title and has_price and has_link


def _to_deal(d: dict) -> Deal | None:
    title = first_key(d, "title", "name")
    raw_price = first_key(d, "newPrice", "currentPrice", "price")
    if not title or raw_price is None:
        return None

    price = raw_price if isinstance(raw_price, (int, float)) else parse_brl(str(raw_price))
    list_raw = first_key(d, "oldPrice", "originalPrice", "listPrice")
    list_price = (
        list_raw if isinstance(list_raw, (int, float)) else parse_brl(str(list_raw or ""))
    )

    link = first_key(d, "sourceUrl", "url", "link")
    slug = first_key(d, "slug")
    if not link and slug:
        link = f"{BASE}/d/{slug}"
    if not link:
        return None
    if link.startswith("/"):
        link = BASE + link

    store = first_key(d, "store", "merchant", "retailer") or ""
    if isinstance(store, dict):
        store = first_key(store, "name", "title") or ""

    return Deal(
        title=str(title).strip(),
        store=str(store).strip(),
        url=str(link),
        price=price,
        list_price=list_price,
        coupon=first_key(d, "coupon", "couponCode", "code"),
        source="pelando",
        raw_id=str(first_key(d, "id", "slug") or ""),
    )


class Pelando:
    name = "pelando"

    def fetch(self) -> list[Deal]:
        try:
            resp = get(LISTING_URL)
            resp.raise_for_status()
        except Exception as exc:
            log.warning("pelando fetch failed: %s", exc)
            return []

        data = parse_next_data(resp.text)
        if not data:
            log.warning("pelando: no __NEXT_DATA__ found (layout changed?)")
            return []

        deals: dict[str, Deal] = {}
        for node in iter_dicts(data):
            if not _looks_like_deal(node):
                continue
            deal = _to_deal(node)
            if deal and deal.key not in deals:
                deals[deal.key] = deal

        log.info("pelando: %d candidate deals", len(deals))
        return list(deals.values())


_source: Source = Pelando()


def fetch() -> list[Deal]:
    return _source.fetch()
