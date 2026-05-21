"""
tests/e2e/test_login.py — Kimlik Doğrulama E2E testleri.

login.feature dosyasını pytest-bdd @scenario dekoratörü ile bağlar.
Her senaryo bağımsız çalışır ve Allure raporuna entegre edilir.
"""
from __future__ import annotations

import sys
from pathlib import Path

import allure
import pytest
from pytest_bdd import scenario

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from steps.bgts_login_steps import *  # noqa: F401,F403 — step import for discovery

FEATURE = str(ROOT / "features" / "testwright-ai" / "login.feature")


# ═══ BAŞARILI GİRİŞ ═════════════════════════════════════════════════════════

@allure.feature("Kimlik Doğrulama")
@allure.story("Başarılı Giriş")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Geçerli kimlik bilgileri ile başarılı giriş")
def test_successful_login():
    """Geçerli e-posta ve parola ile sisteme giriş."""


@allure.feature("Kimlik Doğrulama")
@allure.story("Başarılı Giriş")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Giriş sonrası projeler sayfasına yönlendirme")
def test_redirect_to_projects_after_login():
    """Başarılı giriş sonrası /projects yönlendirmesi."""


# ═══ BAŞARISIZ GİRİŞ ════════════════════════════════════════════════════════

@allure.feature("Kimlik Doğrulama")
@allure.story("Başarısız Giriş")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Hatalı parola ile giriş reddi")
def test_login_wrong_password():
    """Yanlış parola ile giriş reddedilmeli."""


@allure.feature("Kimlik Doğrulama")
@allure.story("Başarısız Giriş")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Kayıtlı olmayan e-posta ile giriş reddi")
def test_login_unregistered_email():
    """Kayıtlı olmayan e-posta ile giriş reddedilmeli."""


@allure.feature("Kimlik Doğrulama")
@allure.story("Başarısız Giriş")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Boş e-posta alanı ile giriş denemesi")
def test_login_empty_email():
    """Boş e-posta alanı ile giriş yapılamamalı."""


@allure.feature("Kimlik Doğrulama")
@allure.story("Başarısız Giriş")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Boş parola alanı ile giriş denemesi")
def test_login_empty_password():
    """Boş parola alanı ile giriş yapılamamalı."""


# ═══ DEVRE DIŞI HESAP ═══════════════════════════════════════════════════════

@allure.feature("Kimlik Doğrulama")
@allure.story("Devre Dışı Hesap")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Devre dışı hesap ile giriş engeli")
def test_login_disabled_account():
    """Devre dışı bırakılmış hesap ile giriş engellenmeli."""


# ═══ OTURUM BİLGİSİ ═════════════════════════════════════════════════════════

@allure.feature("Kimlik Doğrulama")
@allure.story("Oturum Bilgisi")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Oturum açmış kullanıcı bilgilerini görüntüleme")
def test_view_user_info():
    """Giriş yapan kullanıcı kendi bilgilerini görebilmeli."""


# ═══ ÇIKIŞ ══════════════════════════════════════════════════════════════════

@allure.feature("Kimlik Doğrulama")
@allure.story("Çıkış")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Başarılı oturum kapatma")
def test_logout():
    """Kullanıcı başarıyla çıkış yapabilmeli."""


# ═══ GÜVENLİK ══════════════════════════════════════════════════════════════

@allure.feature("Kimlik Doğrulama")
@allure.story("Güvenlik")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Token olmadan korumalı sayfaya erişim engeli")
def test_protected_page_without_token():
    """Token olmadan /projects erişimi /login'e yönlendirmeli."""


@allure.feature("Kimlik Doğrulama")
@allure.story("Güvenlik")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "SQL injection koruması")
def test_sql_injection_protection():
    """SQL injection denemesi engellenmelidir."""
