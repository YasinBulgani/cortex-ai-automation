"""self_healer — feedback loop + confidence recalibration (Dalga 2)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from services import self_healer as sh_mod
from services.self_healer import SelfHealer


@pytest.fixture
def isolated_fingerprints(tmp_path, monkeypatch):
    """Her test için ayrı fingerprints dosyası."""
    fp_path = tmp_path / "fingerprints.json"
    monkeypatch.setattr(sh_mod, "_LOCATOR_FINGERPRINTS", fp_path)
    return fp_path


def _make_gateway(responses):
    mock = MagicMock()
    idx = {"n": 0}

    def _complete(*args, **kwargs):
        r = responses[min(idx["n"], len(responses) - 1)]
        idx["n"] += 1
        resp = MagicMock()
        resp.content = r
        return resp

    mock.complete.side_effect = _complete
    return mock


class TestHealFresh:
    def test_llm_heal_initial(self, isolated_fingerprints):
        gateway = _make_gateway(["[data-testid='login-btn-submit']"])
        healer = SelfHealer(gateway, model="claude-3-5-sonnet-latest")

        result = healer.heal(
            failed_locator="[data-testid='old-btn']",
            accessibility_tree="role=button name=Giriş testid=login-btn-submit",
        )
        assert result.healed is True
        assert result.strategy == "llm_assisted"
        assert result.confidence == healer.INITIAL_CONFIDENCE
        assert result.new_locator == "[data-testid='login-btn-submit']"

    def test_cache_hit_on_second_call(self, isolated_fingerprints):
        gateway = _make_gateway(["[data-testid='btn1']"])
        healer = SelfHealer(gateway, model="m")
        healer.heal(failed_locator=".old1", accessibility_tree="tree")
        # ikinci çağrıda aynı locator → cache'ten dönmeli, LLM çağırılmamalı
        result2 = healer.heal(failed_locator=".old1", accessibility_tree="tree")
        assert result2.strategy == "fingerprint_cache"
        assert gateway.complete.call_count == 1


class TestFeedbackLoop:
    def test_success_increments_confidence(self, isolated_fingerprints):
        gateway = _make_gateway(["[data-testid='new']"])
        healer = SelfHealer(gateway, model="m")
        healer.heal(failed_locator=".old", accessibility_tree="t")

        for i in range(3):
            outcome = healer.report_outcome(
                old_locator=".old", new_locator="[data-testid='new']", success=True,
            )

        assert outcome["status"] == "updated"
        assert outcome["success_count"] == 3
        # 0.7 + 3*0.05 = 0.85
        assert outcome["confidence"] == pytest.approx(0.85, abs=0.001)

    def test_confidence_caps_at_max(self, isolated_fingerprints):
        gateway = _make_gateway(["[data-testid='new']"])
        healer = SelfHealer(gateway, model="m")
        healer.heal(failed_locator=".old", accessibility_tree="t")
        for _ in range(100):
            outcome = healer.report_outcome(
                old_locator=".old", new_locator="[data-testid='new']", success=True,
            )
        assert outcome["confidence"] <= healer.CONF_MAX

    def test_failure_decrements_confidence(self, isolated_fingerprints):
        gateway = _make_gateway(["[data-testid='new']"])
        healer = SelfHealer(gateway, model="m")
        healer.heal(failed_locator=".old", accessibility_tree="t")

        # 2 failure: 0.7 - 2*0.1 = 0.5 — hâlâ eviction üstünde
        for _ in range(2):
            outcome = healer.report_outcome(
                old_locator=".old", new_locator="[data-testid='new']", success=False,
            )
        assert outcome["status"] == "updated"
        assert outcome["confidence"] == pytest.approx(0.5, abs=0.001)
        assert outcome["failure_count"] == 2

    def test_eviction_below_threshold(self, isolated_fingerprints):
        gateway = _make_gateway(["[data-testid='new']"])
        healer = SelfHealer(gateway, model="m")
        healer.heal(failed_locator=".old", accessibility_tree="t")

        # 5 failure: 0.7 - 5*0.1 = 0.2 < 0.3 → evict
        last = None
        for _ in range(5):
            last = healer.report_outcome(
                old_locator=".old", new_locator="[data-testid='new']", success=False,
            )
        assert last["status"] == "evicted"
        assert ".old" not in healer._fingerprints

    def test_reported_locator_must_match_cached(self, isolated_fingerprints):
        gateway = _make_gateway(["[data-testid='x']"])
        healer = SelfHealer(gateway, model="m")
        healer.heal(failed_locator=".old", accessibility_tree="t")
        out = healer.report_outcome(
            old_locator=".old", new_locator="wrong-locator", success=True,
        )
        assert out == {"status": "no_entry"}


class TestEvictedCacheBypassed:
    def test_low_confidence_entry_not_returned(self, isolated_fingerprints):
        # Direkt düşük confidence yaz
        data = {
            ".old": {
                "new_locator": "[data-testid='unreliable']",
                "success_count": 0, "failure_count": 10,
                "confidence": 0.1,   # < 0.3
                "updated_at": "2026-04-19",
            }
        }
        isolated_fingerprints.write_text(json.dumps(data))
        gateway = _make_gateway(["[data-testid='fresh']"])
        healer = SelfHealer(gateway, model="m")
        result = healer.heal(failed_locator=".old", accessibility_tree="t")
        # Cache atlanmalı, LLM çağırılmış olmalı
        assert result.strategy == "llm_assisted"
        assert gateway.complete.call_count == 1
        assert result.new_locator == "[data-testid='fresh']"


class TestMigrationV1ToV2:
    def test_v1_legacy_entry_migrated(self, isolated_fingerprints):
        """Eski şema: {new_locator, timestamp} — yeni alanlar otomatik eklenir."""
        v1 = {".old": {"new_locator": "[data-testid='legacy']", "timestamp": "2026-04-01"}}
        isolated_fingerprints.write_text(json.dumps(v1))
        gateway = _make_gateway([])
        healer = SelfHealer(gateway, model="m")
        entry = healer._fingerprints[".old"]
        assert entry["success_count"] == 0
        assert entry["failure_count"] == 0
        assert entry["confidence"] == healer.INITIAL_CONFIDENCE
        # v2 entry sağlıklı → cache hit döner
        result = healer.heal(failed_locator=".old", accessibility_tree="t")
        assert result.strategy == "fingerprint_cache"
        assert gateway.complete.call_count == 0
