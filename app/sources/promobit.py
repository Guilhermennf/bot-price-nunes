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
import re

from app.models import Deal, normalize_url
from app.sources.base import Source, get, iter_dicts, parse_next_data

log = logging.getLogger(__name__)

LISTING_URL = "https://www.promobit.com.br"
BASE = "https://www.promobit.com.br"

_URL_RE = re.compile(r'https?://[A-Za-z0-9._~:/?#@!$&()*+,;=%-]+')
_NOT_STORE = ("promobit", "promoby", "google", "gstatic", "facebook", "onelink")


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


def resolve_store_url(deal: Deal) -> str | None:
    """Resolve a Promobit deal to the direct store URL.

    The feed payload has no outbound link, but `/Redirect/to/<offerId>/` embeds
    the affiliate link (linksynergy/awin/...), which 30x-chains to the store.
    Two requests per deal — call only for deals about to be posted.
    Returns a normalized direct URL, or None (keep the Promobit page then).
    """
    if not deal.raw_id or not deal.raw_id.isdigit():
        return None
    try:
        page = get(f"{BASE}/Redirect/to/{deal.raw_id}/")
        page.raise_for_status()
        ext = [u for u in _URL_RE.findall(page.text)
               if not any(b in u for b in _NOT_STORE)]
        if not ext:
            return None
        final = get(ext[0])
        url = normalize_url(str(final.url))
        # Sanity: must have left the redirector ecosystem.
        if any(b in url for b in _NOT_STORE):
            return None
        return url
    except Exception as exc:
        log.info("store-url resolve failed for %s: %s", deal.raw_id, exc)
        return None


_source: Source = Promobit()


def fetch() -> list[Deal]:
    return _source.fetch()
