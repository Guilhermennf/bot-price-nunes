"""One-way Telegram notification via the raw Bot API.

CLI smoke test:  python -m app.notify.telegram "test message"
"""

from __future__ import annotations

import html
import sys

import httpx

from app.config import get_settings
from app.models import Deal

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


def _format_deal(deal: Deal) -> str:
    """Build the HTML message body from the (AI-written) copy + facts."""
    lines: list[str] = []
    if deal.copy:
        lines.append(deal.copy.strip())
    else:
        lines.append(f"🔥 <b>{html.escape(deal.title)}</b>")

    if deal.price is not None:
        price_line = f"💰 <b>R$ {deal.price:.2f}</b>"
        if deal.discount_pct:
            price_line += f"  (−{deal.discount_pct:.0f}%)"
        lines.append(price_line)

    if deal.coupon:
        lines.append(f"🎟️ Cupom: <code>{html.escape(deal.coupon)}</code>")

    if deal.store:
        lines.append(f"🏬 {html.escape(deal.store)}")

    lines.append(f'🔗 <a href="{html.escape(deal.url)}">Ver oferta</a>')
    return "\n".join(lines)


def send_deal(deal: Deal) -> dict:
    """Post a formatted deal (link preview ON so the product image shows)."""
    return send_message(_format_deal(deal), disable_preview=False)


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "test ✅"
    print(send_message(msg))
