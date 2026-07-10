"""Validation logic with mocked history stats (no DB)."""

from app.db.supabase_client import PriceStats
from app.models import Deal
from app.validation import price_history


def make_deal(price=100.0, list_price=None):
    return Deal(title="SSD 1TB", store="Amazon",
                url="https://www.amazon.com.br/dp/B1",
                price=price, list_price=list_price)


def mock_stats(monkeypatch, count, minimum, median):
    monkeypatch.setattr(
        price_history, "_safe_stats",
        lambda key, window: PriceStats(count=count, minimum=minimum, median=median),
    )


def test_real_drop_passes(monkeypatch):
    mock_stats(monkeypatch, count=10, minimum=90.0, median=140.0)
    verdict = price_history.validate(make_deal(price=100.0))
    assert verdict.is_real_drop
    assert verdict.discount_pct and verdict.discount_pct >= 25


def test_fake_de_por_rejected(monkeypatch):
    # store claims list 999 -> 500, but median says it always costs ~505
    mock_stats(monkeypatch, count=10, minimum=490.0, median=505.0)
    verdict = price_history.validate(make_deal(price=500.0, list_price=999.0))
    assert not verdict.is_real_drop  # only ~1% below median


def test_no_history_with_solid_claimed_discount_passes(monkeypatch):
    mock_stats(monkeypatch, count=0, minimum=None, median=None)
    verdict = price_history.validate(make_deal(price=60.0, list_price=100.0))
    assert verdict.is_real_drop
    assert verdict.discount_pct == 40.0


def test_no_history_no_list_price_passes_to_ai(monkeypatch):
    mock_stats(monkeypatch, count=0, minimum=None, median=None)
    verdict = price_history.validate(make_deal(price=60.0))
    assert verdict.is_real_drop  # first observation: AI is the second gate
    assert verdict.discount_pct is None


def test_unusable_price_rejected(monkeypatch):
    mock_stats(monkeypatch, count=5, minimum=10.0, median=20.0)
    verdict = price_history.validate(make_deal(price=0))
    assert not verdict.is_real_drop


def test_db_outage_degrades_to_no_history(monkeypatch):
    def boom(key, window):
        raise RuntimeError("supabase down")

    monkeypatch.setattr(price_history, "get_price_stats", boom)
    # goes through _safe_stats which catches -> treated as first observation
    verdict = price_history.validate(make_deal(price=60.0, list_price=100.0))
    assert verdict.is_real_drop
