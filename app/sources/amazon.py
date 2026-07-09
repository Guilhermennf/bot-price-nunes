"""Direct price confirmation for an Amazon.com.br product URL.

Amazon runs heavy anti-bot; httpx will often get a CAPTCHA/robot page. We try
cheap fetch first, fall back to Playwright, and simply return None on block
(the pipeline then trusts the aggregator price rather than crashing).
"""

from __future__ import annotations

import logging

from selectolax.parser import HTMLParser

from app.config import get_settings
from app.sources.base import get, jsonld_price, parse_brl

log = logging.getLogger(__name__)

HOSTS = ("amazon.com.br", "amzn.to", "amazon.com")

# Amazon splits the price across whole + fraction spans in a few layouts.
_PRICE_SELECTORS = (
    "#corePriceDisplay_desktop_feature_div .a-price .a-offscreen",
    "#corePrice_feature_div .a-price .a-offscreen",
    "span.a-price span.a-offscreen",
    "#priceblock_ourprice",
    "#priceblock_dealprice",
)


def _from_html(html: str) -> float | None:
    tree = HTMLParser(html)
    for sel in _PRICE_SELECTORS:
        node = tree.css_first(sel)
        if node and node.text().strip():
            price = parse_brl(node.text())
            if price:
                return price
    return jsonld_price(html)


def confirm_price(url: str) -> float | None:
    try:
        resp = get(url)
        resp.raise_for_status()
    except Exception as exc:
        log.warning("Amazon confirm fetch failed (%s): %s", url, exc)
        return None

    if "captcha" in resp.text.lower() or "api-services-support@amazon" in resp.text:
        log.info("Amazon returned a bot page; trusting aggregator price")
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
        log.warning("playwright not installed; skipping Amazon JS fallback")
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
        log.warning("Amazon playwright fallback failed (%s): %s", url, exc)
        return None
