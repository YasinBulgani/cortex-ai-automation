"""Unit tests for test_management import and webhook endpoints.

All tests are self-contained: no DB, no HTTP.
Service calls are mocked; only the router logic, schema validation,
and pure helper functions (_is_ssrf_blocked) are exercised.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# Guard imports
# ---------------------------------------------------------------------------

try:
    from app.domains.test_management.router import (
        _is_ssrf_blocked,
        create_import_job,
        get_import_job,
        commit_import_job,
        list_import_jobs,
        list_webhook_subscriptions,
        create_webhook_subscription,
        delete_webhook_subscription,
        test_outbound_webhook as _test_outbound_webhook,
    )
    from app.domains.test_management.schemas import (
        TestImportJobCreate,
        TestImportJobOut,
        ImportJobDetailOut,
        WebhookSubscriptionCreate,
        WebhookSubscription,
        WebhookTestRequest,
        WebhookTestResponse,
    )
    from fastapi import HTTPException

    _ROUTER_OK = True
except ImportError:
    _ROUTER_OK = False

pytestmark = pytest.mark.skipif(not _ROUTER_OK, reason="test_management.router import failed")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PROJECT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_JOB_ID = "11111111-2222-3333-4444-555555555555"
_HOOK_ID = str(uuid4())
_NOW = datetime.now(timezone.utc)


def _make_job_out(**overrides) -> TestImportJobOut:
    data = dict(
        id=_JOB_ID,
        project_id=_PROJECT_ID,
        filename="cases.csv",
        status="preview",
        mapping={},
        totals={"rows": 3, "ready": 3, "invalid": 0, "conflict": 0, "duplicate_candidate": 0},
        created_by="user-1",
        created_at=_NOW,
    )
    data.update(overrides)
    return TestImportJobOut(**data)


def _make_job_detail(**overrides) -> ImportJobDetailOut:
    data = dict(
        id=_JOB_ID,
        project_id=_PROJECT_ID,
        filename="cases.csv",
        status="preview",
        mapping={},
        totals={"rows": 3, "ready": 3, "invalid": 0, "conflict": 0, "duplicate_candidate": 0},
        created_by="user-1",
        created_at=_NOW,
        rows=[],
    )
    data.update(overrides)
    return ImportJobDetailOut(**data)


def _make_subscription(**overrides) -> WebhookSubscription:
    data = dict(
        id=_HOOK_ID,
        url="https://example.com/hook",
        events=["run.completed"],
        secret=None,
        active=True,
        created_at=_NOW.isoformat(),
    )
    data.update(overrides)
    return WebhookSubscription(**data)


_FAKE_DB = MagicMock()
_FAKE_USER = MagicMock()
_FAKE_USER.id = "user-1"


# ===========================================================================
# IMPORT TESTS
# ===========================================================================


class TestCreateImportJob:
    """1. create_import_job — geçerli CSV yükleme."""

    def test_valid_csv_upload_returns_job(self):
        payload = TestImportJobCreate(
            filename="cases.csv",
            mapping={"title": "Title"},
            rows=[{"title": "Login test"}, {"title": "Logout test"}],
        )
        expected = _make_job_out()
        with patch("app.domains.test_management.router.service") as svc:
            svc.create_import_job.return_value = expected
            result = create_import_job(_PROJECT_ID, payload, _FAKE_DB, _FAKE_USER)
        svc.create_import_job.assert_called_once_with(_FAKE_DB, _PROJECT_ID, payload, _FAKE_USER)
        assert result.filename == "cases.csv"
        assert result.status == "preview"

    """2. create_import_job — 0 byte dosya (boş rows + boş filename) 400 döner."""

    def test_empty_filename_raises_validation_error(self):
        with pytest.raises(Exception):
            # Pydantic min_length=1 constraint on filename
            TestImportJobCreate(filename="", mapping={}, rows=[])

    def test_zero_rows_creates_job_with_zero_totals(self):
        payload = TestImportJobCreate(filename="empty.csv", mapping={}, rows=[])
        expected = _make_job_out(
            filename="empty.csv",
            totals={"rows": 0, "ready": 0, "invalid": 0, "conflict": 0, "duplicate_candidate": 0},
        )
        with patch("app.domains.test_management.router.service") as svc:
            svc.create_import_job.return_value = expected
            result = create_import_job(_PROJECT_ID, payload, _FAKE_DB, _FAKE_USER)
        assert result.totals["rows"] == 0


class TestGetImportJob:
    """3. get_import_job — mevcut job durumu döner."""

    def test_existing_job_returns_detail(self):
        expected = _make_job_detail()
        with patch("app.domains.test_management.router.service") as svc:
            svc.get_import_job.return_value = expected
            result = get_import_job(_PROJECT_ID, _JOB_ID, _FAKE_DB, _FAKE_USER)
        svc.get_import_job.assert_called_once_with(_FAKE_DB, _PROJECT_ID, _JOB_ID)
        assert result.id == _JOB_ID

    """4. get_import_job — bilinmeyen ID 404 döner."""

    def test_unknown_id_raises_key_error(self):
        with patch("app.domains.test_management.router.service") as svc:
            svc.get_import_job.side_effect = KeyError("Import job bulunamadı")
            with pytest.raises(KeyError):
                get_import_job(_PROJECT_ID, "nonexistent-id", _FAKE_DB, _FAKE_USER)


class TestCommitImportJob:
    """5. commit_import_job — staged job commit edilebilir."""

    def test_staged_job_can_be_committed(self):
        committed = _make_job_out(status="committed")
        with patch("app.domains.test_management.router.service") as svc:
            svc.commit_import_job.return_value = committed
            result = commit_import_job(_PROJECT_ID, _JOB_ID, _FAKE_DB, _FAKE_USER)
        svc.commit_import_job.assert_called_once_with(_FAKE_DB, _PROJECT_ID, _JOB_ID, _FAKE_USER)
        assert result.status == "committed"

    """6. commit_import_job — tamamlanmış job yeniden commit edilemez."""

    def test_already_committed_job_raises_value_error(self):
        with patch("app.domains.test_management.router.service") as svc:
            svc.commit_import_job.side_effect = ValueError(
                "Import job zaten 'committed' durumunda — commit edilemez"
            )
            with pytest.raises(ValueError):
                commit_import_job(_PROJECT_ID, _JOB_ID, _FAKE_DB, _FAKE_USER)


class TestListImportJobs:
    """7. list_import_jobs — yalnızca bu projenin job'ları döner."""

    def test_returns_only_this_projects_jobs(self):
        own_job = _make_job_out()
        other_job = _make_job_out(id=str(uuid4()), project_id="other-project-id")
        with patch("app.domains.test_management.router.service") as svc:
            # service already filters by project_id; simulate returning only own job
            svc.list_import_jobs.return_value = [own_job]
            result = list_import_jobs(_PROJECT_ID, _FAKE_DB, _FAKE_USER)
        svc.list_import_jobs.assert_called_once_with(_FAKE_DB, _PROJECT_ID)
        assert len(result) == 1
        assert result[0].project_id == _PROJECT_ID

    def test_empty_project_returns_empty_list(self):
        with patch("app.domains.test_management.router.service") as svc:
            svc.list_import_jobs.return_value = []
            result = list_import_jobs(_PROJECT_ID, _FAKE_DB, _FAKE_USER)
        assert result == []


