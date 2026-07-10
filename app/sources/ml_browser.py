"""Resolve Mercado Livre's generic `meli.la` landing to the real product URL.

The meli.la short links Promobit embeds do an HTTP 301 to a generic
"/social/promobit" recommendations page — the actual product only appears
after client-side JS renders the page, with the offer's product as the FIRST
product anchor. This module runs that JS in headless Chromium and validates
the extracted link against the deal title before trusting it.

Cost: one browser navigation (~3-5s) per deal — call only for deals about
to be posted. Fails soft (returns None) on any error or validation miss.
"""

from __future__ import annotations

import logging
import re
import unicodedata

from app.config import get_settings
from app.models import normalize_url
from app.stores import looks_like_product_url

log = logging.getLogger(__name__)

_PRODUCT_ANCHOR_SELECTOR = "a[href*='/p/MLB'], a[href*='MLB-']"


def _fold_tokens(text: str) -> set[str]:
    """Lowercase, strip accents, keep tokens of 4+ chars (discriminative words)."""
    norm = unicodedata.normalize("NFKD", text.lower())
    folded = "".join(c for c in norm if not unicodedata.combining(c))
    return {t for t in re.split(r"[^a-z0-9]+", folded) if len(t) >= 4}


def _title_matches_slug(title: str, url: str) -> bool:
    """At least 40% of the title's discriminative tokens appear in the URL slug.

    Guards against grabbing a *recommended* product instead of the offer's own
    (the landing lists ~40 unrelated items after the first).
    """
    title_tokens = _fold_tokens(title)
    if not title_tokens:
        return False
    url_tokens = _fold_tokens(url)
    overlap = len(title_tokens & url_tokens)
    return overlap / len(title_tokens) >= 0.4


def resolve_ml_landing(meli_url: str, deal_title: str) -> str | None:
    """Open the meli.la link in Chromium, grab the first product anchor,
    validate it names the same product as the deal title."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.info("playwright not installed; cannot resolve ML landing")
        return None

    s = get_settings()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=s.user_agent, locale="pt-BR")
            page = ctx.new_page()
            page.goto(meli_url, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_selector(_PRODUCT_ANCHOR_SELECTOR, timeout=15_000)
            hrefs = page.eval_on_selector_all(
                _PRODUCT_ANCHOR_SELECTOR,
                "els => els.slice(0, 5).map(e => e.href)",
            )
            browser.close()
    except Exception as exc:
        log.info("ML landing resolve failed (%s): %s", meli_url[:50], exc)
        return None

    for href in hrefs:
        url = normalize_url(str(href))
        if looks_like_product_url(url, "mercadolivre") and _title_matches_slug(
            deal_title, url
        ):
            return url
    log.info("ML landing had no anchor matching title %r", deal_title[:50])
    return None
