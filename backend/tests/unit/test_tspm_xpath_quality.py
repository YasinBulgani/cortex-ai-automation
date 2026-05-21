"""XPath yardımcıları için birim testleri.

Kapsam:
- _normalize_xpath: absolute prefix, text(), TR translate() sarmalama
- _validate_xpath_syntax: parantez/tırnak/boş adım tespiti
- _score_xpath: stabilite skoru + issue listesi (data-testid, dinamik class, vb.)
- _best_xpath_for_locator: öncelik sırası (data-testid → id → css)
"""

from __future__ import annotations

from app.domains.tspm.router import (
    _best_xpath_for_locator,
    _normalize_xpath,
    _score_xpath,
    _validate_xpath_syntax,
)


# ── normalize ────────────────────────────────────────────────────────

def test_normalize_strips_absolute_html_prefix() -> None:
    assert _normalize_xpath("/html/body/div/button").startswith("/div")
    assert _normalize_xpath("/HTML/BODY/div").startswith("/div")


def test_normalize_keeps_relative_paths() -> None:
    assert _normalize_xpath("//button[@id='x']") == "//button[@id='x']"


def test_normalize_text_to_normalize_space() -> None:
    out = _normalize_xpath("//button[text()='Giriş']")
    assert "normalize-space()" in out  # text() → normalize-space() dönüşümü
    assert "text()=" not in out


def test_normalize_wraps_turkish_literal_with_translate() -> None:
    out = _normalize_xpath("//button[normalize-space()='Giriş Yap']")
    # Türkçe karakter tespit edilince translate() ile sarmalanır
    assert "translate(" in out
    assert "'giriş yap'" in out


def test_normalize_leaves_ascii_literals_untouched() -> None:
    out = _normalize_xpath("//button[normalize-space()='Login']")
    assert "translate(" not in out  # ASCII → gereksiz sarmalama yok


# ── validate ────────────────────────────────────────────────────────

def test_validate_rejects_empty() -> None:
    ok, why = _validate_xpath_syntax("")
    assert not ok and why == "empty"


def test_validate_rejects_non_xpath_prefix() -> None:
    ok, why = _validate_xpath_syntax("button.primary")
    assert not ok and why == "not-xpath"


def test_validate_detects_paren_imbalance() -> None:
    ok, why = _validate_xpath_syntax("//button[contains(@class,'x']")
    assert not ok
    assert why in {"paren-imbalance", "bracket-imbalance"}


def test_validate_detects_empty_step() -> None:
    ok, _ = _validate_xpath_syntax("//")
    assert not ok


def test_validate_accepts_well_formed() -> None:
    ok, why = _validate_xpath_syntax("//button[@id='btn']")
    assert ok and why == ""


# ── score ────────────────────────────────────────────────────────────

def test_score_data_testid_is_top_tier() -> None:
    r = _score_xpath("//*[@data-testid='login-btn']")
    assert r["grade"] == "good"
    assert r["score"] >= 85
    assert "data-testid" in r["strengths"]


def test_score_absolute_path_is_bad() -> None:
    r = _score_xpath("/html/body/div[2]/div[3]/button")
    assert r["grade"] in {"bad", "warn"}
    assert any("absolute" in i for i in r["issues"])


def test_score_numeric_index_penalized() -> None:
    r = _score_xpath("//div[3]/button")
    assert any("numeric index" in i for i in r["issues"])


def test_score_dynamic_class_penalized() -> None:
    r = _score_xpath("//button[contains(@class,'css-1ab2cd')]")
    assert any("dinamik" in i for i in r["issues"])


def test_score_turkish_without_translate_warns() -> None:
    r = _score_xpath("//button[normalize-space()='Giriş Yap']")
    assert any("TR karakter" in i for i in r["issues"])


def test_score_turkish_with_translate_is_fine() -> None:
    r = _score_xpath(
        "//button[translate(normalize-space(.),"
        "'ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ',"
        "'abcçdefgğhıijklmnoöprsştuüvyz')='giriş yap']"
    )
    # translate() olduğu için TR-uyarısı tetiklenmez
    assert not any("TR karakter" in i for i in r["issues"])
    assert "i18n translate()" in r["strengths"]


def test_score_invalid_xpath_returns_invalid() -> None:
    r = _score_xpath("not-an-xpath")
    assert r["grade"] == "invalid"
    assert r["score"] == 0


def test_score_pseudo_selector_is_warn() -> None:
    # css= gibi pseudo biçimler saf XPath değil
    r = _score_xpath("css=.primary-button")
    assert r["grade"] == "warn"


# ── best_xpath_for_locator ──────────────────────────────────────────

def test_best_prefers_data_testid_over_css() -> None:
    loc = {
        "key": "LoginBtn",
        "type": "css",
        "value": ".btn.primary",
        "extras": {"data-testid": "login-btn"},
    }
    out = _best_xpath_for_locator(loc)
    assert "@data-testid='login-btn'" in out


def test_best_uses_primary_xpath_when_present() -> None:
    loc = {
        "key": "SubmitBtn",
        "type": "xpath",
        "value": "//button[@id='submit']",
    }
    assert _best_xpath_for_locator(loc) == "//button[@id='submit']"


def test_best_falls_back_to_id_when_no_xpath() -> None:
    loc = {"key": "UserField", "type": "id", "value": "username"}
    assert _best_xpath_for_locator(loc) == "//*[@id='username']"


def test_best_normalizes_absolute_xpath() -> None:
    loc = {"key": "X", "type": "xpath", "value": "/html/body/div/button"}
    out = _best_xpath_for_locator(loc)
    assert not out.startswith("/html")


def test_best_aria_label_fallback() -> None:
    loc = {
        "key": "MenuBtn",
        "type": "",
        "value": "",
        "aria_label": "Menüyü Aç",
    }
    out = _best_xpath_for_locator(loc)
    assert "@aria-label=" in out
    # Normalize aria-label'ı sadece tek başına değiştirmez (eşitlik wrap'i normalize-space() ile tetiklenir)
    assert "Menüyü" in out or "translate(" in out
