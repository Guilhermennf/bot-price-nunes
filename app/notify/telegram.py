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


CHANNEL_NAME = "NUNES TECH PROMOS"
CHANNEL_LINK = "t.me/nunestechpromos"


def _hashtag(category: str | None) -> str | None:
    """Turn Gemini's category into a channel hashtag: 'placa de vídeo' -> #placadevideo."""
    if not category:
        return None
    import re
    import unicodedata
    folded = unicodedata.normalize("NFKD", category.lower())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]", "", folded)
    return f"#{slug}" if slug else None


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


def _format_deal(deal: Deal) -> str:
    """Branded channel message: título curto / preço / cupom / loja / link."""
    lines: list[str] = [f"⚡ <b>{CHANNEL_NAME}</b>", ""]

    lines.append(f"🔥 <b>{html.escape(_short_title(deal))}</b>")
    lines.append("")

    price_line = _price_line(deal)
    if price_line:
        lines.append(price_line)

    if deal.coupon:
        lines.append(f"🎟️ Cupom: <code>{html.escape(deal.coupon)}</code>")

    if deal.store:
        lines.append(f"🏬 {html.escape(deal.store)}")

    lines.append(f'🛒 <a href="{html.escape(deal.url)}">COMPRAR AGORA</a>')

    footer = [_hashtag(deal.category), f"➡️ {CHANNEL_LINK}"]
    lines.extend(["", " · ".join(p for p in footer if p)])
    return "\n".join(lines)


def send_deal(deal: Deal) -> dict:
    """Post a formatted deal (link preview ON so the product image shows)."""
    return send_message(_format_deal(deal), disable_preview=False)


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "test ✅"
    print(send_message(msg))
