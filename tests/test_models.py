from app.models import Deal, normalize_url, url_key


def test_normalize_strips_tracking_params():
    url = ("https://www.mercadolivre.com.br/produto/p/MLB123"
           "?matt_tool=abc&matt_word=xyz&utm_source=promobit&ref=home&pdp_filters=x")
    assert normalize_url(url) == "https://www.mercadolivre.com.br/produto/p/MLB123"


def test_normalize_keeps_functional_params():
    url = "https://pt.aliexpress.com/item/100500.html?spm=keep&sku_id=12345"
    normalized = normalize_url(url)
    assert "sku_id=12345" in normalized


def test_normalize_strips_affiliate_families():
    url = "https://www.lg.com/br/tv?aw_affid=1&awc=2_3_4&aff_fcid=deadbeef&af=1"
    assert normalize_url(url) == "https://www.lg.com/br/tv"


def test_normalize_lowercases_host_and_drops_fragment():
    assert normalize_url("https://WWW.Amazon.COM.BR/dp/B0ABC#reviews") == (
        "https://www.amazon.com.br/dp/B0ABC"
    )


def test_url_key_stable_across_tracking_variants():
    a = url_key("https://www.amazon.com.br/dp/B0ABC?tag=promo&utm_medium=feed")
    b = url_key("https://www.amazon.com.br/dp/B0ABC")
    assert a == b


def test_deal_computes_key_on_init():
    deal = Deal(title="X", store="Amazon", url="https://www.amazon.com.br/dp/B1?utm_source=x")
    assert deal.key == url_key("https://www.amazon.com.br/dp/B1")
    assert "utm_source" not in deal.url
