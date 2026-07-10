"""Posting-time URL resolution: turn a deal's raw URL into a validated,
direct product link — or None (deal must then be skipped, never posted
with a broken/generic link).

Per-source strategy:
- promobit:  its /Redirect/to/ page embeds affiliate links (+ meli.la browser
             fallback) — handled by promobit.resolve_store_url.
- gatry:     outbound links are affiliate shortlinks (tidd.ly/Awin) — follow
             redirects, then validate.
- pelando /
  pechinchou: URLs point at the store already — just validate (and follow
             one redirect hop if needed).
"""

from __future__ import annotations

import logging

from app.models import Deal, normalize_url
from app.sources import promobit
from app.sources.base import get
from app.stores import is_dead_redirect, looks_like_product_url, store_from_url

log = logging.getLogger(__name__)


def _validate(url: str) -> str | None:
    normalized = normalize_url(url)
    if is_dead_redirect(normalized):
        return None
    store_id = store_from_url(normalized)
    if store_id is not None and looks_like_product_url(normalized, store_id):
        return normalized
    return None


def _follow_and_validate(url: str) -> str | None:
    """Validate as-is first (no network); else follow redirects once and retry."""
    direct = _validate(url)
    if direct:
        return direct
    try:
        resp = get(url)
        return _validate(str(resp.url))
    except Exception as exc:
        log.info("follow failed (%s): %s", url[:60], exc)
        return None


def resolve_posting_url(deal: Deal) -> str | None:
    """The URL to actually post for this deal, or None to skip it."""
    if deal.source == "promobit":
        return promobit.resolve_store_url(deal)
    return _follow_and_validate(deal.url)
