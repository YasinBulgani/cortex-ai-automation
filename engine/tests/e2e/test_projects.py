"""
tests/e2e/test_projects.py — Proje Yönetimi E2E testleri.

projects.feature dosyasını pytest-bdd @scenario dekoratörü ile bağlar.
"""
from __future__ import annotations

import sys
from pathlib import Path

import allure
import pytest
from pytest_bdd import scenario

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from steps.bgts_project_steps import *  # noqa: F401,F403

FEATURE = str(ROOT / "features" / "testwright-ai" / "projects.feature")


# ═══ PROJE LİSTELEME ════════════════════════════════════════════════════════

@allure.feature("Proje Yönetimi")
@allure.story("Listeleme")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Proje listesi görüntüleme")
def test_view_project_list():
    """Proje listesi sayfası başarıyla yüklenmeli."""


@allure.feature("Proje Yönetimi")
@allure.story("Listeleme")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Proje listesi boş durum gösterimi")
def test_empty_project_list():
    """Boş proje listesi uygun durum mesajı göstermeli."""


# ═══ PROJE OLUŞTURMA ════════════════════════════════════════════════════════

@allure.feature("Proje Yönetimi")
@allure.story("Oluşturma")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Yeni proje oluşturma")
def test_create_new_project():
    """Yeni proje başarıyla oluşturulabilmeli."""


@allure.feature("Proje Yönetimi")
@allure.story("Oluşturma")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Proje adı olmadan oluşturma denemesi")
def test_create_project_without_name():
    """İsim olmadan proje oluşturma doğrulama hatası vermeli."""


# ═══ PROJE DASHBOARD ════════════════════════════════════════════════════════

@allure.feature("Proje Yönetimi")
@allure.story("Dashboard")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Proje dashboard istatistikleri")
def test_view_project_dashboard():
    """Proje dashboard istatistikleri doğru görüntülenmeli."""


@allure.feature("Proje Yönetimi")
@allure.story("Dashboard")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Dashboard hızlı aksiyonlar")
def test_dashboard_quick_actions():
    """Dashboard hızlı aksiyon butonları erişilebilir olmalı."""


# ═══ PROJE NAVİGASYON ═══════════════════════════════════════════════════════

@allure.feature("Proje Yönetimi")
@allure.story("Navigasyon")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Dashboard'dan senaryo listesine navigasyon")
def test_navigate_to_scenarios():
    """Proje detayından senaryolar sayfasına geçiş mümkün olmalı."""


@allure.feature("Proje Yönetimi")
@allure.story("Navigasyon")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Dashboard'dan onay kuyruğuna navigasyon")
def test_navigate_to_approvals():
    """Proje detayından onaylar sayfasına geçiş mümkün olmalı."""


@allure.feature("Proje Yönetimi")
@allure.story("Navigasyon")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Dashboard'dan içe aktarmaya navigasyon")
def test_navigate_to_import():
    """Proje detayından içe aktarma sayfasına geçiş mümkün olmalı."""


# ═══ ÜYE YÖNETİMİ ══════════════════════════════════════════════════════════

@allure.feature("Proje Yönetimi")
@allure.story("Üye Yönetimi")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Proje üye listesi")
def test_view_project_members():
    """Proje üye listesi görüntülenebilmeli."""
