from app import affiliate
from app.config import get_settings


def test_no_config_is_passthrough():
    url = "https://www.amazon.com.br/dp/B1"
    assert affiliate.apply(url, "Amazon") == url


def test_amazon_tag_appended(monkeypatch):
    monkeypatch.setenv("AMAZON_ASSOC_TAG", "meucanal-20")
    get_settings.cache_clear()
    out = affiliate.apply("https://www.amazon.com.br/dp/B1", "Amazon")
    assert "tag=meucanal-20" in out


def test_amazon_tag_appends_to_existing_query(monkeypatch):
    monkeypatch.setenv("AMAZON_ASSOC_TAG", "meucanal-20")
    get_settings.cache_clear()
    out = affiliate.apply("https://www.amazon.com.br/dp/B1?th=1", "Amazon")
    assert out.count("?") == 1 and "th=1" in out and "tag=meucanal-20" in out


def test_ml_tool_id(monkeypatch):
    monkeypatch.setenv("ML_AFFILIATE_TOOL_ID", "12345")
    get_settings.cache_clear()
    out = affiliate.apply("https://www.mercadolivre.com.br/p/MLB1", "Mercado Livre")
    assert "matt_tool=12345" in out and "matt_word=12345" in out


def test_config_for_other_store_untouched(monkeypatch):
    monkeypatch.setenv("AMAZON_ASSOC_TAG", "meucanal-20")
    get_settings.cache_clear()
    url = "https://shopee.com.br/product/1"
    assert affiliate.apply(url, "Shopee") == url
