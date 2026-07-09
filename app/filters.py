"""Gather-stage filters: store whitelist + tech keyword pre-filter.

The keyword layer is deliberately INCLUSIVE (broad terms, accents optional):
its only job is to cheaply discard obvious non-tech before spending Gemini
quota. The strict verdict is Gemini's ``is_tech`` (layer 2, app/ai/gemini.py).
"""

from __future__ import annotations

import unicodedata

from app.config import get_settings
from app.models import Deal
from app.stores import identify

# Broad tech vocabulary (matched accent-insensitively on the title).
TECH_KEYWORDS = (
    # computing
    "notebook", "laptop", "pc ", "desktop", "computador", "monitor", "ssd",
    "hd ", "nvme", "memoria ram", "memória ram", " ram ", "processador",
    "cpu", "gpu", "placa de video", "placa-mae", "placa mae", "gabinete",
    "fonte atx", "water cooler", "cooler",
    # phones & wearables
    "smartphone", "celular", "iphone", "galaxy", "xiaomi", "redmi", "poco",
    "motorola", "smartwatch", "relogio inteligente", "band ", "tablet", "ipad",
    "carregador", "power bank", "powerbank", "cabo usb", "usb-c", "type-c",
    # audio & video
    "fone", "headset", "headphone", "earbud", "caixa de som", "soundbar",
    "home theater", "microfone", "tv ", "smart tv", "projetor", "chromecast",
    "fire tv", "roku", "camera", "câmera", "webcam", "gopro", "drone",
    # gaming
    "console", "playstation", "ps5", "ps4", "xbox", "nintendo", "switch",
    "controle", "joystick", "gamer", "steam deck", "jogo ", "game ",
    # networking & smart home
    "roteador", "router", "wi-fi", "wifi", "mesh", "repetidor", "alexa",
    "echo dot", "echo ", "google home", "lampada inteligente", "smart home",
    "assistente virtual", "robo aspirador", "robô aspirador",
    # peripherals & office tech
    "teclado", "mouse", "mousepad", "impressora", "scanner", "nobreak",
    "estabilizador", "hub usb", "dock", "pen drive", "cartao de memoria",
    "cartão de memória", "micro sd", "microsd", "kindle", "e-reader",
    "cadeira gamer", "suporte monitor",
)


def _fold(text: str) -> str:
    """Lowercase + strip accents for robust keyword matching."""
    norm = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in norm if not unicodedata.combining(c))


def looks_tech(title: str) -> bool:
    folded = " " + _fold(title) + " "
    return any(_fold(kw) in folded for kw in TECH_KEYWORDS)


def allowed_store(deal: Deal) -> bool:
    """True if the deal belongs to one of the whitelisted stores."""
    allowed = get_settings().allowed_stores_set()
    if not allowed:
        return True
    store_id = identify(deal.store, deal.url)
    return store_id in allowed


def passes(deal: Deal) -> tuple[bool, str]:
    """Combined gather-stage verdict: (passes, reason-if-not)."""
    if not allowed_store(deal):
        return False, "store not whitelisted"
    if get_settings().tech_only and not looks_tech(deal.title):
        return False, "not tech (keywords)"
    return True, ""