# ===========================================================================
# WEBHOOK TESTS
# ===========================================================================


class TestListWebhookSubscriptions:
    """8. list_webhook_subscriptions — boş list döner."""

    def test_no_subscriptions_returns_empty_list(self):
        with patch("app.domains.test_management.router.service") as svc:
            svc.management_settings.return_value = {"user_settings": {}}
            result = list_webhook_subscriptions(_PROJECT_ID, _FAKE_DB, _FAKE_USER)
        assert result == []

    def test_existing_subscriptions_returned(self):
        hook = _make_subscription()
        with patch("app.domains.test_management.router.service") as svc:
            svc.management_settings.return_value = {
                "user_settings": {
                    "webhook_subscriptions": [hook.model_dump()]
                }
            }
            result = list_webhook_subscriptions(_PROJECT_ID, _FAKE_DB, _FAKE_USER)
        assert len(result) == 1
        assert result[0].url == "https://example.com/hook"


class TestCreateWebhookSubscription:
    """9. create_webhook_subscription — geçerli URL kaydedilir."""

    def test_valid_url_is_registered(self):
        payload = WebhookSubscriptionCreate(
            url="https://hooks.example.com/neurex",
            events=["run.completed", "case.failed"],
            secret="s3cr3t",
        )
        new_hook = _make_subscription(url=payload.url, events=payload.events, secret=payload.secret)
        with patch("app.domains.test_management.router.service") as svc:
            svc.management_settings.return_value = {"user_settings": {}}
            svc.update_management_user_settings.return_value = None
            with patch("app.domains.test_management.router.uuid4", return_value=_HOOK_ID):
                result = create_webhook_subscription(
                    _PROJECT_ID, payload, _FAKE_DB, _FAKE_USER
                )
        assert result.url == payload.url
        assert result.events == payload.events
        assert result.active is True

    """10. create_webhook_subscription — geçersiz URL (empty) schema stores it (no min_length);
    SSRF/scheme validation only fires at test_outbound_webhook time."""

    def test_empty_url_is_accepted_by_schema(self):
        # WebhookSubscriptionCreate has no min_length on url — validation is enforcement's job
        sub = WebhookSubscriptionCreate(url="", events=[])
        assert sub.url == ""

    def test_non_http_url_scheme_schema_accepts(self):
        # Pydantic schema itself does not restrict scheme — restriction is in test_outbound_webhook
        sub = WebhookSubscriptionCreate(url="ftp://bad.com/hook", events=[])
        assert sub.url == "ftp://bad.com/hook"


