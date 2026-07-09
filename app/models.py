"""Core data structures shared across the pipeline."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Query params that are pure tracking noise and must be stripped so the same
# product always collapses to a single dedupe key.
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "ref", "ref_", "refresh", "tag", "ascsubtag",
    "pd_rd_w", "pd_rd_r", "pd_rd_wg", "pf_rd_p", "pf_rd_r", "th", "psc",
    "forceInApp", "tracking_id", "wid", "sid", "c_id", "pdp_filters",
}
# Whole families of tracking params (Mercado Livre "matt_*", recommendation
# "reco_*", etc.) — anything with these prefixes is stripped.
_TRACKING_PREFIXES = ("matt_", "reco_", "utm_", "pf_rd_", "pd_rd_")


def _is_tracking(key: str) -> bool:
    lk = key.lower()
    return lk in _TRACKING_PARAMS or lk.startswith(_TRACKING_PREFIXES)


def normalize_url(url: str) -> str:
    """Return a canonical URL with tracking params removed.

    Used as the stable dedupe / price-history key for a product.
    """
    parts = urlsplit(url.strip())
    kept = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if not _is_tracking(k)
    ]
    query = urlencode(sorted(kept))
    # Drop fragment, lowercase host, strip trailing slash on the path.
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme, parts.netloc.lower(), path, query, ""))


def url_key(url: str) -> str:
    """Short stable hash of the normalized URL — the product identity."""
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()[:32]


@dataclass
class Deal:
    """A candidate deal as it flows through the pipeline.

    Fields are progressively filled: sources set the basics, the direct
    price-confirm step may correct ``price``, validation sets ``discount_pct``,
    and the AI step sets ``score`` / ``copy``.
    """

    title: str
    store: str
    url: str
    price: float | None = None
    list_price: float | None = None
    coupon: str | None = None
    source: str = ""          # e.g. "promobit", "pelando"
    raw_id: str = ""          # source-native id, best-effort

    # Filled downstream:
    discount_pct: float | None = None
    hist_min: float | None = None
    hist_median: float | None = None
    score: int | None = None
    copy: str | None = None
    reason: str | None = None

    key: str = field(default="", init=False)

    def __post_init__(self) -> None:
        if self.url:
            self.url = normalize_url(self.url)
            self.key = url_key(self.url)
