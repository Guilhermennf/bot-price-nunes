"""Promobit aggregator source.

Reads the homepage Next.js __NEXT_DATA__ payload and extracts the deal objects
(verified live schema: offerTitle / offerPrice / offerOldPrice / offerCoupon /
offerSlug / storeName). If Promobit renames these keys, update _to_deal below.

Note: the payload has no outbound store URL — only the Promobit offer page,
which redirects to the store on click. We post that page. Direct price-confirm
(ML/Amazon) therefore doesn't apply to Promobit deals and is skipped; we trust
Promobit's price for them.
"""

from __future__ import annotations

import logging

from app.models import Deal
from app.sources.base import Source, get, iter_dicts, parse_next_data

log = logging.getLogger(__name__)

LISTING_URL = "https://www.promobit.com.br"
BASE = "https://www.promobit.com.br"


def _to_deal(d: dict) -> Deal | None:
    title = d.get("offerTitle")
    price = d.get("offerPrice")
    slug = d.get("offerSlug")
    if not title or price is None or not slug:
        return None
    try:
        price = float(price)
    except (TypeError, ValueError):
        return None
    # Promobit uses ~0.01 as a sentinel for store-wide coupon promos that have
    # no real product price. Drop them — they'd read as fake 99% discounts.
    if price < 1.0:
        return None

    old = d.get("offerOldPrice")
    try:
        list_price = float(old) if old not in (None, 0) else None
    except (TypeError, ValueError):
        list_price = None

    return Deal(
        title=str(title).strip(),
        store=str(d.get("storeName") or "").strip(),
        url=f"{BASE}/oferta/{slug}",
        price=price,
        list_price=list_price,
        coupon=(d.get("offerCoupon") or None),
        source="promobit",
        raw_id=str(d.get("offerId") or slug),
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
            if "offerPrice" not in node or "offerTitle" not in node:
                continue
            deal = _to_deal(node)
            if deal and deal.key not in deals:
                deals[deal.key] = deal

        log.info("promobit: %d candidate deals", len(deals))
        return list(deals.values())


_source: Source = Promobit()


def fetch() -> list[Deal]:
    return _source.fetch()
