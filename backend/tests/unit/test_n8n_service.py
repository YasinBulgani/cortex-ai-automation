"""Unit tests for app.domains.n8n.service facade.

Covers: list_workflows, trigger_workflow, get_execution
External HTTP calls and DB sessions are fully mocked.
"""
from __future__ import annotations

import pytest

try:
    from unittest.mock import MagicMock, patch, PropertyMock
    import app.domains.n8n.service as n8n_svc  # noqa: F401
except ImportError as _exc:
    pytestmark = pytest.mark.skipif(True, reason=f"n8n service not importable: {_exc}")
    n8n_svc = None  # type: ignore


# ---------------------------------------------------------------------------
# list_workflows
# ---------------------------------------------------------------------------

class TestListWorkflows:
    def test_list_workflows_no_api_key_raises_value_error(self, monkeypatch):
        """list_workflows raises ValueError when N8N_API_KEY is empty."""
        monkeypatch.setattr(n8n_svc, "_N8N_API_KEY", "")
        with pytest.raises(ValueError, match="N8N_API_KEY"):
            n8n_svc.list_workflows()

    def test_list_workflows_returns_list_from_api(self, monkeypatch):
        """list_workflows returns the 'data' array from n8n API response."""
        monkeypatch.setattr(n8n_svc, "_N8N_API_KEY", "test-key")
        wf_list = [{"id": "wf-1", "name": "Workflow One"}]

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": wf_list}
        mock_resp.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("app.domains.n8n.service.httpx.Client", return_value=mock_client):
            result = n8n_svc.list_workflows()

        assert isinstance(result, list)
        assert result[0]["id"] == "wf-1"

    def test_list_workflows_http_error_raises_value_error(self, monkeypatch):
        """HTTPError from n8n is re-raised as ValueError."""
        import httpx
        monkeypatch.setattr(n8n_svc, "_N8N_API_KEY", "test-key")

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.ConnectError("connection refused")

        with patch("app.domains.n8n.service.httpx.Client", return_value=mock_client):
            with pytest.raises(ValueError, match="n8n bağlantı hatası"):
                n8n_svc.list_workflows()


# ---------------------------------------------------------------------------
# trigger_workflow
# ---------------------------------------------------------------------------

class TestTriggerWorkflow:
    def _make_db(self, workflow=None):
        db = MagicMock()
        db.get.return_value = workflow
        return db

    def _make_workflow(self, webhook_url="https://n8n.example/webhook/abc"):
        wf = MagicMock()
        wf.config = {"webhook_url": webhook_url}
        return wf

    def test_trigger_workflow_not_found_raises_key_error(self):
        """Missing workflow link raises KeyError with the ID in the message."""
        db = self._make_db(workflow=None)
        with pytest.raises(KeyError, match="wf-missing"):
            n8n_svc.trigger_workflow(db, "wf-missing")

    def test_trigger_workflow_no_webhook_url_raises_value_error(self):
        """Workflow config without webhook_url raises ValueError."""
        wf = MagicMock()
        wf.config = {}
        db = self._make_db(workflow=wf)
        with pytest.raises(ValueError, match="webhook_url"):
            n8n_svc.trigger_workflow(db, "wf-no-url")

    def test_trigger_workflow_success_returns_expected_keys(self):
        """Happy path returns dict with workflow_link_id and n8n_response."""
        wf = self._make_workflow()
        db = self._make_db(workflow=wf)

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"executionId": "exec-99"}
        mock_resp.content = b'{"executionId": "exec-99"}'
        mock_resp.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp

        with patch("app.domains.n8n.service.httpx.Client", return_value=mock_client):
            result = n8n_svc.trigger_workflow(db, "wf-1", payload={"key": "val"})

        assert result["workflow_link_id"] == "wf-1"
        assert "n8n_response" in result

    def test_trigger_workflow_http_error_raises_value_error(self):
        """HTTPError during webhook POST is wrapped in ValueError."""
        import httpx
        wf = self._make_workflow()
        db = self._make_db(workflow=wf)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.TimeoutException("timed out")

        with patch("app.domains.n8n.service.httpx.Client", return_value=mock_client):
            with pytest.raises(ValueError, match="webhook çağrısı başarısız"):
                n8n_svc.trigger_workflow(db, "wf-1")


# ---------------------------------------------------------------------------
# get_execution
# ---------------------------------------------------------------------------

class TestGetExecution:
    def test_get_execution_not_found_raises_key_error(self):
        """Missing execution raises KeyError containing the execution ID."""
        db = MagicMock()
        db.get.return_value = None
        with pytest.raises(KeyError, match="exec-missing"):
            n8n_svc.get_execution(db, "exec-missing")

    def test_get_execution_found_returns_dict(self):
        """Existing execution is returned as a column-keyed dict."""
        col1 = MagicMock()
        col1.key = "id"
        col2 = MagicMock()
        col2.key = "status"

        ex = MagicMock()
        ex.id = "exec-1"
        ex.status = "success"
        ex.__table__ = MagicMock()
        ex.__table__.columns = [col1, col2]

        db = MagicMock()
        db.get.return_value = ex

        result = n8n_svc.get_execution(db, "exec-1")
        assert result["id"] == "exec-1"
        assert result["status"] == "success"
