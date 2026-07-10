"""One-way Telegram notification via the raw Bot API.

CLI smoke test:  python -m app.notify.telegram "test message"
"""

from __future__ import annotations

import html
import logging
import sys

import httpx

from app.config import get_settings
from app.models import Deal

log = logging.getLogger(__name__)

_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_message(text: str, disable_preview: bool = False) -> dict:
    s = get_settings()
    if not s.telegram_bot_token or not s.telegram_chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not configured")
    resp = httpx.post(
        _API.format(token=s.telegram_bot_token),
        json={
            "chat_id": s.telegram_chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_preview,
        },
        timeout=s.request_timeout,
    )
    resp.raise_for_status()
    return resp.json()


def shorten_url(url: str) -> str:
    """Shorten a URL via TinyURL's free, keyless API.

    Fails soft: any error (network, non-2xx, empty/odd body) returns the
    original URL unchanged rather than blocking the post.
    """
    try:
        resp = httpx.get(
            "https://tinyurl.com/api-create.php",
            params={"url": url},
            timeout=10,
        )
        resp.raise_for_status()
        short = resp.text.strip()
        if short.startswith("http"):
            return short
    except Exception as exc:
        log.info("shorten_url failed, using original link: %s", exc)
    return url


def _brl(value: float) -> str:
    return f"{value:,.2f}".replace(",", "\0").replace(".", ",").replace("\0", ".")


def _short_title(deal: Deal) -> str:
    """The AI-written ≤6-word product name, or a truncated fallback."""
    title = (deal.short_title or "").strip() or deal.title
    return " ".join(title.split()[:6])


def _price_line(deal: Deal) -> str | None:
    """'De X por Y (−N%)' when there's a real discount, else just the price.

    The "de" reference is reconstructed from discount_pct rather than
    list_price, since discount_pct is always populated consistently (against
    list_price OR our own tracked median — see validation/price_history.py)
    while list_price often isn't set by the source at all.
    """
    if deal.price is None:
        return None
    if deal.discount_pct and 0 < deal.discount_pct < 100:
        from_price = deal.price / (1 - deal.discount_pct / 100)
        return (f"De R$ {_brl(from_price)} por <b>R$ {_brl(deal.price)}</b>"
                f"  (−{deal.discount_pct:.0f}%)")
    return f"<b>R$ {_brl(deal.price)}</b>"


def _format_deal(deal: Deal, link: str | None = None) -> str:
    """Structured message: título / preço / cupom+loja / link — blank-line
    separated sections, no header or footer."""
    link = link or deal.url
    sections: list[str] = [f"🔥 <b>{html.escape(_short_title(deal))}</b>"]

    price_line = _price_line(deal)
    if price_line:
        sections.append(price_line)

    facts = []
    if deal.coupon:
        facts.append(f"🎟️ Cupom: <code>{html.escape(deal.coupon)}</code>")
    if deal.store:
        facts.append(f"🏬 {html.escape(deal.store)}")
    if facts:
        sections.append("\n".join(facts))

    sections.append(f'🛒 <a href="{html.escape(link)}">{html.escape(link)}</a>')

    return "\n\n".join(sections)


def send_deal(deal: Deal) -> dict:
    """Post a formatted deal with a shortened store link (link preview ON so
    the product image still shows)."""
    short_link = shorten_url(deal.url)
    return send_message(_format_deal(deal, link=short_link), disable_preview=False)


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "test ✅"
    print(send_message(msg))
