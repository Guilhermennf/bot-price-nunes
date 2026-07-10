from app.filters import looks_tech, passes
from app.models import Deal
from app.stores import identify, is_dead_redirect, store_from_url


def make_deal(title="Notebook Gamer", store="Amazon",
              url="https://www.amazon.com.br/dp/B1"):
    return Deal(title=title, store=store, url=url)


# --- tech keywords ---

def test_tech_titles_pass():
    for title in (
        "Smartphone Samsung Galaxy S26",
        "Fone de Ouvido Bluetooth JBL",
        "SSD NVMe 1TB Kingston",
        "Console PlayStation 5 Slim",
        "Câmera de segurança wi-fi",
    ):
        assert looks_tech(title), title


def test_non_tech_titles_fail():
    for title in (
        "Camisa Polo Masculina Algodão",
        "Perfume Árabe Feminino 100ml",
        "Cômoda 4 Gavetas Quarto Casal",
        "Azeite de Oliva Extra Virgem 500ml",
    ):
        assert not looks_tech(title), title


def test_accent_insensitive():
    assert looks_tech("CÂMERA GoPro Hero")
    assert looks_tech("Robo aspirador inteligente")


# --- store identity ---

def test_store_from_url_matches_subdomains():
    assert store_from_url("https://pt.aliexpress.com/item/1.html") == "aliexpress"
    assert store_from_url("https://produto.mercadolivre.com.br/MLB-1") == "mercadolivre"
    assert store_from_url("https://www.magazinevoce.com.br/x") == "magalu"


def test_store_name_aliases():
    assert identify("Magazine Luiza", None) == "magalu"
    assert identify("Mercado Livre", None) == "mercadolivre"
    assert identify("KaBuM!", None) is None


def test_dead_redirect_hosts():
    assert is_dead_redirect("https://click.linksynergy.com/fs-bin/click?id=x")
    assert is_dead_redirect("https://www.promobit.com.br/promocoes/")
    assert not is_dead_redirect("https://www.amazon.com.br/dp/B1")


# --- combined gate ---

def test_passes_whitelisted_tech_deal():
    ok, why = passes(make_deal())
    assert ok, why


def test_rejects_non_whitelisted_store():
    ok, why = passes(make_deal(store="KaBuM!", url="https://www.kabum.com.br/p/1"))
    assert not ok and why.startswith("store")


def test_rejects_non_tech_title():
    ok, why = passes(make_deal(title="Camisa Polo Piquet"))
    assert not ok and "tech" in why


def test_pelando_deal_allowed_by_url_host_alone():
    # Pelando sometimes carries a store display name we don't alias, but the
    # sourceUrl host is authoritative.
    ok, _ = passes(make_deal(store="Loja Estranha",
                             url="https://shopee.com.br/product/123"))
    assert ok
