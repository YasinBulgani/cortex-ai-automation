"""
tests/e2e/test_synthetic_data.py — Sentetik Veri Üretimi E2E testleri.

synthetic_data.feature dosyasını pytest-bdd @scenario dekoratörü ile bağlar.
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

# common_steps'i plugin olarak yükle — pytest_plugins in tests/conftest.py
# non-root conftest'te tam yüklenmiyor; burada açıkça belirtiyoruz.
pytest_plugins = ["steps.common_steps"]

from steps.bgts_synthetic_steps import *  # noqa: F401,F403 — step import for discovery

FEATURE = str(ROOT / "features" / "testwright-ai" / "synthetic_data.feature")


# ═══ VERİ SETİ YÜKLEME ══════════════════════════════════════════════════════

@allure.feature("Sentetik Veri Üretimi")
@allure.story("Veri Seti Yükleme")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "CSV dosyası yükleme")
def test_csv_file_upload():
    """CSV dosyası başarıyla yüklenmeli."""


@allure.feature("Sentetik Veri Üretimi")
@allure.story("Veri Seti Yükleme")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "JSON dosyası yükleme")
def test_json_file_upload():
    """JSON dosyası başarıyla yüklenmeli."""


# ═══ VERİ ANALİZİ ═══════════════════════════════════════════════════════════

@allure.feature("Sentetik Veri Üretimi")
@allure.story("Veri Analizi")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Yüklenen verinin yapı analizini görüntüleme")
def test_view_data_structure_analysis():
    """Yüklenen verinin yapı analizi görüntülenmeli."""


@allure.feature("Sentetik Veri Üretimi")
@allure.story("Veri Analizi")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Sütun tip tespiti sonuçlarını inceleme")
def test_column_type_detection_results():
    """Sütun tip tespiti sonuçları incelenmeli."""


# ═══ PII TESPİTİ ════════════════════════════════════════════════════════════

@allure.feature("Sentetik Veri Üretimi")
@allure.story("PII Tespiti")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Kişisel veri (PII) tespiti")
def test_pii_detection():
    """Kişisel veri (PII) tespiti yapılmalı."""


@allure.feature("Sentetik Veri Üretimi")
@allure.story("PII Tespiti")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "TCKN ve telefon alanlarının PII olarak işaretlenmesi")
def test_tckn_phone_pii_marking():
    """TCKN ve telefon alanları PII olarak işaretlenmeli."""


# ═══ SENTETİK VERİ ÜRETİMİ ══════════════════════════════════════════════════

@allure.feature("Sentetik Veri Üretimi")
@allure.story("Sentetik Veri Üretimi")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Sentetik veri üretimini başlatma")
def test_start_synthetic_data_generation():
    """Sentetik veri üretimi başlatılmalı."""


@allure.feature("Sentetik Veri Üretimi")
@allure.story("Sentetik Veri Üretimi")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Üretim iş durumunu takip etme")
def test_track_generation_job_status():
    """Üretim iş durumu takip edilmeli."""


# ═══ DIŞA AKTARMA ═══════════════════════════════════════════════════════════

@allure.feature("Sentetik Veri Üretimi")
@allure.story("Dışa Aktarma")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Üretilen veri setini CSV olarak dışa aktarma")
def test_export_dataset_as_csv():
    """Üretilen veri seti CSV olarak dışa aktarılmalı."""


@allure.feature("Sentetik Veri Üretimi")
@allure.story("Dışa Aktarma")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Üretilen veri setini JSON olarak dışa aktarma")
def test_export_dataset_as_json():
    """Üretilen veri seti JSON olarak dışa aktarılmalı."""


# ═══ PROJE TEST VERİSİ ══════════════════════════════════════════════════════

@allure.feature("Sentetik Veri Üretimi")
@allure.story("Proje Test Verisi")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@pytest.mark.xfail(
    strict=False,
    reason="Senaryo sayfasında 'Test Verisi' butonu henüz mevcut değil — UI feature bekliyor",
)
@scenario(FEATURE, "Proje bazlı test veri seti oluşturma")
def test_create_project_test_dataset():
    """Proje bazlı test veri seti oluşturulmalı."""


@allure.feature("Sentetik Veri Üretimi")
@allure.story("Proje Test Verisi")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@pytest.mark.xfail(
    strict=False,
    reason="'Veri Bağla' UI elementi henüz mevcut değil — UI feature bekliyor",
)
@scenario(FEATURE, "Senaryoya test verisi bağlama")
def test_bind_test_data_to_scenario():
    """Senaryoya test verisi bağlanmalı."""


# ═══ VERİ SINIFLANDIRMA ═════════════════════════════════════════════════════

@allure.feature("Sentetik Veri Üretimi")
@allure.story("Veri Sınıflandırma")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@pytest.mark.xfail(
    strict=False,
    reason="/datasets sayfası veya 'Sınıflandır' butonu henüz mevcut değil",
)
@scenario(FEATURE, "Veri seti sınıflandırma")
def test_dataset_classification():
    """Veri seti sınıflandırılmalı."""


# ═══ KURAL ÇIKARIMI ═════════════════════════════════════════════════════════

@allure.feature("Sentetik Veri Üretimi")
@allure.story("Kural Çıkarımı")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@pytest.mark.xfail(
    strict=False,
    reason="/datasets sayfasında 'Kural Çıkar' butonu henüz mevcut değil",
)
@scenario(FEATURE, "Veri kuralları çıkarımı")
def test_data_rules_inference():
    """Veri kuralları çıkarımı yapılmalı."""
