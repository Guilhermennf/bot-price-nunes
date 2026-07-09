"""Store identity: canonical ids, name/URL matching, whitelist filter.

Single source of truth for "which store is this deal from" — used by the
gather-stage whitelist, the Promobit link resolver (final-host validation)
and the affiliate module.
"""

from __future__ import annotations

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
        "hosts": ("magazineluiza.com.br", "magazinevoce.com.br"),
    },
}

# Affiliate-network / redirector hosts — a resolution chain that ENDS on one
# of these is a dead link (e.g. linksynergy "bad merchant" pages).
REDIRECTOR_HOSTS = (
    "linksynergy.com", "awin1.com", "rakuten.com", "tidd.ly", "lomadee.com",
    "promobit.com.br", "promoby.me", "onelink.me", "shareasale.com",
)


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


def identify(name: str | None, url: str | None) -> str | None:
    """Best-effort canonical store id from name and/or URL."""
    return store_from_name(name) or store_from_url(url)
