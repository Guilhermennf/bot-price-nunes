"""Posting-time image lookup (fail-soft, store-agnostic og:image fetch)."""

from app import main

from tests.conftest import FakeResponse


def test_fetch_image_returns_og_image(monkeypatch):
    html = '<html><head><meta property="og:image" content="https://store.com/p.jpg"></head></html>'
    monkeypatch.setattr(main, "get", lambda url, **kw: FakeResponse(text=html))
    assert main.fetch_image("https://store.com/product") == "https://store.com/p.jpg"


def test_fetch_image_is_soft_on_network_failure(monkeypatch):
    def boom(url, **kw):
        raise RuntimeError("blocked")

    monkeypatch.setattr(main, "get", boom)
    assert main.fetch_image("https://store.com/product") is None


def test_fetch_image_none_when_no_meta_tag(monkeypatch):
    monkeypatch.setattr(
        main, "get", lambda url, **kw: FakeResponse(text="<html></html>")
    )
    assert main.fetch_image("https://store.com/product") is None
