"""
tests/e2e/test_scenarios.py — Senaryo Yönetimi E2E testleri.

scenarios.feature dosyasını pytest-bdd @scenario dekoratörü ile bağlar.
"""
from __future__ import annotations

import sys
from pathlib import Path

import allure
import pytest
from pytest_bdd import scenario

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from steps.bgts_scenario_steps import *  # noqa: F401,F403

FEATURE = str(ROOT / "features" / "testwright-ai" / "scenarios.feature")


# ═══ SENARYO LİSTELEME ══════════════════════════════════════════════════════

@allure.feature("Senaryo Yönetimi")
@allure.story("Listeleme")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Senaryo listesi sayfasını görüntüleme")
def test_view_scenario_list():
    """Senaryo listesi sayfası başarıyla yüklenmeli."""


@allure.feature("Senaryo Yönetimi")
@allure.story("Arama")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Senaryo listesinde arama yapma")
def test_search_scenarios():
    """Senaryo listesinde arama yapılabilmeli."""


@allure.feature("Senaryo Yönetimi")
@allure.story("Arama")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Boş arama sonucu gösterimi")
def test_empty_search_result():
    """Sonuçsuz arama uygun durum mesajı göstermeli."""


# ═══ SENARYO OLUŞTURMA ══════════════════════════════════════════════════════

@allure.feature("Senaryo Yönetimi")
@allure.story("Oluşturma")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Yeni test senaryosu oluşturma")
def test_create_new_scenario():
    """Yeni test senaryosu oluşturulabilmeli."""


@allure.feature("Senaryo Yönetimi")
@allure.story("Oluşturma")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Senaryo başlığı olmadan kaydetme denemesi")
def test_create_scenario_without_title():
    """Başlıksız senaryo kaydı doğrulama hatası vermeli."""


@allure.feature("Senaryo Yönetimi")
@allure.story("Oluşturma")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Senaryo oluşturma formunda adım ekleme")
def test_add_steps_to_scenario():
    """Senaryoya adım eklenebilmeli."""


# ═══ SENARYO DÜZENLEME ══════════════════════════════════════════════════════

@allure.feature("Senaryo Yönetimi")
@allure.story("Düzenleme")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Mevcut senaryoyu düzenleme")
def test_edit_existing_scenario():
    """Mevcut senaryo düzenlenebilmeli."""


# ═══ SENARYO DETAY ══════════════════════════════════════════════════════════

@allure.feature("Senaryo Yönetimi")
@allure.story("Detay")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Senaryo detay sayfasını görüntüleme")
def test_view_scenario_detail():
    """Senaryo detay bilgileri görüntülenebilmeli."""


@allure.feature("Senaryo Yönetimi")
@allure.story("Versiyon Geçmişi")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Senaryo versiyon geçmişi görüntüleme")
def test_view_scenario_version_history():
    """Senaryo versiyon geçmişi görüntülenebilmeli."""


# ═══ TOPLU İŞLEMLER ═════════════════════════════════════════════════════════

@allure.feature("Senaryo Yönetimi")
@allure.story("Toplu İşlemler")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Birden fazla senaryo seçme")
def test_multi_select_scenarios():
    """Birden fazla senaryo seçilebilmeli."""


@allure.feature("Senaryo Yönetimi")
@allure.story("Toplu İşlemler")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Seçili senaryoları toplu silme")
def test_bulk_delete_scenarios():
    """Seçili senaryolar toplu silinebilmeli."""


# ═══ BDD SENARYO ÜRETİMİ ════════════════════════════════════════════════════

@allure.feature("Senaryo Yönetimi")
@allure.story("BDD Üretimi")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "AI ile BDD senaryo üretimi")
def test_ai_bdd_generation():
    """AI ile BDD senaryosu üretilebilmeli."""


@allure.feature("Senaryo Yönetimi")
@allure.story("BDD Üretimi")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Üretilen BDD senaryolarını kaydetme")
def test_save_generated_bdd_scenarios():
    """Üretilen BDD senaryoları kaydedilebilmeli."""


# ═══ GEREKSİNİM BAĞLAMA ════════════════════════════════════════════════════

@allure.feature("Senaryo Yönetimi")
@allure.story("Gereksinim Bağlama")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Senaryoya gereksinim bağlama")
def test_link_requirement_to_scenario():
    """Senaryoya gereksinim bağlanabilmeli."""
