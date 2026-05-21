"""
tests/e2e/test_regression.py — Regresyon Test Seti E2E testleri.

regression.feature dosyasını pytest-bdd @scenario dekoratörü ile bağlar.
Sprint sonu ve release öncesi tam regresyon doğrulaması için kullanılır.
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

from steps.bgts_regression_steps import *  # noqa: F401,F403 — step import for discovery

FEATURE = str(ROOT / "features" / "testwright-ai" / "regression.feature")


# ═══ REG-AUTH: Kimlik Doğrulama Regresyonu ═══════════════════════════════════

@allure.feature("Regresyon Test Seti")
@allure.story("Kimlik Doğrulama Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-AUTH-001 Başarılı giriş ve yönlendirme")
def test_reg_auth_001_successful_login_redirect():
    """Regresyon: Başarılı giriş ve /projects yönlendirmesi."""


@allure.feature("Regresyon Test Seti")
@allure.story("Kimlik Doğrulama Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-AUTH-002 Kullanıcı menüsü görünürlüğü")
def test_reg_auth_002_user_menu_visibility():
    """Regresyon: Kullanıcı menüsü görünürlüğü."""


@allure.feature("Regresyon Test Seti")
@allure.story("Kimlik Doğrulama Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-AUTH-003 Oturum kapatma akışı")
def test_reg_auth_003_logout_flow():
    """Regresyon: Oturum kapatma akışı."""


# ═══ REG-PRJ: Proje Yönetimi Regresyonu ═════════════════════════════════════

@allure.feature("Regresyon Test Seti")
@allure.story("Proje Yönetimi Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-PRJ-001 Proje listesi erişimi")
def test_reg_prj_001_project_list_access():
    """Regresyon: Proje listesi erişimi."""


@allure.feature("Regresyon Test Seti")
@allure.story("Proje Yönetimi Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-PRJ-002 Yeni proje oluşturma")
def test_reg_prj_002_create_new_project():
    """Regresyon: Yeni proje oluşturma."""


@allure.feature("Regresyon Test Seti")
@allure.story("Proje Yönetimi Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-PRJ-003 Proje dashboard erişimi")
def test_reg_prj_003_project_dashboard_access():
    """Regresyon: Proje dashboard erişimi."""


# ═══ REG-SCN: Senaryo Yönetimi Regresyonu ═══════════════════════════════════

@allure.feature("Regresyon Test Seti")
@allure.story("Senaryo Yönetimi Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-SCN-001 Senaryo listesi erişimi")
def test_reg_scn_001_scenario_list_access():
    """Regresyon: Senaryo listesi erişimi."""


@allure.feature("Regresyon Test Seti")
@allure.story("Senaryo Yönetimi Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-SCN-002 Yeni senaryo oluşturma")
def test_reg_scn_002_create_new_scenario():
    """Regresyon: Yeni senaryo oluşturma."""


@allure.feature("Regresyon Test Seti")
@allure.story("Senaryo Yönetimi Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P2
@scenario(FEATURE, "REG-SCN-003 Senaryo arama fonksiyonu")
def test_reg_scn_003_scenario_search_function():
    """Regresyon: Senaryo arama fonksiyonu."""


@allure.feature("Regresyon Test Seti")
@allure.story("Senaryo Yönetimi Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P2
@scenario(FEATURE, "REG-SCN-004 Senaryo detay görüntüleme")
def test_reg_scn_004_scenario_detail_view():
    """Regresyon: Senaryo detay görüntüleme."""


@allure.feature("Regresyon Test Seti")
@allure.story("Senaryo Yönetimi Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P2
@scenario(FEATURE, "REG-SCN-005 Senaryo düzenleme")
def test_reg_scn_005_scenario_editing():
    """Regresyon: Senaryo düzenleme."""


@allure.feature("Regresyon Test Seti")
@allure.story("Senaryo Yönetimi Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P2
@scenario(FEATURE, "REG-SCN-006 Versiyon geçmişi")
def test_reg_scn_006_version_history():
    """Regresyon: Versiyon geçmişi."""


@allure.feature("Regresyon Test Seti")
@allure.story("Senaryo Yönetimi Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P2
@scenario(FEATURE, "REG-SCN-007 BDD senaryo üretimi")
def test_reg_scn_007_bdd_scenario_generation():
    """Regresyon: BDD senaryo üretimi."""


@allure.feature("Regresyon Test Seti")
@allure.story("Senaryo Yönetimi Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P2
@scenario(FEATURE, "REG-SCN-008 Toplu seçim fonksiyonu")
def test_reg_scn_008_bulk_selection():
    """Regresyon: Toplu seçim fonksiyonu."""


# ═══ REG-APR: Onay İş Akışı Regresyonu ══════════════════════════════════════

@allure.feature("Regresyon Test Seti")
@allure.story("Onay İş Akışı Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-APR-001 Onay kuyruğu erişimi")
def test_reg_apr_001_approval_queue_access():
    """Regresyon: Onay kuyruğu erişimi."""


@allure.feature("Regresyon Test Seti")
@allure.story("Onay İş Akışı Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-APR-002 Onay detay split view")
def test_reg_apr_002_approval_detail_split_view():
    """Regresyon: Onay detay split view."""


@allure.feature("Regresyon Test Seti")
@allure.story("Onay İş Akışı Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-APR-003 Onaylama akışı")
def test_reg_apr_003_approval_flow():
    """Regresyon: Onaylama akışı."""


@allure.feature("Regresyon Test Seti")
@allure.story("Onay İş Akışı Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-APR-004 Reddetme akışı")
def test_reg_apr_004_rejection_flow():
    """Regresyon: Reddetme akışı."""


# ═══ REG-IMP: İçe Aktarma Regresyonu ════════════════════════════════════════

@allure.feature("Regresyon Test Seti")
@allure.story("İçe Aktarma Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-IMP-001 İçe aktarma sayfası erişimi")
def test_reg_imp_001_import_page_access():
    """Regresyon: İçe aktarma sayfası erişimi."""


@allure.feature("Regresyon Test Seti")
@allure.story("İçe Aktarma Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-IMP-002 Dosya yükleme alanı")
def test_reg_imp_002_file_upload_area():
    """Regresyon: Dosya yükleme alanı."""


# ═══ REG-EXC: Test Koşusu Regresyonu ════════════════════════════════════════

@allure.feature("Regresyon Test Seti")
@allure.story("Test Koşusu Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-EXC-001 Koşu listesi erişimi")
def test_reg_exc_001_execution_list_access():
    """Regresyon: Koşu listesi erişimi."""


@allure.feature("Regresyon Test Seti")
@allure.story("Test Koşusu Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P2
@scenario(FEATURE, "REG-EXC-002 Koşu detayı görüntüleme")
def test_reg_exc_002_execution_detail_view():
    """Regresyon: Koşu detayı görüntüleme."""


# ═══ REG-REG: Regresyon Seti Yönetimi Regresyonu ════════════════════════════

@allure.feature("Regresyon Test Seti")
@allure.story("Regresyon Seti Yönetimi")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P2
@scenario(FEATURE, "REG-REG-001 Regresyon seti listesi")
def test_reg_reg_001_regression_set_list():
    """Regresyon: Regresyon seti listesi."""


# ═══ REG-DATA: Sentetik Veri Regresyonu ══════════════════════════════════════

@allure.feature("Regresyon Test Seti")
@allure.story("Sentetik Veri Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-DATA-001 Veri seti sayfası erişimi")
def test_reg_data_001_dataset_page_access():
    """Regresyon: Veri seti sayfası erişimi."""


# ═══ REG-NAV: Navigasyon Regresyonu ═════════════════════════════════════════

@allure.feature("Regresyon Test Seti")
@allure.story("Navigasyon Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-NAV-001 Ana menü navigasyonu — Projeler")
def test_reg_nav_001_main_menu_projects():
    """Regresyon: Ana menü navigasyonu — Projeler."""


@allure.feature("Regresyon Test Seti")
@allure.story("Navigasyon Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-NAV-002 Proje içi navigasyon — Senaryolar")
def test_reg_nav_002_project_nav_scenarios():
    """Regresyon: Proje içi navigasyon — Senaryolar."""


@allure.feature("Regresyon Test Seti")
@allure.story("Navigasyon Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-NAV-003 Proje içi navigasyon — Onaylar")
def test_reg_nav_003_project_nav_approvals():
    """Regresyon: Proje içi navigasyon — Onaylar."""


@allure.feature("Regresyon Test Seti")
@allure.story("Navigasyon Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-NAV-004 Proje içi navigasyon — İçe Aktarma")
def test_reg_nav_004_project_nav_import():
    """Regresyon: Proje içi navigasyon — İçe Aktarma."""


# ═══ REG-API: API Endpoint Regresyonu ════════════════════════════════════════

@allure.feature("Regresyon Test Seti")
@allure.story("API Endpoint Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-API-001 Backend sağlık kontrolü")
def test_reg_api_001_backend_health_check():
    """Regresyon: Backend sağlık kontrolü."""


@allure.feature("Regresyon Test Seti")
@allure.story("API Endpoint Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-API-002 Auth API erişimi")
def test_reg_api_002_auth_api_access():
    """Regresyon: Auth API erişimi."""


@allure.feature("Regresyon Test Seti")
@allure.story("API Endpoint Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-API-003 TSPM proje API erişimi")
def test_reg_api_003_tspm_project_api_access():
    """Regresyon: TSPM proje API erişimi."""


@allure.feature("Regresyon Test Seti")
@allure.story("API Endpoint Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-API-004 TSPM senaryo API erişimi")
def test_reg_api_004_tspm_scenario_api_access():
    """Regresyon: TSPM senaryo API erişimi."""


@allure.feature("Regresyon Test Seti")
@allure.story("API Endpoint Regresyonu")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "REG-API-005 Engine feature API erişimi")
def test_reg_api_005_engine_feature_api_access():
    """Regresyon: Engine feature API erişimi."""
