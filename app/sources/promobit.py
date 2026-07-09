"""Promobit aggregator source.

Strategy: fetch the "most popular in the last 24h" listing, pull the Next.js
__NEXT_DATA__ payload, and heuristically extract deal-shaped objects. This is
resilient to CSS churn; if Promobit changes their internal JSON field names,
adjust the key candidates below (that's the one thing that needs live tuning).
"""

from __future__ import annotations

import logging

from app.models import Deal
from app.sources.base import (
    Source, first_key, get, iter_dicts, parse_brl, parse_next_data,
)

log = logging.getLogger(__name__)

LISTING_URL = "https://www.promobit.com.br/ofertas/"
BASE = "https://www.promobit.com.br"


def _looks_like_deal(d: dict) -> bool:
    has_title = any(k in d for k in ("title", "name", "offer_title", "slug"))
    has_price = any(k in d for k in ("price", "new_price", "offer_price", "value"))
    return has_title and has_price


def _to_deal(d: dict) -> Deal | None:
    title = first_key(d, "title", "offer_title", "name")
    raw_price = first_key(d, "new_price", "offer_price", "price", "value")
    if not title or raw_price is None:
        return None

    price = raw_price if isinstance(raw_price, (int, float)) else parse_brl(str(raw_price))
    list_raw = first_key(d, "old_price", "list_price", "original_price")
    list_price = (
        list_raw if isinstance(list_raw, (int, float)) else parse_brl(str(list_raw or ""))
    )

    # Prefer the outbound store link; fall back to the Promobit offer page.
    link = first_key(d, "url", "outbound_url", "store_url", "link", "permalink")
    slug = first_key(d, "slug")
    if not link and slug:
        link = f"{BASE}/oferta/{slug}"
    if not link:
        return None
    if link.startswith("/"):
        link = BASE + link

    store = first_key(d, "store", "store_name", "retailer") or ""
    if isinstance(store, dict):
        store = first_key(store, "name", "title") or ""

    return Deal(
        title=str(title).strip(),
        store=str(store).strip(),
        url=str(link),
        price=price,
        list_price=list_price,
        coupon=first_key(d, "coupon", "coupon_code", "voucher"),
        source="promobit",
        raw_id=str(first_key(d, "id", "offer_id", "slug") or ""),
    )


class Promobit:
    name = "promobit"

    def fetch(self) -> list[Deal]:
        try:
            resp = get(LISTING_URL)
            resp.raise_for_status()
        except Exception as exc:  # network / block — never crash the whole run
            log.warning("promobit fetch failed: %s", exc)
            return []

        data = parse_next_data(resp.text)
        if not data:
            log.warning("promobit: no __NEXT_DATA__ found (layout changed?)")
            return []

        deals: dict[str, Deal] = {}
        for node in iter_dicts(data):
            if not _looks_like_deal(node):
                continue
            deal = _to_deal(node)
            if deal and deal.key not in deals:
                deals[deal.key] = deal

        log.info("promobit: %d candidate deals", len(deals))
        return list(deals.values())


_source: Source = Promobit()


def fetch() -> list[Deal]:
    return _source.fetch()
