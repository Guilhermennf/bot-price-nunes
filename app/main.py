"""Pipeline orchestrator — the single entrypoint the cron job runs.

    python -m app.main            # full run: scrape -> validate -> AI -> post
    python -m app.main --dry-run  # everything except Telegram send + deals write

Stateless: all memory lives in Supabase. Any single stage failing degrades
gracefully rather than aborting the whole run.
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
import time
from urllib.parse import urlsplit

# Windows consoles default to cp1252, which chokes on emoji in deal copy.
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from app.ai import gemini
from app.config import get_settings
from app.models import Deal
from app.sources import amazon, mercadolivre, pelando, promobit
from app.validation import checkout_sim
from app.validation.price_history import validate

log = logging.getLogger("bot-price-nunes")


# ---- DB helpers (resilient: a pure offline dry-run works with no Supabase) ---

def _db():
    """Return the supabase_client module, or None if not configured/reachable."""
    from app.db import supabase_client
    s = get_settings()
    if not s.supabase_url or not s.supabase_key:
        return None
    return supabase_client


def record_price(deal: Deal) -> None:
    db = _db()
    if not db or deal.price is None:
        return
    try:
        db.record_price(deal.key, deal.price)
    except Exception as exc:
        log.warning("record_price failed: %s", exc)


def already_posted(deal: Deal) -> bool:
    db = _db()
    if not db or deal.price is None:
        return False
    try:
        return db.was_recently_posted(deal.key, deal.price,
                                      get_settings().repost_cooldown_days)
    except Exception as exc:
        log.warning("dedupe check failed: %s", exc)
        return False


def mark_posted(deal: Deal) -> None:
    db = _db()
    if not db:
        return
    try:
        db.record_posted_deal(deal.key, deal.title, deal.store, deal.price,
                              deal.coupon, deal.score)
    except Exception as exc:
        log.warning("record_posted_deal failed: %s", exc)


# ------------------------------- stages --------------------------------------

def gather() -> list[Deal]:
    deals: dict[str, Deal] = {}
    for src in (promobit, pelando):
        for deal in src.fetch():
            deals.setdefault(deal.key, deal)
    log.info("gathered %d unique candidates", len(deals))
    return list(deals.values())


def confirm_price(deal: Deal) -> None:
    """Correct deal.price against the live store page when we support the host."""
    host = urlsplit(deal.url).netloc.lower()
    confirmer = None
    if any(h in host for h in mercadolivre.HOSTS):
        confirmer = mercadolivre.confirm_price
    elif any(h in host for h in amazon.HOSTS):
        confirmer = amazon.confirm_price
    if not confirmer:
        return
    live = confirmer(deal.url)
    if live is not None:
        if deal.price is not None and abs(live - deal.price) / max(live, 1) > 0.005:
            log.info("price corrected %.2f -> %.2f for %s", deal.price, live, deal.title)
        deal.price = live


def _priority(deal: Deal) -> float:
    """Rank candidates so expensive steps hit the best ones first."""
    if deal.list_price and deal.price and deal.list_price > deal.price:
        return (deal.list_price - deal.price) / deal.list_price
    return 0.0


def run(dry_run: bool = False) -> None:
    s = get_settings()
    candidates = gather()
    candidates.sort(key=_priority, reverse=True)
    candidates = candidates[: s.max_deals_per_run]

    posted = 0
    for deal in candidates:
        confirm_price(deal)

        # Judge against prior history, THEN record this observation (so the
        # current price never pollutes its own median).
        verdict = validate(deal)
        record_price(deal)  # build the series (happens even in dry-run)
        if not verdict.is_real_drop:
            log.info("skip (validation): %s — %s", deal.title, verdict.reason)
            continue

        if not checkout_sim.verify_coupon(deal):
            log.info("skip (coupon invalid): %s", deal.title)
            continue

        evaluation = gemini.evaluate(deal)
        if evaluation is None:
            log.info("skip (no AI eval): %s", deal.title)
            continue
        deal.score = evaluation.score
        deal.copy = evaluation.copy
        deal.reason = evaluation.reason
        if not evaluation.legit or evaluation.score < s.min_score:
            log.info("skip (score %s): %s — %s", evaluation.score, deal.title,
                     evaluation.reason)
            continue

        if already_posted(deal):
            log.info("skip (already posted): %s", deal.title)
            continue

        if dry_run:
            print(_preview(deal))
        else:
            from app.notify.telegram import send_deal
            send_deal(deal)
            mark_posted(deal)
        posted += 1

        time.sleep(random.uniform(0.5, 1.5))  # be polite between deals

    verb = "would post" if dry_run else "posted"
    log.info("done. %s %d deals", verb, posted)


def _preview(deal: Deal) -> str:
    return (
        "\n--- CANDIDATE ---\n"
        f"title:    {deal.title}\n"
        f"store:    {deal.store}\n"
        f"price:    R$ {deal.price}\n"
        f"discount: {deal.discount_pct}% (median R$ {deal.hist_median}, "
        f"min R$ {deal.hist_min})\n"
        f"score:    {deal.score} — {deal.reason}\n"
        f"coupon:   {deal.coupon}\n"
        f"copy:     {deal.copy}\n"
        f"url:      {deal.url}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Brazilian deal bot pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="run everything but don't post to Telegram or write deals")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
