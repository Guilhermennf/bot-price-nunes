"""Pipeline orchestrator — the single entrypoint the cron job runs.

    python -m app.main                # collect: scrape -> validate -> AI -> queue
    python -m app.main --dry-run      # collect, but print candidates, write nothing
    python -m app.main --post-queue 1 # drain N queued deals to the channel

Collect runs approve deals into the `post_queue` table; posting runs (fired
frequently by an external scheduler) drain it one deal at a time, so the
channel gets a steady drip instead of bursts.

Stateless: all memory lives in Supabase. Any single stage failing degrades
gracefully rather than aborting the whole run.
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
import time
from datetime import UTC, datetime
from urllib.parse import urlsplit

# Windows consoles default to cp1252, which chokes on emoji in deal copy.
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

from app import affiliate, filters, resolver
from app.ai import gemini
from app.config import get_settings
from app.models import Deal
from app.sources import amazon, gatry, mercadolivre, pechinchou, pelando, promobit
from app.sources.base import get, meta_image
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


def record_run_stats(started_at: str, counters: dict, sources: dict) -> None:
    db = _db()
    if not db:
        return
    from app.notify.telegram import get_member_count
    try:
        db.record_run(started_at, counters, sources,
                      subscribers=get_member_count())
    except Exception as exc:
        log.warning("record_run failed: %s", exc)


def _already_queued(deal: Deal) -> bool:
    db = _db()
    if not db:
        return False
    try:
        return db.is_queued(deal.key)
    except Exception as exc:
        log.warning("queue check failed: %s", exc)
        return False


def enqueue(deal: Deal) -> None:
    db = _db()
    if not db:
        log.warning("no DB configured; cannot queue %s", deal.title)
        return
    try:
        db.enqueue_post({
            "url_key": deal.key,
            "title": deal.title,
            "short_title": deal.short_title,
            "store": deal.store,
            "price": deal.price,
            "discount_pct": deal.discount_pct,
            "coupon": deal.coupon,
            "category": deal.category,
            "score": deal.score,
            "url": deal.url,
            "image_url": deal.image_url,
        })
        log.info("queued: %s", deal.short_title or deal.title)
    except Exception as exc:
        log.warning("enqueue failed: %s", exc)


def _quiet_channel_watchdog() -> None:
    """Alert the admin when the channel has been silent too long.

    Runs on every (15-min) post run; the modulo window fires the alert once
    per multiple of `alert_quiet_hours` instead of spamming every run.
    """
    db = _db()
    s = get_settings()
    if not db or not s.admin_chat_id:
        return
    try:
        last = db.last_posted_at()
    except Exception as exc:
        log.warning("watchdog check failed: %s", exc)
        return
    if last is None:
        return
    hours_since = (datetime.now(UTC) - last).total_seconds() / 3600
    if hours_since < s.alert_quiet_hours:
        return
    # Fire only in a ~20-min window right after each threshold multiple.
    if (hours_since % s.alert_quiet_hours) * 60 < 20:
        from app.notify.telegram import send_admin
        send_admin(
            f"⚠️ <b>Canal mudo há {hours_since:.0f}h</b>\n"
            f"Fila vazia e sem posts desde então — verificar coleta "
            f"(fontes/validação) no GitHub Actions."
        )
        log.warning("quiet-channel alert sent (%.1fh without posts)", hours_since)


def post_from_queue(limit: int = 1) -> None:
    """Drain up to `limit` pending deals from the queue to the channel."""
    db = _db()
    if not db:
        log.error("no DB configured; nothing to post")
        return
    from app.notify.telegram import send_deal

    try:
        rows = db.fetch_pending_posts(limit)
    except Exception as exc:
        log.error("queue fetch failed: %s", exc)
        return
    if not rows:
        log.info("queue empty; nothing to post")
        _quiet_channel_watchdog()
        return

    for row in rows:
        deal = Deal(title=row["title"], store=row.get("store") or "",
                    url=row["url"],
                    price=float(row["price"]) if row.get("price") else None,
                    coupon=row.get("coupon"))
        deal.short_title = row.get("short_title")
        deal.image_url = row.get("image_url")
        deal.discount_pct = (
            float(row["discount_pct"]) if row.get("discount_pct") else None
        )
        deal.category = row.get("category")
        deal.score = row.get("score")
        try:
            send_deal(deal)
        except Exception as exc:
            log.error("send failed for queue id %s: %s", row["id"], exc)
            continue
        try:
            # Dedupe record keyed on the ORIGINAL product key, not the
            # resolved URL's — same identity the collect run checks.
            db.record_posted_deal(row["url_key"], deal.title, deal.store,
                                  deal.price, deal.coupon, deal.score,
                                  deal.category)
            db.mark_queue_posted(row["id"])
        except Exception as exc:
            log.warning("post bookkeeping failed for id %s: %s", row["id"], exc)
        log.info("posted from queue: %s", deal.short_title or deal.title)
        time.sleep(random.uniform(0.5, 1.5))


# ------------------------------- stages --------------------------------------

def gather() -> list[Deal]:
    deals: dict[str, Deal] = {}
    for src in (promobit, pelando, gatry, pechinchou):
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


def fetch_image(url: str) -> str | None:
    """Product photo (og:image) from the final store page. Fail-soft: a
    missing/unreachable image never blocks a post, Telegram just falls back
    to a text-only message."""
    try:
        resp = get(url)
        resp.raise_for_status()
    except Exception as exc:
        log.info("image fetch failed (%s): %s", url[:60], exc)
        return None
    return meta_image(resp.text)


def _priority(deal: Deal) -> float:
    """Rank candidates so expensive steps hit the best ones first."""
    if deal.list_price and deal.price and deal.list_price > deal.price:
        return (deal.list_price - deal.price) / deal.list_price
    return 0.0


def run(dry_run: bool = False) -> None:
    s = get_settings()
    started_at = datetime.now(UTC).isoformat()

    all_deals = gather()
    sources_mix: dict[str, int] = {}
    for d in all_deals:
        sources_mix[d.source] = sources_mix.get(d.source, 0) + 1

    counters = {
        "gathered": len(all_deals), "posted": 0, "skipped_store": 0,
        "skipped_tech": 0, "skipped_validation": 0, "skipped_ai": 0,
        "skipped_dupe": 0, "skipped_resolve": 0,
    }

    # Curation gates (store whitelist + tech keywords) before anything costly.
    candidates: list[Deal] = []
    for deal in all_deals:
        ok, why = filters.passes(deal)
        if ok:
            candidates.append(deal)
        elif why.startswith("store"):
            counters["skipped_store"] += 1
        else:
            counters["skipped_tech"] += 1
    log.info("curation: %d/%d candidates (store -%d, tech -%d)",
             len(candidates), len(all_deals),
             counters["skipped_store"], counters["skipped_tech"])

    candidates.sort(key=_priority, reverse=True)
    candidates = candidates[: s.max_deals_per_run]

    for deal in candidates:
        confirm_price(deal)

        # Judge against prior history, THEN record this observation (so the
        # current price never pollutes its own median).
        verdict = validate(deal)
        record_price(deal)  # build the series (happens even in dry-run)
        if not verdict.is_real_drop:
            counters["skipped_validation"] += 1
            log.info("skip (validation): %s — %s", deal.title, verdict.reason)
            continue

        if not checkout_sim.verify_coupon(deal):
            counters["skipped_validation"] += 1
            log.info("skip (coupon invalid): %s", deal.title)
            continue

        evaluation = gemini.evaluate(deal)
        if evaluation is None:
            counters["skipped_ai"] += 1
            log.info("skip (no AI eval): %s", deal.title)
            continue
        deal.score = evaluation.score
        deal.short_title = evaluation.short_title
        deal.reason = evaluation.reason
        deal.category = evaluation.category or None
        if s.tech_only and not evaluation.is_tech:
            counters["skipped_tech"] += 1
            log.info("skip (not tech, AI: %s): %s", evaluation.category, deal.title)
            continue
        if not evaluation.legit or evaluation.score < s.min_score:
            counters["skipped_ai"] += 1
            log.info("skip (score %s): %s — %s", evaluation.score, deal.title,
                     evaluation.reason)
            continue

        if already_posted(deal) or _already_queued(deal):
            counters["skipped_dupe"] += 1
            log.info("skip (already posted/queued): %s", deal.title)
            continue

        # Swap in a validated direct product URL (per-source strategy in
        # app/resolver.py). No valid link = don't post at all — a generic or
        # broken link is worse than no post. Dedupe keys stay on the original.
        direct = resolver.resolve_posting_url(deal)
        if not direct:
            counters["skipped_resolve"] += 1
            log.info("skip (no direct store link): %s", deal.title)
            continue
        deal.url = direct
        deal.image_url = fetch_image(deal.url)

        # Attach affiliate identity (no-op until env vars are configured).
        deal.url = affiliate.apply(deal.url, deal.store)

        if dry_run:
            print(_preview(deal))
        else:
            enqueue(deal)
        counters["posted"] += 1  # semantics: approved into the posting queue

        time.sleep(random.uniform(0.5, 1.5))  # be polite between deals

    verb = "would post" if dry_run else "posted"
    log.info("done. %s %d deals | %s", verb, counters["posted"],
             {k: v for k, v in counters.items() if k != "posted"})
    if not dry_run:
        record_run_stats(started_at, counters, sources_mix)


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
        f"short:    {deal.short_title}\n"
        f"url:      {deal.url}\n"
        f"image:    {deal.image_url}"
    )


def _init_sentry() -> None:
    """Error tracking, active only when SENTRY_DSN is set (no-op otherwise)."""
    import os
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=dsn, traces_sample_rate=0, environment="production")
        log.info("sentry enabled")
    except Exception as exc:
        log.warning("sentry init failed: %s", exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Brazilian deal bot pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="collect, but print candidates instead of queueing")
    parser.add_argument("--post-queue", type=int, metavar="N", default=None,
                        help="post up to N pending deals from the queue and exit")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _init_sentry()
    if args.post_queue is not None:
        post_from_queue(limit=max(1, args.post_queue))
    else:
        run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
