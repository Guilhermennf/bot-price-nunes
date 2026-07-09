"""Checkout simulation — STUB, gated behind ENABLE_CHECKOUT_SIM.

Not implemented in v1. When enabled per-store later, this will drive Playwright
to add the item to a cart and apply the coupon to confirm it's still valid.
Kept isolated so the MVP never depends on it.
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.models import Deal

log = logging.getLogger(__name__)


def is_enabled() -> bool:
    return get_settings().enable_checkout_sim


def verify_coupon(deal: Deal) -> bool:
    """Return True if the coupon is confirmed valid via checkout simulation.

    When the flag is off (default) this always returns True so it's a no-op in
    the pipeline. Real per-store implementations go here later.
    """
    if not is_enabled():
        return True
    if not deal.coupon:
        return True

    log.info("checkout_sim enabled but no implementation for store=%s; passing through",
             deal.store)
    # TODO: per-store Playwright cart flows (Mercado Livre, Amazon, ...).
    return True
