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

_API = "https://api.telegram.org/bot{token}/{method}"


def send_message(text: str, disable_preview: bool = False,
                 chat_id: str | None = None) -> dict:
    s = get_settings()
    chat_id = chat_id or s.telegram_chat_id
    if not s.telegram_bot_token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not configured")
    resp = httpx.post(
        _API.format(token=s.telegram_bot_token, method="sendMessage"),
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_preview,
        },
        timeout=s.request_timeout,
    )
    resp.raise_for_status()
    return resp.json()


def send_admin(text: str) -> None:
    """Operational alert to the admin's private chat. Fail-soft, optional."""
    s = get_settings()
    if not s.admin_chat_id:
        return
    try:
        send_message(text, disable_preview=True, chat_id=s.admin_chat_id)
    except Exception as exc:
        log.warning("admin alert failed: %s", exc)


def get_member_count() -> int | None:
    """Subscriber count of the channel (fail-soft)."""
    s = get_settings()
    if not s.telegram_bot_token or not s.telegram_chat_id:
        return None
    try:
        resp = httpx.get(
            _API.format(token=s.telegram_bot_token, method="getChatMemberCount"),
            params={"chat_id": s.telegram_chat_id},
            timeout=s.request_timeout,
        )
        resp.raise_for_status()
        return int(resp.json()["result"])
    except Exception as exc:
        log.info("getChatMemberCount failed: %s", exc)
        return None


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

    sections.append(f'🛒 <a href="{html.escape(link)}">COMPRAR AGORA</a>')

    return "\n\n".join(sections)


def send_deal(deal: Deal) -> dict:
    """Post a formatted deal (link preview ON so the product image shows)."""
    return send_message(_format_deal(deal), disable_preview=False)


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "test ✅"
    print(send_message(msg))
