"""ROI pure compute + formatting testleri."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domains.ai.roi_service import (
    ROISummary,
    RoiInputs,
    RoiOutputs,
    compute_roi,
    format_weekly_report,
)


class TestCompute:
    def test_basic_calc(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ROI_HOURLY_RATE_USD", "50")
        monkeypatch.setenv("ROI_AVG_MANUAL_HOURS_PER_TEST", "0.5")
        # 100 test × 0.5h × $50 = $2500 manual savings
        # AI cost $100 → net $2400, ROI %2400
        out = compute_roi(RoiInputs(tests_generated=100, ai_cost_usd=100.0, days=7))
        assert out.manual_hours_saved == 50.0
        assert out.manual_cost_saved_usd == 2500.0
        assert out.net_savings_usd == 2400.0
        assert out.roi_pct == 2400.0

    def test_zero_ai_cost_with_positive_savings_returns_sentinel(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ROI_HOURLY_RATE_USD", "40")
        monkeypatch.setenv("ROI_AVG_MANUAL_HOURS_PER_TEST", "0.5")
        out = compute_roi(RoiInputs(tests_generated=10, ai_cost_usd=0.0, days=1))
        # 10 * 0.5 * 40 = 200 manual, net 200, ROI "infinity" sentinel 99999
        assert out.net_savings_usd == 200.0
        assert out.roi_pct == 99999.0

    def test_zero_everything(self) -> None:
        out = compute_roi(RoiInputs(tests_generated=0, ai_cost_usd=0.0, days=1))
        assert out.net_savings_usd == 0.0
        assert out.roi_pct == 0.0

    def test_negative_roi_when_cost_exceeds_savings(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ROI_HOURLY_RATE_USD", "40")
        monkeypatch.setenv("ROI_AVG_MANUAL_HOURS_PER_TEST", "0.5")
        # 1 test × 0.5h × $40 = $20; AI cost $100 → net -$80, ROI -80
        out = compute_roi(RoiInputs(tests_generated=1, ai_cost_usd=100.0, days=1))
        assert out.net_savings_usd == -80.0
        assert out.roi_pct == -80.0

    def test_env_overrides_picked_up(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ROI_HOURLY_RATE_USD", "200")
        monkeypatch.setenv("ROI_AVG_MANUAL_HOURS_PER_TEST", "1.0")
        out = compute_roi(RoiInputs(tests_generated=5, ai_cost_usd=50.0, days=7))
        # 5 * 1.0 * 200 = 1000; net 950; ROI 1900
        assert out.manual_cost_saved_usd == 1000.0
        assert out.net_savings_usd == 950.0
        assert out.roi_pct == 1900.0


class TestFormat:
    def test_report_includes_key_fields(self) -> None:
        summary = ROISummary(
            tenant_id="tenant-x",
            days=7,
            range_start=datetime(2026, 4, 13, tzinfo=timezone.utc),
            range_end=datetime(2026, 4, 20, tzinfo=timezone.utc),
            tests_generated=50,
            ai_cost_usd=25.0,
            manual_hours_saved=25.0,
            manual_cost_saved_usd=1000.0,
            net_savings_usd=975.0,
            roi_pct=3900.0,
            hourly_rate_usd=40.0,
            avg_manual_hours=0.5,
            task_types_counted=["test_generation"],
        )
        text = format_weekly_report(summary)
        assert "tenant-x" in text
        assert "7 gün" in text
        assert "50" in text
        assert "975" in text
        assert "3,900" in text or "3900" in text

    def test_report_handles_missing_tenant(self) -> None:
        summary = ROISummary(
            tenant_id=None,
            days=1,
            range_start=datetime(2026, 4, 19, tzinfo=timezone.utc),
            range_end=datetime(2026, 4, 20, tzinfo=timezone.utc),
            tests_generated=0,
            ai_cost_usd=0.0,
            manual_hours_saved=0.0,
            manual_cost_saved_usd=0.0,
            net_savings_usd=0.0,
            roi_pct=0.0,
            hourly_rate_usd=40.0,
            avg_manual_hours=0.5,
        )
        text = format_weekly_report(summary)
        assert "tüm tenant" in text.lower()