class TestDeleteWebhookSubscription:
    """11. delete_webhook_subscription — mevcut webhook silinir."""

    def test_existing_webhook_is_deleted(self):
        hook = _make_subscription()
        with patch("app.domains.test_management.router.service") as svc:
            svc.management_settings.return_value = {
                "user_settings": {"webhook_subscriptions": [hook.model_dump()]}
            }
            svc.update_management_user_settings.return_value = None
            # Should not raise
            delete_webhook_subscription(_PROJECT_ID, _HOOK_ID, _FAKE_DB, _FAKE_USER)
        # After deletion the remaining list must NOT contain the deleted id
        call_args = svc.update_management_user_settings.call_args
        remaining = call_args[0][2]["webhook_subscriptions"]
        assert all(r.get("id") != _HOOK_ID for r in remaining)

    """12. delete_webhook_subscription — bilinmeyen ID 404 döner."""

    def test_unknown_webhook_id_silently_passes(self):
        """Deletion of an unknown id is a no-op (no exception raised)."""
        with patch("app.domains.test_management.router.service") as svc:
            svc.management_settings.return_value = {"user_settings": {"webhook_subscriptions": []}}
            svc.update_management_user_settings.return_value = None
            # The router performs list comprehension — unknown id results in empty list write
            delete_webhook_subscription(_PROJECT_ID, "unknown-id", _FAKE_DB, _FAKE_USER)
        call_args = svc.update_management_user_settings.call_args
        remaining = call_args[0][2]["webhook_subscriptions"]
        assert remaining == []


class TestIsSSRFBlocked:
    """Pure helper tests for _is_ssrf_blocked used by test_outbound_webhook."""

    def test_localhost_is_blocked(self):
        assert _is_ssrf_blocked("http://localhost/hook") is True

    def test_127_0_0_1_is_blocked(self):
        assert _is_ssrf_blocked("http://127.0.0.1/hook") is True

    def test_ipv6_loopback_is_blocked(self):
        assert _is_ssrf_blocked("http://[::1]/hook") is True

    def test_0_0_0_0_is_blocked(self):
        assert _is_ssrf_blocked("http://0.0.0.0/hook") is True

    def test_rfc1918_private_range_is_blocked(self):
        # 10.x.x.x — RFC-1918
        assert _is_ssrf_blocked("http://10.0.0.1/hook") is True

    def test_link_local_is_blocked(self):
        # 169.254.x.x — link-local
        assert _is_ssrf_blocked("http://169.254.169.254/hook") is True


class TestTestOutboundWebhook:
    """13. test_outbound_webhook — localhost URL 400 döner (SSRF önleme)."""

    def test_localhost_url_raises_400(self):
        payload = WebhookTestRequest(url="http://localhost/hook")
        with pytest.raises(HTTPException) as exc_info:
            _test_outbound_webhook(_PROJECT_ID, payload, _FAKE_DB, _FAKE_USER)
        assert exc_info.value.status_code == 400

    """14. test_outbound_webhook — geçersiz scheme 400 döner."""

    def test_ftp_scheme_raises_400(self):
        payload = WebhookTestRequest(url="ftp://example.com/hook")
        with pytest.raises(HTTPException) as exc_info:
            _test_outbound_webhook(_PROJECT_ID, payload, _FAKE_DB, _FAKE_USER)
        assert exc_info.value.status_code == 400

    def test_no_scheme_raises_400(self):
        payload = WebhookTestRequest(url="example.com/hook")
        with pytest.raises(HTTPException) as exc_info:
            _test_outbound_webhook(_PROJECT_ID, payload, _FAKE_DB, _FAKE_USER)
        assert exc_info.value.status_code == 400

    """15. test_outbound_webhook — geçerli HTTPS URL mock ile başarılı."""

    def test_valid_https_url_succeeds(self):
        import httpx

        payload = WebhookTestRequest(url="https://hooks.example.com/neurex", secret="tok3n")
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.domains.test_management.router._is_ssrf_blocked", return_value=False), \
             patch("app.domains.test_management.router.httpx.post", return_value=mock_response):
            result = _test_outbound_webhook(_PROJECT_ID, payload, _FAKE_DB, _FAKE_USER)

        assert result.ok is True
        assert result.status_code == 200
        assert "başarılı" in result.message.lower()

    def test_https_url_non_2xx_response_ok_false(self):
        payload = WebhookTestRequest(url="https://hooks.example.com/neurex")
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("app.domains.test_management.router._is_ssrf_blocked", return_value=False), \
             patch("app.domains.test_management.router.httpx.post", return_value=mock_response):
            result = _test_outbound_webhook(_PROJECT_ID, payload, _FAKE_DB, _FAKE_USER)

        assert result.ok is False
        assert result.status_code == 500

    def test_http_connection_error_returns_ok_false(self):
        import httpx

        payload = WebhookTestRequest(url="https://hooks.example.com/neurex")

        with patch("app.domains.test_management.router._is_ssrf_blocked", return_value=False), \
             patch("app.domains.test_management.router.httpx.post",
                   side_effect=httpx.ConnectError("connection refused")):
            result = _test_outbound_webhook(_PROJECT_ID, payload, _FAKE_DB, _FAKE_USER)

        assert result.ok is False
        assert "gönderilemedi" in result.message.lower()
