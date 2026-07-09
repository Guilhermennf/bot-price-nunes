"""Affiliate link transformation — dormant until env vars are filled.

Applied in main.py immediately before sending, AFTER dedupe/normalization,
so affiliate params never pollute dedupe keys or price-history identity.

Activation per store:
- Amazon:        set AMAZON_ASSOC_TAG (Amazon Associates tag, e.g. "meucanal-20")
- Mercado Livre: set ML_AFFILIATE_TOOL_ID (Programa de Afiliados ML tool id;
                 links use the matt_word/matt_tool query params)
- AliExpress / Shopee / Magalu: their programs (AliExpress Portals, Shopee
  Affiliate, Awin for Magalu) issue portal-generated links per product and
  have no simple query-param form — wire a link-builder here when the
  accounts exist. Until then URLs pass through untouched.
"""

from __future__ import annotations

from urllib.parse import urlencode, urlsplit, urlunsplit

from app.config import get_settings
from app.stores import identify


def _append_params(url: str, params: dict[str, str]) -> str:
    parts = urlsplit(url)
    query = parts.query + ("&" if parts.query else "") + urlencode(params)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def apply(url: str, store_name: str | None = None) -> str:
    """Return the URL with this bot's affiliate identity attached (when
    configured for that store); otherwise return it unchanged."""
    s = get_settings()
    store = identify(store_name, url)

    if store == "amazon" and s.amazon_assoc_tag:
        return _append_params(url, {"tag": s.amazon_assoc_tag})

    if store == "mercadolivre" and s.ml_affiliate_tool_id:
        return _append_params(url, {
            "matt_word": s.ml_affiliate_tool_id,
            "matt_tool": s.ml_affiliate_tool_id,
        })

    # aliexpress / shopee / magalu: portal-generated links required — TODO.
    return url
