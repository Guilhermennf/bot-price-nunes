from app.config import get_settings
from app.models import Deal
from app.notify import telegram
from app.notify.telegram import _format_deal, _short_title

from tests.conftest import FakeResponse


def make_deal(**kw):
    deal = Deal(title="Fone Bluetooth JBL Tune 510BT Original Lacrado", store="Amazon",
                url="https://www.amazon.com.br/dp/B1", price=1299.9)
    for k, v in kw.items():
        setattr(deal, k, v)
    return deal


def test_no_header_or_footer():
    msg = _format_deal(make_deal())
    assert "NUNES TECH PROMOS" not in msg
    assert "t.me/" not in msg
    assert "#" not in msg  # no hashtag footer


def test_section_order_and_blank_lines():
    msg = _format_deal(make_deal(coupon="TECH10", discount_pct=35.0, price=649.90))
    lines = msg.split("\n")
    assert lines[0].startswith("🔥")
    assert lines[1] == ""
    assert lines[2].startswith("De R$")
    assert lines[3] == ""
    assert lines[4].startswith("🎟️ Cupom")
    assert lines[5].startswith("🏬")
    assert lines[6] == ""
    assert lines[7].startswith("🛒")


def test_brl_price_formatting_no_discount():
    msg = _format_deal(make_deal(price=1299.9))
    assert "R$ 1.299,90" in msg
    assert "De R$" not in msg


def test_de_por_price_with_discount():
    msg = _format_deal(make_deal(price=649.90, discount_pct=35.0))
    # from_price = 649.90 / (1 - 0.35) = 999.846...
    assert "De R$ 999,8" in msg
    assert "por <b>R$ 649,90</b>" in msg
    assert "(−35%)" in msg


def test_zero_or_full_discount_falls_back_to_plain_price():
    msg = _format_deal(make_deal(price=100.0, discount_pct=0))
    assert "<b>R$ 100,00</b>" in msg and "De R$" not in msg
    msg2 = _format_deal(make_deal(price=100.0, discount_pct=100.0))
    assert "<b>R$ 100,00</b>" in msg2 and "De R$" not in msg2


def test_coupon_in_code_block():
    msg = _format_deal(make_deal(coupon="TECH10"))
    assert "<code>TECH10</code>" in msg


def test_no_coupon_line_when_absent():
    msg = _format_deal(make_deal(coupon=None))
    assert "Cupom" not in msg


def test_link_hidden_behind_comprar_agora_label():
    msg = _format_deal(make_deal())
    assert '<a href="https://www.amazon.com.br/dp/B1">COMPRAR AGORA</a>' in msg


def test_link_param_overrides_deal_url_but_label_stays():
    msg = _format_deal(make_deal(), link="https://www.amazon.com.br/dp/OTHER")
    assert '<a href="https://www.amazon.com.br/dp/OTHER">COMPRAR AGORA</a>' in msg
    assert "/dp/B1" not in msg


# --- short title: AI-provided, capped at 6 words, escaped ---

def test_short_title_used_when_present():
    msg = _format_deal(make_deal(short_title="Fone JBL Tune 510BT"))
    assert "Fone JBL Tune 510BT" in msg
    assert "Original Lacrado" not in msg


def test_short_title_falls_back_to_truncated_raw_title():
    deal = make_deal(short_title=None)
    deal.title = "Notebook Gamer Acer Nitro V15 Intel Core i7 16GB 512GB RTX"
    assert _short_title(deal) == "Notebook Gamer Acer Nitro V15 Intel"


def test_short_title_html_escaped():
    msg = _format_deal(make_deal(short_title='TV 50" <Promo> & Cia'))
    assert "&lt;Promo&gt;" in msg and "&amp;" in msg


# --- send_deal: photo when we have an image, plain text (preview off) otherwise ---

def _mock_telegram(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "test-chat")
    get_settings.cache_clear()
    calls = []

    def fake_post(url, json=None, timeout=None):
        calls.append((url, json))
        return FakeResponse(json_data={"ok": True})

    monkeypatch.setattr(telegram.httpx, "post", fake_post)
    return calls


def test_send_deal_uses_sendphoto_when_image_present(monkeypatch):
    calls = _mock_telegram(monkeypatch)
    deal = make_deal(image_url="https://example.com/product.jpg")

    telegram.send_deal(deal)

    assert len(calls) == 1
    url, payload = calls[0]
    assert url.endswith("/sendPhoto")
    assert payload["photo"] == "https://example.com/product.jpg"
    assert payload["caption"] == _format_deal(deal)


def test_send_deal_falls_back_to_text_without_image(monkeypatch):
    calls = _mock_telegram(monkeypatch)
    deal = make_deal(image_url=None)

    telegram.send_deal(deal)

    assert len(calls) == 1
    url, payload = calls[0]
    assert url.endswith("/sendMessage")
    assert payload["disable_web_page_preview"] is True
    assert payload["text"] == _format_deal(deal)


def test_send_deal_falls_back_when_sendphoto_fails(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "test-chat")
    get_settings.cache_clear()
    calls = []

    def fake_post(url, json=None, timeout=None):
        if url.endswith("/sendPhoto"):
            return FakeResponse(status=400)
        calls.append((url, json))
        return FakeResponse(json_data={"ok": True})

    monkeypatch.setattr(telegram.httpx, "post", fake_post)
    deal = make_deal(image_url="https://example.com/broken.jpg")

    telegram.send_deal(deal)

    assert len(calls) == 1
    assert calls[0][0].endswith("/sendMessage")
