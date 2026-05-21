"""
tests/e2e/test_import.py — Dosya İçe Aktarma E2E testleri.

import.feature dosyasını pytest-bdd @scenario dekoratörü ile bağlar.
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

from steps.bgts_import_steps import *  # noqa: F401,F403 — step import for discovery

FEATURE = str(ROOT / "features" / "testwright-ai" / "import.feature")


# ═══ İÇE AKTARMA SAYFASI ════════════════════════════════════════════════════

@allure.feature("Dosya İçe Aktarma")
@allure.story("Sayfa Görüntüleme")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "İçe aktarma sayfasını görüntüleme")
def test_view_import_page():
    """İçe aktarma sayfası başarıyla yüklenmeli."""


@allure.feature("Dosya İçe Aktarma")
@allure.story("Sayfa Görüntüleme")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Kaynak seçim alanını görüntüleme")
def test_view_source_selector():
    """Kaynak seçim alanı görünür olmalı."""


# ═══ DOSYA YÜKLEME ══════════════════════════════════════════════════════════

@allure.feature("Dosya İçe Aktarma")
@allure.story("Dosya Yükleme")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Dosya seçimi ve yükleme başlatma")
def test_file_selection_and_upload():
    """Dosya seçilip yükleme başlatılmalı."""


@allure.feature("Dosya İçe Aktarma")
@allure.story("Dosya Yükleme")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Yükleme ilerleme durumunu izleme")
def test_upload_progress_tracking():
    """Yükleme ilerleme durumu görüntülenmeli."""


# ═══ AI İŞLEME ══════════════════════════════════════════════════════════════

@allure.feature("Dosya İçe Aktarma")
@allure.story("AI İşleme")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Yüklenen dosyanın AI tarafından analiz edilmesi")
def test_ai_analysis_of_uploaded_file():
    """Yüklenen dosya AI tarafından analiz edilmeli."""


@allure.feature("Dosya İçe Aktarma")
@allure.story("AI İşleme")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "AI işleme sonuçlarını görüntüleme")
def test_view_ai_processing_results():
    """AI işleme sonuçları görüntülenmeli."""


# ═══ DURUM TAKİBİ ═══════════════════════════════════════════════════════════

@allure.feature("Dosya İçe Aktarma")
@allure.story("Durum Takibi")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "İçe aktarma geçmişini görüntüleme")
def test_view_import_history():
    """İçe aktarma geçmişi görüntülenmeli."""


@allure.feature("Dosya İçe Aktarma")
@allure.story("Durum Takibi")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Tamamlanan import kaydının detayı")
def test_view_completed_import_detail():
    """Tamamlanan import kaydının detayı görüntülenmeli."""


# ═══ HATA DURUMLARI ═════════════════════════════════════════════════════════

@allure.feature("Dosya İçe Aktarma")
@allure.story("Hata Durumları")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Desteklenmeyen dosya formatı hatası")
def test_unsupported_file_format_error():
    """Desteklenmeyen dosya formatı hata mesajı göstermeli."""


@allure.feature("Dosya İçe Aktarma")
@allure.story("Hata Durumları")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Boş dosya yükleme hatası")
def test_empty_file_upload_error():
    """Boş dosya yükleme hata mesajı göstermeli."""
