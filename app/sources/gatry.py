"""Gatry aggregator source.

Old-school server-rendered HTML: each deal is an <article> with the title and
outbound link in `h3 > a`, price in `.price`, and store name in the
`.option-store a` button ("Ir para <Loja>"). Outbound links are usually
affiliate shortlinks (tidd.ly/Awin) — resolved to the real store URL at
posting time (see app/resolver.py), not here.
"""

from __future__ import annotations

import logging

from selectolax.parser import HTMLParser

from app.models import Deal
from app.sources.base import Source, get, parse_brl

log = logging.getLogger(__name__)

LISTING_URL = "https://gatry.com/"


def _to_deal(article) -> Deal | None:
    link_node = article.css_first("h3 > a")
    if not link_node:
        return None
    title = (link_node.text() or "").strip()
    url = link_node.attributes.get("href") or ""
    if not title or not url.startswith("http"):
        return None

    price_node = article.css_first(".price")
    price = parse_brl(price_node.text()) if price_node else None
    if not price or price < 1.0:
        return None

    store = ""
    store_node = article.css_first(".option-store a")
    if store_node:
        # Button text is "Ir para <Loja>" (the "Ir para" span is hidden on
        # mobile); strip the prefix if present.
        store = (store_node.text() or "").strip()
        store = store.removeprefix("Ir para").strip()

    return Deal(
        title=title,
        store=store,
        url=url,
        price=price,
        coupon=None,
        source="gatry",
        raw_id=url,
    )


class Gatry:
    name = "gatry"

    def fetch(self) -> list[Deal]:
        try:
            resp = get(LISTING_URL)
            resp.raise_for_status()
        except Exception as exc:
            log.warning("gatry fetch failed: %s", exc)
            return []

        tree = HTMLParser(resp.text)
        deals: dict[str, Deal] = {}
        for article in tree.css("article"):
            deal = _to_deal(article)
            if deal and deal.key not in deals:
                deals[deal.key] = deal

        log.info("gatry: %d candidate deals", len(deals))
        return list(deals.values())


_source: Source = Gatry()


def fetch() -> list[Deal]:
    return _source.fetch()
