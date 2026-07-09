"""Gemini evaluation: is the discount legit, and write PT-BR sales copy.

Called only for candidates that already passed price-history validation, to
stay inside the free-tier quota. Uses structured JSON output.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.config import get_settings
from app.models import Deal

log = logging.getLogger(__name__)

_PROMPT = """Você é um curador de ofertas para um canal de promoções brasileiro.
Avalie se esta é uma oferta REALMENTE boa (desconto legítimo, não preço inflado).

Produto: {title}
Loja: {store}
Preço atual: R$ {price}
Preço de tabela informado: {list_price}
Mediana histórica ({window}d): {median}
Menor preço já visto: {hist_min}
Desconto calculado: {discount}%
Cupom: {coupon}

Responda em JSON com:
- legit (bool): o desconto é real e vale a pena?
- score (0-100): quão boa é a oferta
- reason (string, curto): justificativa objetiva
- copy (string): texto persuasivo em PT-BR para o canal, com emojis, 1-3 linhas,
  destacando o desconto e o cupom se houver. NÃO invente preços nem repita o link.
"""


@dataclass
class Evaluation:
    legit: bool
    score: int
    reason: str
    copy: str


def _fmt(v) -> str:
    return f"R$ {v:.2f}" if isinstance(v, (int, float)) else "desconhecido"


def evaluate(deal: Deal) -> Evaluation | None:
    s = get_settings()
    if not s.gemini_api_key:
        log.warning("GEMINI_API_KEY not configured; skipping AI evaluation")
        return None

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        log.error("google-genai not installed")
        return None

    client = genai.Client(api_key=s.gemini_api_key)
    prompt = _PROMPT.format(
        title=deal.title,
        store=deal.store or "?",
        price=f"{deal.price:.2f}" if deal.price else "?",
        list_price=_fmt(deal.list_price),
        window=s.history_window_days,
        median=_fmt(deal.hist_median),
        hist_min=_fmt(deal.hist_min),
        discount=f"{deal.discount_pct:.0f}" if deal.discount_pct is not None else "?",
        coupon=deal.coupon or "nenhum",
    )

    try:
        resp = client.models.generate_content(
            model=s.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
            ),
        )
        data = json.loads(resp.text)
    except Exception as exc:
        log.warning("gemini evaluate failed for %s: %s", deal.title, exc)
        return None

    return Evaluation(
        legit=bool(data.get("legit", False)),
        score=int(data.get("score", 0)),
        reason=str(data.get("reason", "")),
        copy=str(data.get("copy", "")),
    )
