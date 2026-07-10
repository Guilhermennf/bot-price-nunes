"""Store identity: canonical ids, name/URL matching, whitelist filter.

Single source of truth for "which store is this deal from" — used by the
gather-stage whitelist, the Promobit link resolver (final-host validation)
and the affiliate module.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

# Canonical store id -> aliases seen in aggregator feeds + real product hosts.
STORES: dict[str, dict[str, tuple[str, ...]]] = {
    "amazon": {
        "names": ("amazon",),
        "hosts": ("amazon.com.br", "amzn.to", "amazon.com"),
    },
    "mercadolivre": {
        "names": ("mercado livre", "mercadolivre", "mercadolibre"),
        "hosts": ("mercadolivre.com.br", "mercadolibre.com"),
    },
    "aliexpress": {
        "names": ("aliexpress", "ali express"),
        "hosts": ("aliexpress.com", "aliexpress.us"),
    },
    "shopee": {
        "names": ("shopee",),
        "hosts": ("shopee.com.br",),
    },
    "magalu": {
        "names": ("magalu", "magazine luiza", "magazineluiza", "magazine você",
                  "magazine voce", "magazinevoce"),
        # influenciadormagalu.com.br is Magalu's official affiliate-program
        # storefront (used by Pechinchou links) — same catalog/checkout.
        "hosts": ("magazineluiza.com.br", "magazinevoce.com.br",
                  "influenciadormagalu.com.br"),
    },
}

# Affiliate-network / redirector hosts — a resolution chain that ENDS on one
# of these is a dead link (e.g. linksynergy "bad merchant" pages).
REDIRECTOR_HOSTS = (
    "linksynergy.com", "awin1.com", "rakuten.com", "tidd.ly", "lomadee.com",
    "promobit.com.br", "promoby.me", "onelink.me", "shareasale.com",
)

# A resolved URL can have a whitelisted store HOST yet still not be a product
# page — e.g. Mercado Livre's `meli.la` short links land on a generic
# "/social/promobit?forceInApp=true" recommendations page (a client-JS-driven
# landing, not an HTTP redirect to the product) rather than the item itself.
# These patterns confirm the URL actually names a specific product.
_PRODUCT_URL_PATTERNS: dict[str, re.Pattern[str]] = {
    "mercadolivre": re.compile(r"MLB-?\d{6,}", re.IGNORECASE),
    "amazon": re.compile(r"/(?:dp|gp/product|gp/aw/d)/[A-Z0-9]{10}", re.IGNORECASE),
    "aliexpress": re.compile(r"/item/\d+\.html"),
    "shopee": re.compile(r"-i\.\d+\.\d+"),
    "magalu": re.compile(r"/p/[a-zA-Z0-9]{5,}"),
}


def _host(url: str) -> str:
    return urlsplit(url).netloc.lower()


def _host_matches(host: str, candidate: str) -> bool:
    return host == candidate or host.endswith("." + candidate)


def store_from_name(name: str | None) -> str | None:
    """Canonical store id from an aggregator's display name, or None."""
    if not name:
        return None
    low = name.strip().lower()
    for store_id, spec in STORES.items():
        if any(alias in low for alias in spec["names"]):
            return store_id
    return None


def store_from_url(url: str | None) -> str | None:
    """Canonical store id from a product URL's host, or None."""
    if not url:
        return None
    host = _host(url)
    for store_id, spec in STORES.items():
        if any(_host_matches(host, h) for h in spec["hosts"]):
            return store_id
    return None


def is_dead_redirect(url: str) -> bool:
    """True if the URL is still inside an affiliate/redirector network."""
    host = _host(url)
    return any(_host_matches(host, h) for h in REDIRECTOR_HOSTS)


def looks_like_product_url(url: str, store_id: str | None = None) -> bool:
    """True if the URL's path actually names a specific product.

    A whitelisted-store HOST is necessary but not sufficient: generic
    category/social/recommendation pages share the same host. Stores without
    a known pattern are not blocked here (host + dead-redirect checks already
    filter those).
    """
    store_id = store_id or store_from_url(url)
    if store_id is None:
        return False
    pattern = _PRODUCT_URL_PATTERNS.get(store_id)
    return True if pattern is None else bool(pattern.search(url))


def identify(name: str | None, url: str | None) -> str | None:
    """Best-effort canonical store id from name and/or URL."""
    return store_from_name(name) or store_from_url(url)
