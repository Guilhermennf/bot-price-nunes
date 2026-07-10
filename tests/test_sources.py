"""Parsers against recorded real-site fixtures (offline)."""

from app.sources import pelando, promobit

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
