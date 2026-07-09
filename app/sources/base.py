"""Source protocol + shared scraping helpers."""

from __future__ import annotations

import json
import re
from typing import Any, Iterator, Protocol

import httpx
from selectolax.parser import HTMLParser

from app.config import get_settings
from app.models import Deal


class Source(Protocol):
    """Anything that can produce a batch of candidate deals."""

    name: str

    def fetch(self) -> list[Deal]:
        ...


def get(url: str, **kwargs) -> httpx.Response:
    """GET with the configured UA + timeout and sane defaults."""
    s = get_settings()
    headers = {
        "User-Agent": s.user_agent,
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    headers.update(kwargs.pop("headers", {}))
    return httpx.get(url, headers=headers, timeout=s.request_timeout,
                     follow_redirects=True, **kwargs)


def parse_next_data(html: str) -> dict | None:
    """Extract Next.js __NEXT_DATA__ JSON blob (Promobit & Pelando are Next apps).

    Far more stable than CSS selectors when it's present.
    """
    tree = HTMLParser(html)
    node = tree.css_first("script#__NEXT_DATA__")
    if not node:
        return None
    try:
        return json.loads(node.text())
    except (ValueError, TypeError):
        return None


def iter_dicts(obj: Any) -> Iterator[dict]:
    """Depth-first walk yielding every dict nested anywhere in a JSON structure.

    Lets a source hunt for 'deal-shaped' objects without hard-coding the exact
    path through a Next.js payload (which changes often).
    """
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from iter_dicts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_dicts(v)


def first_key(d: dict, *candidates: str) -> Any:
    """Return the first present, truthy value among candidate keys."""
    for k in candidates:
        if k in d and d[k] not in (None, "", []):
            return d[k]
    return None


_PRICE_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*|\d+)(?:,(\d{2}))?")


def parse_brl(text: str | None) -> float | None:
    """Parse a Brazilian-format price string like 'R$ 1.299,90' -> 1299.90."""
    if not text:
        return None
    m = _PRICE_RE.search(text.replace("\xa0", " "))
    if not m:
        return None
    integer = m.group(1).replace(".", "")
    cents = m.group(2) or "00"
    try:
        return float(f"{integer}.{cents}")
    except ValueError:
        return None


def jsonld_price(html: str) -> float | None:
    """Pull an offer price out of schema.org JSON-LD blocks (store-agnostic).

    JSON-LD uses a dot-decimal 'price' (e.g. "1299.90"), so parse as float
    directly rather than via the BRL parser.
    """
    tree = HTMLParser(html)
    for node in tree.css('script[type="application/ld+json"]'):
        try:
            data = json.loads(node.text())
        except (ValueError, TypeError):
            continue
        for d in iter_dicts(data):
            offers = d.get("offers")
            for offer in iter_dicts(offers) if offers is not None else ():
                price = offer.get("price") or offer.get("lowPrice")
                if price is not None:
                    try:
                        return float(str(price).replace(",", "."))
                    except ValueError:
                        continue
    return None


def meta_price(html: str) -> float | None:
    """Fallback: itemprop / og:price meta tags (dot-decimal)."""
    tree = HTMLParser(html)
    for sel in ('meta[itemprop="price"]', 'meta[property="product:price:amount"]',
                'meta[property="og:price:amount"]'):
        node = tree.css_first(sel)
        if node:
            content = node.attributes.get("content")
            if content:
                try:
                    return float(content.replace(",", "."))
                except ValueError:
                    continue
    return None
