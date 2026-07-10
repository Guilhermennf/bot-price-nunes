"""Parsers against recorded real-site fixtures (offline)."""

from app.sources import gatry, pechinchou, pelando, promobit

from tests.conftest import FakeResponse


def test_promobit_parses_recorded_page(monkeypatch, promobit_html):
    monkeypatch.setattr(
        promobit, "get", lambda url, **kw: FakeResponse(text=promobit_html)
    )
    deals = promobit.fetch()
    assert len(deals) >= 5
    sample = deals[0]
    assert sample.title
    assert sample.price and sample.price >= 1.0  # sub-R$1 sentinels dropped
    assert sample.url.startswith("https://www.promobit.com.br/oferta/")
    assert sample.source == "promobit"
    assert sample.raw_id.isdigit()


def test_promobit_network_failure_is_soft(monkeypatch):
    def boom(url, **kw):
        raise RuntimeError("blocked")

    monkeypatch.setattr(promobit, "get", boom)
    assert promobit.fetch() == []


def test_pelando_parses_recorded_feed(monkeypatch, pelando_payload):
    monkeypatch.setattr(
        pelando.httpx, "get",
        lambda *a, **kw: FakeResponse(json_data=pelando_payload),
    )
    deals = pelando.fetch()
    assert len(deals) >= 5
    sample = deals[0]
    assert sample.title
    assert sample.price and sample.price >= 1.0
    assert sample.source == "pelando"
    # coupon-only entries (price null) must be filtered out
    assert all(d.price is not None for d in deals)


def test_pelando_shape_change_is_soft(monkeypatch):
    monkeypatch.setattr(
        pelando.httpx, "get",
        lambda *a, **kw: FakeResponse(json_data={"data": {"unexpected": []}}),
    )
    assert pelando.fetch() == []


def test_gatry_parses_recorded_page(monkeypatch, gatry_html):
    monkeypatch.setattr(
        gatry, "get", lambda url, **kw: FakeResponse(text=gatry_html)
    )
    deals = gatry.fetch()
    assert len(deals) >= 5
    sample = deals[0]
    assert sample.title
    assert sample.price and sample.price >= 1.0
    assert sample.url.startswith("http")
    assert sample.source == "gatry"
    assert sample.store  # "Ir para" prefix stripped
    assert not sample.store.startswith("Ir para")


def test_gatry_network_failure_is_soft(monkeypatch):
    def boom(url, **kw):
        raise RuntimeError("blocked")

    monkeypatch.setattr(gatry, "get", boom)
    assert gatry.fetch() == []


def test_pechinchou_parses_recorded_page(monkeypatch, pechinchou_html):
    monkeypatch.setattr(
        pechinchou, "get", lambda url, **kw: FakeResponse(text=pechinchou_html)
    )
    deals = pechinchou.fetch()
    assert len(deals) >= 10
    sample = deals[0]
    assert sample.title
    assert sample.price and sample.price >= 1.0
    assert sample.source == "pechinchou"
    assert sample.store
    # old_price feeds list_price when present
    assert any(d.list_price for d in deals)
    # coupons come through as plain strings
    assert all(isinstance(d.coupon, str) for d in deals if d.coupon)


def test_pechinchou_shape_change_is_soft(monkeypatch):
    monkeypatch.setattr(
        pechinchou, "get",
        lambda url, **kw: FakeResponse(
            text='<html><body><script id="__NEXT_DATA__" type="application/json">'
                 '{"props":{"pageProps":{}}}</script></body></html>'
        ),
    )
    assert pechinchou.fetch() == []
