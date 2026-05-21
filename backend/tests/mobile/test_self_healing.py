"""Self-Healing karar motoru testleri."""
from __future__ import annotations

import pytest

from app.domains.mobile.self_healing import HealRequest, suggest


pytestmark = pytest.mark.P1


class TestHealDecisions:
    def test_retry_on_first_failure_doubles_timeout(self):
        req = HealRequest(
            failed_action={"action": "find", "by": "accessibilityId", "value": "login", "timeout": 5000},
            retry_count=0,
        )
        result = suggest(req)
        assert result.decision == "RETRY"
        assert result.new_action is not None
        assert result.new_action["timeout"] == 10000
        assert result.confidence >= 0.8

    def test_retry_uses_5000_default_when_no_timeout(self):
        req = HealRequest(
            failed_action={"action": "find", "by": "accessibilityId", "value": "login"},
            retry_count=0,
        )
        result = suggest(req)
        assert result.new_action is not None
        assert result.new_action["timeout"] == 10000  # 2x 5000 default

    def test_rewrite_on_second_failure_with_accessibility_id(self):
        req = HealRequest(
            failed_action={"action": "find", "by": "accessibilityId", "value": "submit_btn"},
            retry_count=1,
        )
        result = suggest(req)
        assert result.decision == "REWRITE"
        assert result.new_action is not None
        assert result.new_action["by"] == "xpath"
        assert "submit_btn" in result.new_action["value"]
        assert "content-desc" in result.new_action["value"]

    def test_rewrite_preserves_action_type(self):
        req = HealRequest(
            failed_action={"action": "find", "by": "accessibilityId", "value": "btn", "timeout": 3000},
            retry_count=1,
        )
        result = suggest(req)
        assert result.new_action is not None
        assert result.new_action["action"] == "find"
        assert result.new_action["timeout"] == 3000  # timeout preserved

    def test_ui_changed_after_two_failures(self):
        req = HealRequest(
            failed_action={"action": "find", "by": "accessibilityId", "value": "btn"},
            retry_count=2,
        )
        result = suggest(req)
        assert result.decision == "UI_CHANGED"
        assert result.new_action is None
        assert "quarantine" in result.reason.lower()

    def test_rewrite_skipped_when_not_accessibility_id(self):
        """xpath locator zaten düşük öncelikte, tekrar xpath önermeyiz."""
        req = HealRequest(
            failed_action={"action": "find", "by": "xpath", "value": "//*[@id='x']"},
            retry_count=1,
        )
        result = suggest(req)
        # rewrite yerine ui_changed'e düşmeli (accessibility id değil)
        assert result.decision == "UI_CHANGED"

    def test_all_decisions_have_reason(self):
        for retry in (0, 1, 2, 5):
            req = HealRequest(
                failed_action={"action": "find", "by": "accessibilityId", "value": "x"},
                retry_count=retry,
            )
            result = suggest(req)
            assert result.reason
            assert 0.0 <= result.confidence <= 1.0
