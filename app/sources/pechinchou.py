"""Pechinchou aggregator source.

Next.js site — the homepage __NEXT_DATA__ carries
props.pageProps.promos.results[]: title, price/old_price (decimal strings),
long_url/short_url (direct store or store-affiliate link), store{name,
slug_url} and coupons (list of code strings). Verified live 2026-07-10.
"""

from __future__ import annotations

import logging
from typing import Any

from app.models import Deal
from app.sources.base import Source, get, parse_next_data

log = logging.getLogger(__name__)

LISTING_URL = "https://pechinchou.com.br/"


def _num(value: Any) -> float | None:
    try:
        f = float(value)
        return f if f >= 1.0 else None
    except (TypeError, ValueError):
        return None


def _to_deal(promo: dict) -> Deal | None:
    title = promo.get("title")
    price = _num(promo.get("price"))
    url = promo.get("long_url") or promo.get("short_url")
    if not title or price is None or not url:
        return None
    if promo.get("status") not in (None, "ACTIVE"):
        return None

    store = promo.get("store") or {}
    coupons = promo.get("coupons") or []
    coupon = str(coupons[0]) if coupons and coupons[0] else None

    return Deal(
        title=str(title).strip(),
        store=str(store.get("name") or "").strip(),
        url=str(url),
        price=price,
        list_price=_num(promo.get("old_price")),
        coupon=coupon,
        source="pechinchou",
        raw_id=str(promo.get("id") or promo.get("slug") or ""),
    )


class Pechinchou:
    name = "pechinchou"

    def fetch(self) -> list[Deal]:
        try:
            resp = get(LISTING_URL)
            resp.raise_for_status()
        except Exception as exc:
            log.warning("pechinchou fetch failed: %s", exc)
            return []

        data = parse_next_data(resp.text)
        if not data:
            log.warning("pechinchou: no __NEXT_DATA__ (layout changed?)")
            return []

        try:
            results = data["props"]["pageProps"]["promos"]["results"]
        except (KeyError, TypeError):
            log.warning("pechinchou: unexpected payload shape (API changed?)")
            return []

        deals: dict[str, Deal] = {}
        for promo in results:
            if not isinstance(promo, dict):
                continue
            deal = _to_deal(promo)
            if deal and deal.key not in deals:
                deals[deal.key] = deal

        log.info("pechinchou: %d candidate deals", len(deals))
        return list(deals.values())


_source: Source = Pechinchou()


def fetch() -> list[Deal]:
    return _source.fetch()
