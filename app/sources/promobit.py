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
from app.stores import is_dead_redirect, store_from_url

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
    """Resolve a Promobit deal to a validated direct store URL.

    The feed payload has no outbound link, but `/Redirect/to/<offerId>/` embeds
    the affiliate link(s) (linksynergy/awin/...), which 30x-chain to the store.
    Tries every candidate link on the page and only accepts a final URL whose
    host is a known store (app/stores.py) — dead affiliate links ("bad
    merchant" error pages) and chains that bounce back to Promobit return None.
    Call only for deals about to be posted (a few requests each).
    """
    if not deal.raw_id or not deal.raw_id.isdigit():
        return None
    try:
        page = get(f"{BASE}/Redirect/to/{deal.raw_id}/")
        page.raise_for_status()
    except Exception as exc:
        log.info("store-url resolve failed for %s: %s", deal.raw_id, exc)
        return None

    candidates = [u for u in _URL_RE.findall(page.text)
                  if not any(b in u for b in _NOT_STORE)]
    for candidate in candidates[:4]:
        try:
            final = get(candidate)
            url = normalize_url(str(final.url))
        except Exception as exc:
            log.debug("resolve hop failed (%s): %s", candidate[:60], exc)
            continue
        if is_dead_redirect(url):
            continue
        if store_from_url(url) is not None:
            return url
        log.debug("resolved to non-store host, rejecting: %s", url[:80])
    log.info("no valid store URL for offer %s (%s)", deal.raw_id, deal.store)
    return None


_source: Source = Promobit()


def fetch() -> list[Deal]:
    return _source.fetch()
