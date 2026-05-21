"""
tests/e2e/test_smoke.py — Smoke Test Seti.

smoke.feature içindeki tüm senaryoları pytest-bdd `scenarios()` toplu
yükleyicisi ile otomatik keşfeder. Feature ⇄ test isim senkronizasyon
hatalarını önler.

Bağımsız olarak çalıştırılabilir: pytest -m smoke
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pytest_bdd import scenarios

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from steps.bgts_smoke_steps import *  # noqa: F401,F403

FEATURE = str(ROOT / "features" / "testwright-ai" / "smoke.feature")

scenarios(FEATURE)

pytestmark = [pytest.mark.smoke, pytest.mark.e2e]
