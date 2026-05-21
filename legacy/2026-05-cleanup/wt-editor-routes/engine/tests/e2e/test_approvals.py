"""
tests/e2e/test_approvals.py — Onay İş Akışı E2E testleri.

approvals.feature dosyasını pytest-bdd @scenario dekoratörü ile bağlar.
"""
from __future__ import annotations

import sys
from pathlib import Path

import allure
import pytest
from pytest_bdd import scenario

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from steps.bgts_approval_steps import *  # noqa: F401,F403

FEATURE = str(ROOT / "features" / "testwright-ai" / "approvals.feature")


# ═══ ONAY KUYRUĞU ═══════════════════════════════════════════════════════════

@allure.feature("Onay İş Akışı")
@allure.story("Onay Kuyruğu")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Onay kuyruğunu görüntüleme")
def test_view_approval_queue():
    """Onay kuyruğu sayfası başarıyla yüklenmeli."""


@allure.feature("Onay İş Akışı")
@allure.story("Onay Kuyruğu")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Bekleyen onay sayısını kontrol etme")
def test_pending_approval_count():
    """Bekleyen onay sayısı gösterilmeli."""


@allure.feature("Onay İş Akışı")
@allure.story("Onay Kuyruğu")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Boş onay kuyruğu durumu")
def test_empty_approval_queue():
    """Boş onay kuyruğu uygun durum mesajı göstermeli."""


# ═══ SPLIT VIEW ═════════════════════════════════════════════════════════════

@allure.feature("Onay İş Akışı")
@allure.story("Split View")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Onay detayında split view görüntüleme")
def test_approval_split_view():
    """Onay detayında kaynak ve taslak paneli yan yana görüntülenmeli."""


@allure.feature("Onay İş Akışı")
@allure.story("Split View")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Kaynak doküman içeriğini inceleme")
def test_view_source_document():
    """Kaynak doküman paneli görüntülenebilmeli."""


@allure.feature("Onay İş Akışı")
@allure.story("Split View")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "AI taslak içeriğini inceleme")
def test_view_ai_draft():
    """AI taslak paneli görüntülenebilmeli."""


# ═══ ONAY KARARLARI ═════════════════════════════════════════════════════════

@allure.feature("Onay İş Akışı")
@allure.story("Karar")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Onay taslağını onaylama")
def test_approve_draft():
    """Onay taslağı onaylanabilmeli."""


@allure.feature("Onay İş Akışı")
@allure.story("Karar")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Onay taslağını reddetme")
def test_reject_draft():
    """Onay taslağı reddedilebilmeli."""


@allure.feature("Onay İş Akışı")
@allure.story("Karar")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P2
@scenario(FEATURE, "Onay taslağını düzenleyerek onaylama")
def test_edit_and_approve_draft():
    """Onay taslağı düzenlenerek onaylanabilmeli."""


# ═══ ONAY SONRASI DURUM ═════════════════════════════════════════════════════

@allure.feature("Onay İş Akışı")
@allure.story("Sonuç")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "Onaylanan taslağın senaryo havuzuna eklenmesi")
def test_approved_draft_added_to_pool():
    """Onaylanan taslak senaryo havuzuna eklenmeli."""


@allure.feature("Onay İş Akışı")
@allure.story("Sonuç")
@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.P1
@scenario(FEATURE, "Reddedilen taslağın senaryo havuzuna eklenmemesi")
def test_rejected_draft_not_in_pool():
    """Reddedilen taslak senaryo havuzuna eklenmemeli."""
