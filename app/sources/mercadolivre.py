"""Direct price confirmation for a Mercado Livre product URL.

Purpose: verify an aggregator's advertised price against ML's live page before
we trust it. Tries cheap httpx + JSON-LD/meta first; only falls back to
Playwright when the price is JS-rendered.
"""

from __future__ import annotations

import logging

from selectolax.parser import HTMLParser

from app.config import get_settings
from app.sources.base import get, jsonld_price, meta_price, parse_brl

log = logging.getLogger(__name__)

HOSTS = ("mercadolivre.com", "mercadolibre.com", "produto.mercadolivre")


def _from_html(html: str) -> float | None:
    price = jsonld_price(html) or meta_price(html)
    if price is not None:
        return price
    # ML renders the current price in <meta itemprop="price"> usually, but as a
    # last resort read the andes-money-amount fraction/cents nodes.
    tree = HTMLParser(html)
    frac = tree.css_first(".andes-money-amount__fraction")
    if frac:
        cents_node = tree.css_first(".andes-money-amount__cents")
        cents = cents_node.text() if cents_node else "00"
        return parse_brl(f"{frac.text()},{cents}")
    return None


def confirm_price(url: str) -> float | None:
    try:
        resp = get(url)
        resp.raise_for_status()
    except Exception as exc:
        log.warning("ML confirm fetch failed (%s): %s", url, exc)
        return None

    # ML bounces datacenter/no-JS requests to an anti-bot verification wall.
    if "account-verification" in str(resp.url) or "/gz/" in str(resp.url):
        log.info("ML anti-bot wall hit; trusting aggregator price")
        return _maybe_browser(url)

    price = _from_html(resp.text)
    return price if price is not None else _maybe_browser(url)


def _maybe_browser(url: str) -> float | None:
    """Playwright fallback, only when explicitly enabled (off in CI)."""
    if not get_settings().enable_browser_confirm:
        return None
    return _confirm_with_playwright(url)


def _confirm_with_playwright(url: str) -> float | None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.warning("playwright not installed; skipping ML JS fallback")
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            html = page.content()
            browser.close()
        return _from_html(html)
    except Exception as exc:
        log.warning("ML playwright fallback failed (%s): %s", url, exc)
        return None
