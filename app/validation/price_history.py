"""Price-history validation (MVP).

Decides whether a deal is a *real* drop by comparing the current price to the
product's own recent price series in Supabase — this is what rejects fake
"de/por" inflation. Also computes the honest discount % (vs recent median,
not the store's claimed list price).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings
from app.db.supabase_client import PriceStats, get_price_stats
from app.models import Deal


@dataclass
class Verdict:
    is_real_drop: bool
    discount_pct: float | None
    reason: str


def validate(deal: Deal) -> Verdict:
    """Compare ``deal.price`` against its stored history.

    Records nothing here; the orchestrator records the observation separately.
    """
    s = get_settings()
    if deal.price is None or deal.price <= 0:
        return Verdict(False, None, "no usable price")

    stats: PriceStats = get_price_stats(deal.key, s.history_window_days)
    deal.hist_min = stats.minimum
    deal.hist_median = stats.median

    # First time we ever see this product: no history to judge against. Fall
    # back to the store's claimed list price if it implies a solid discount,
    # otherwise let it pass to AI as "unverified" (AI is the second gate).
    if stats.count == 0 or stats.median is None:
        if deal.list_price and deal.list_price > deal.price:
            disc = (1 - deal.price / deal.list_price) * 100
            deal.discount_pct = round(disc, 1)
            ok = disc >= s.min_discount_pct
            return Verdict(ok, deal.discount_pct,
                           f"no history; claimed −{disc:.0f}% vs list price")
        deal.discount_pct = None
        return Verdict(True, None, "no history; first observation")

    disc = (1 - deal.price / stats.median) * 100
    deal.discount_pct = round(disc, 1)
    if disc < s.min_discount_pct:
        return Verdict(False, deal.discount_pct,
                       f"only −{disc:.0f}% vs {s.history_window_days}d median")
    return Verdict(True, deal.discount_pct,
                   f"−{disc:.0f}% vs {s.history_window_days}d median "
                   f"(min seen R$ {stats.minimum:.2f})")
