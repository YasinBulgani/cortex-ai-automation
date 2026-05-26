"""Unit tests for app.domains.api_testing.service.

All DB interactions are mocked via MagicMock. No real HTTP calls made.
Tests cover: import_spec (validation), generate_tests_with_ai (endpoint collection,
AI agent invocation), and pure helper logic.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, call
from uuid import uuid4

import pytest

try:
    from app.domains.api_testing import service as api_testing_service
    from app.domains.api_testing.service import (
        import_spec,
        generate_tests_with_ai,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="api_testing service import failed")

PROJECT_ID = "proj-001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_spec_analysis(
    errors=None,
    title="Test API",
    version="1.0.0",
    spec_format="openapi3",
    endpoint_count=2,
    schema_count=3,
    critical_count=0,
    pii_endpoint_count=0,
    endpoints=None,
):
    analysis = MagicMock()
    analysis.errors = errors or []
    analysis.title = title
    analysis.version = version
    analysis.spec_format = spec_format
    analysis.endpoint_count = endpoint_count
    analysis.schema_count = schema_count
    analysis.critical_count = critical_count
    analysis.pii_endpoint_count = pii_endpoint_count
    analysis.endpoints = endpoints or []
    return analysis


def _make_db():
    db = MagicMock()
    db.add = MagicMock()
    db.flush = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    return db


def _make_endpoint_row(method="GET", path="/health", spec_id="spec-1"):
    ep = MagicMock()
    ep.id = str(uuid4())
    ep.method = method
    ep.path = path
    ep.spec_id = spec_id
    ep.operation_id = f"{method.lower()}_{path.replace('/', '_')}"
    ep.summary = "Test endpoint"
    ep.description = ""
    ep.tags = []
    ep.parameters = []
    ep.request_body_schema = {}
    ep.response_schemas = {}
    ep.risk_level = "low"
    ep.has_pii = False
    ep.has_financial = False
    ep.compliance_tags = []
    ep.depends_on = []
    return ep


# ---------------------------------------------------------------------------
# import_spec
# ---------------------------------------------------------------------------

class TestImportSpec:
    def test_raises_value_error_on_parse_errors(self):
        bad_analysis = _make_spec_analysis(errors=["Invalid YAML", "Missing 'info' key"])
        with patch.object(api_testing_service, "parse_spec", return_value=bad_analysis):
            with pytest.raises(ValueError, match="Spec parse hatalari"):
                import_spec(_make_db(), PROJECT_ID, content="{}")

    def test_valid_spec_returns_tuple(self):
        analysis = _make_spec_analysis()
        db = _make_db()
        with patch.object(api_testing_service, "parse_spec", return_value=analysis):
            result = import_spec(db, PROJECT_ID, content={"openapi": "3.0.0"}, name="MyAPI")
        assert isinstance(result, tuple) and len(result) == 2

    def test_valid_spec_calls_db_commit(self):
        analysis = _make_spec_analysis()
        db = _make_db()
        with patch.object(api_testing_service, "parse_spec", return_value=analysis):
            import_spec(db, PROJECT_ID, content={"openapi": "3.0.0"})
        db.commit.assert_called_once()

    def test_spec_name_uses_analysis_title_when_name_not_provided(self):
        analysis = _make_spec_analysis(title="Inferred API Title")
        db = _make_db()
        with patch.object(api_testing_service, "parse_spec", return_value=analysis):
            spec, _ = import_spec(db, PROJECT_ID, content={"openapi": "3.0.0"})
        assert spec.name == "Inferred API Title"

    def test_explicit_name_overrides_title(self):
        analysis = _make_spec_analysis(title="SomeTitle")
        db = _make_db()
        with patch.object(api_testing_service, "parse_spec", return_value=analysis):
            spec, _ = import_spec(db, PROJECT_ID, content={"openapi": "3.0.0"}, name="ExplicitName")
        assert spec.name == "ExplicitName"

    def test_endpoints_added_to_db(self):
        ep_info = MagicMock()
        ep_info.method = "POST"
        ep_info.path = "/users"
        ep_info.operation_id = "createUser"
        ep_info.summary = "Create user"
        ep_info.description = ""
        ep_info.tags = []
        ep_info.parameters = []
        ep_info.request_body_schema = {}
        ep_info.response_schemas = {}
        ep_info.security_requirements = []
        ep_info.auth_required = True
        ep_info.risk_level = "high"
        ep_info.has_pii = True
        ep_info.has_financial = False
        ep_info.compliance_tags = ["KVKK"]
        ep_info.depends_on = []
        analysis = _make_spec_analysis(endpoints=[ep_info])
        db = _make_db()
        with patch.object(api_testing_service, "parse_spec", return_value=analysis):
            import_spec(db, PROJECT_ID, content={"openapi": "3.0.0"})
        # db.add should be called at least twice: once for spec, once for endpoint
        assert db.add.call_count >= 2


# ---------------------------------------------------------------------------
# generate_tests_with_ai
# ---------------------------------------------------------------------------

class TestGenerateTestsWithAi:
    def _mock_agent(self, success=True, tests=None):
        agent = MagicMock()
        result = MagicMock()
        result.success = success
        result.error = None if success else "AI failure"
        result.data = {
            "test_cases": tests or [
                {"name": "TC1", "method": "GET", "path": "/health", "assertions": []}
            ]
        }
        agent.safe_run.return_value = result
        return agent

    def test_no_endpoints_returns_zero_generated(self):
        db = _make_db()
        db.query.return_value.filter.return_value.all.return_value = []
        with patch("app.domains.api_testing.service.ServiceTestAgent", return_value=self._mock_agent()):
            with patch.object(api_testing_service, "enrich_generation_prompt", return_value={}):
                result = generate_tests_with_ai(db, PROJECT_ID, endpoint_ids=["nonexistent"])
        assert result["generated_count"] == 0

    def test_ai_failure_returns_warning(self):
        ep = _make_endpoint_row()
        db = _make_db()
        db.query.return_value.filter.return_value.all.return_value = [ep]
        failed_agent = self._mock_agent(success=False)
        with patch("app.domains.api_testing.service.ServiceTestAgent", return_value=failed_agent):
            with patch.object(api_testing_service, "enrich_generation_prompt", return_value={}):
                result = generate_tests_with_ai(db, PROJECT_ID, endpoint_ids=[ep.id])
        assert result["generated_count"] == 0
        assert any("hatasi" in w.lower() or "error" in w.lower() or "üretim" in w.lower()
                   for w in result["warnings"])

    def test_result_contains_mode_key(self):
        db = _make_db()
        db.query.return_value.filter.return_value.all.return_value = []
        with patch("app.domains.api_testing.service.ServiceTestAgent", return_value=self._mock_agent()):
            with patch.object(api_testing_service, "enrich_generation_prompt", return_value={}):
                result = generate_tests_with_ai(db, PROJECT_ID, mode="security_test")
        assert result["mode"] == "security_test"

    def test_spec_id_path_queries_endpoints(self):
        ep = _make_endpoint_row()
        db = _make_db()
        # Mock db.query(...).filter(...).all() to return our endpoint
        db.query.return_value.filter.return_value.all.return_value = [ep]
        with patch("app.domains.api_testing.service.ServiceTestAgent", return_value=self._mock_agent()):
            with patch.object(api_testing_service, "enrich_generation_prompt", return_value={}):
                result = generate_tests_with_ai(db, PROJECT_ID, spec_id="spec-abc")
        assert "mode" in result

    def test_enrichment_failure_does_not_crash(self):
        db = _make_db()
        db.query.return_value.filter.return_value.all.return_value = []
        with patch("app.domains.api_testing.service.ServiceTestAgent", return_value=self._mock_agent()):
            with patch.object(api_testing_service, "enrich_generation_prompt",
                              side_effect=Exception("Redis down")):
                result = generate_tests_with_ai(db, PROJECT_ID)
        # Should still return a result dict, just with a warning
        assert isinstance(result, dict)

    def test_duration_ms_in_result(self):
        db = _make_db()
        db.query.return_value.filter.return_value.all.return_value = []
        with patch("app.domains.api_testing.service.ServiceTestAgent", return_value=self._mock_agent()):
            with patch.object(api_testing_service, "enrich_generation_prompt", return_value={}):
                result = generate_tests_with_ai(db, PROJECT_ID)
        assert "duration_ms" in result
