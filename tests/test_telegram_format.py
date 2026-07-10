from app.models import Deal
from app.notify.telegram import CHANNEL_LINK, _format_deal, _hashtag


def make_deal(**kw):
    deal = Deal(title="Fone Bluetooth JBL", store="Amazon",
                url="https://www.amazon.com.br/dp/B1", price=1299.9)
    for k, v in kw.items():
        setattr(deal, k, v)
    return deal


def test_branded_header_and_footer():
    msg = _format_deal(make_deal())
    assert msg.startswith("⚡ <b>NUNES TECH PROMOS</b>")
    assert CHANNEL_LINK in msg


def test_brl_price_formatting():
    msg = _format_deal(make_deal(price=1299.9))
    assert "R$ 1.299,90" in msg


def test_category_hashtag():
    msg = _format_deal(make_deal(category="Placa de Vídeo"))
    assert "#placadevideo" in msg


def test_hashtag_edge_cases():
    assert _hashtag(None) is None
    assert _hashtag("não-tech!") == "#naotech"
    assert _hashtag("...") is None


def test_coupon_in_code_block():
    msg = _format_deal(make_deal(coupon="TECH10"))
    assert "<code>TECH10</code>" in msg


def test_html_escaped_title_fallback():
    deal = make_deal(copy=None)
    deal.title = "TV 50\" <Promo> & Cia"
    msg = _format_deal(deal)
    assert "&lt;Promo&gt;" in msg and "&amp;" in msg
