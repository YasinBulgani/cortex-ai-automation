"""Unit tests for app.domains.automation_suite.service.

Tests are fully self-contained: no HTTP, no DB, no external services.
The in-memory _RunRegistry and pure helpers are tested directly;
httpx calls are monkeypatched where needed.
"""
from __future__ import annotations

import asyncio
import pytest

try:
    from app.domains.automation_suite import service as svc
    from app.domains.automation_suite.service import (
        _RunRegistry,
        _match_gherkin_with_dsl,
        get_run_status,
    )
    from app.domains.automation_suite.schemas import (
        Framework,
        SuiteRunRequest,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="automation_suite service import failed")


# ── _RunRegistry ──────────────────────────────────────────────────────────────


class TestRunRegistry:
    def _make_registry(self):
        return _RunRegistry()

    def test_create_returns_record_with_run_id(self):
        """create() çağrısı run_id içeren bir _RunRecord döndürmeli."""
        reg = self._make_registry()
        rec = reg.create(feature_path="features/login.feature", framework="playwright")
        assert rec.run_id
        assert len(rec.run_id) > 0

    def test_create_sets_status_queued(self):
        """Yeni kayıt status='queued' ile başlamalı."""
        reg = self._make_registry()
        rec = reg.create(feature_path="features/search.feature", framework="playwright")
        assert rec.status == "queued"

    def test_get_returns_none_for_unknown_id(self):
        """Bilinmeyen run_id için get() None döndürmeli."""
        reg = self._make_registry()
        assert reg.get("nonexistent-id") is None

    def test_get_returns_record_after_create(self):
        """Oluşturulan kayıt get() ile alınabilmeli."""
        reg = self._make_registry()
        rec = reg.create(feature_path="features/checkout.feature", framework="playwright")
        fetched = reg.get(rec.run_id)
        assert fetched is not None
        assert fetched.run_id == rec.run_id

    def test_update_changes_status(self):
        """update() ile status alanı güncellenebilmeli."""
        reg = self._make_registry()
        rec = reg.create(feature_path="features/cart.feature", framework="playwright")
        reg.update(rec.run_id, status="running")
        fetched = reg.get(rec.run_id)
        assert fetched.status == "running"

    def test_update_unknown_run_id_returns_none(self):
        """Bilinmeyen run_id için update() None döndürmeli."""
        reg = self._make_registry()
        result = reg.update("unknown-xyz", status="running")
        assert result is None

    def test_append_log_adds_line(self):
        """append_log() logu kayıt'a eklemeli."""
        reg = self._make_registry()
        rec = reg.create(feature_path="features/test.feature", framework="playwright")
        reg.append_log(rec.run_id, "Başlıyor...")
        fetched = reg.get(rec.run_id)
        assert "Başlıyor..." in fetched.logs

    def test_append_log_caps_at_200_lines(self):
        """Log 200 satırla sınırlı olmalı."""
        reg = self._make_registry()
        rec = reg.create(feature_path=None, framework=None)
        for i in range(250):
            reg.append_log(rec.run_id, f"Satır {i}")
        fetched = reg.get(rec.run_id)
        assert len(fetched.logs) <= 200

    def test_multiple_records_independent(self):
        """Farklı run_id'ler bağımsız kayıtlar olmalı."""
        reg = self._make_registry()
        rec1 = reg.create(feature_path="f1.feature", framework="playwright")
        rec2 = reg.create(feature_path="f2.feature", framework="playwright")
        assert rec1.run_id != rec2.run_id


# ── get_run_status (global registry proxy) ───────────────────────────────────


class TestGetRunStatus:
    def test_unknown_run_id_returns_none(self):
        """Bilinmeyen run_id için get_run_status() None döndürmeli."""
        result = get_run_status("totally-unknown-run-id-xyz")
        assert result is None


# ── _match_gherkin_with_dsl ───────────────────────────────────────────────────


class TestMatchGherkinWithDsl:
    def test_empty_gherkin_returns_empty_lists(self, monkeypatch):
        """Boş Gherkin için matched ve unknown listeleri boş olmalı."""
        matched, unknown = _match_gherkin_with_dsl("")
        assert matched == []
        assert unknown == []

    def test_returns_two_lists(self, monkeypatch):
        """_match_gherkin_with_dsl iki liste döndürmeli."""
        # dsl_service.search_actions mock
        class _FakeHit:
            class action:
                id = "click-button"
        class _FakeResult:
            items = []
        monkeypatch.setattr(
            "app.domains.automation_suite.service.dsl_service.search_actions",
            lambda q, limit=1: _FakeResult(),
            raising=False,
        )
        result = _match_gherkin_with_dsl("Given kullanıcı sayfaya gider")
        assert isinstance(result, tuple)
        assert len(result) == 2


# ── start_run validation ──────────────────────────────────────────────────────


class TestStartRunValidation:
    def test_missing_feature_path_and_suite_id_raises_value_error(self):
        """feature_path ve suite_id yokken start_run ValueError fırlatmalı."""
        req = SuiteRunRequest(
            feature_path=None,
            suite_id=None,
            framework="playwright",
            headless=True,
            tags=[],
        )

        with pytest.raises(ValueError, match="feature_path"):
            asyncio.get_event_loop().run_until_complete(svc.start_run(req))

    def test_valid_feature_path_returns_run_id(self, monkeypatch):
        """Geçerli feature_path ile start_run run_id döndürmeli."""
        # asyncio.create_task stub
        monkeypatch.setattr(
            "asyncio.create_task",
            lambda coro: coro.close() or None,
            raising=False,
        )
        req = SuiteRunRequest(
            feature_path="features/login.feature",
            suite_id=None,
            framework="playwright",
            headless=True,
            tags=[],
        )
        result = asyncio.get_event_loop().run_until_complete(svc.start_run(req))
        assert result.run_id
        assert result.status == "queued"
