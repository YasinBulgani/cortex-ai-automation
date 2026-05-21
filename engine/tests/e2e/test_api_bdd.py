"""
tests/e2e/test_api_bdd.py — API Endpoint BDD testleri.

api_tests.feature dosyasındaki tüm senaryoları pytest-bdd `scenarios()` toplu
yükleyicisi ile otomatik keşfeder. Bu, her senaryo için elle `@scenario()`
dekoratörü yazmayı ortadan kaldırır ve feature ⇄ test senkronizasyon
hatalarını (senaryo adı değişince test collection kırılmasını) önler.

Allure raporlaması pytest-bdd otomatik olarak yapar.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pytest_bdd import scenarios

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from steps.bgts_api_steps import *  # noqa: F401,F403 — step import for discovery

FEATURE = str(ROOT / "features" / "testwright-ai" / "api_tests.feature")

# Feature içindeki tüm Scenario + Scenario Outline'ları yakala.
scenarios(FEATURE)

# Bu modüldeki senaryolar API katmanını doğrular.
pytestmark = [pytest.mark.api, pytest.mark.e2e]
