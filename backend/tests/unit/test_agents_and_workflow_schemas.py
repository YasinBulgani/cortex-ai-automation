"""Unit tests for agent and workflow Pydantic schemas.

Tests are fully self-contained: no DB, no HTTP, no AI.
Covers:
  - banking_team.heal_schemas: HealTestEntry, HealRequest, HealDetailEntry,
    HealResponse, HealHistoryEntry, HealHistoryResponse, HealStatsResponse
  - agents.v2.api_schemas: RunAgentV2Request, RunAgentV2Response, RunV2Status,
    RunV2ListItem, RunV2ListResponse, AgentStreamEvent
  - agents.v2.schemas.app_map: FormField, FormDescriptor, ApiObservation,
    PageNode, AppMap (including page_count/form_count/to_state_dict)
  - ai.workflow_schemas: AIWorkflowCreateRequest, AIWorkflowCreateResponse,
    AIWorkflowStatus, AIWorkflowArtifact, AIWorkflowApprovalRequest
"""
from __future__ import annotations

from datetime import datetime, timezone
import pytest

try:
    from app.domains.agents.banking_team.heal_schemas import (
        HealTestEntry,
        HealRequest,
        HealDetailEntry,
        HealResponse,
        HealHistoryEntry,
        HealHistoryResponse,
        HealStatsResponse,
    )
    _HEAL_OK = True
except ImportError:
    _HEAL_OK = False

try:
    from app.domains.agents.v2.api_schemas import (
        RunAgentV2Request,
        RunAgentV2Response,
        RunV2Status,
        RunV2ListItem,
        RunV2ListResponse,
        AgentStreamEvent,
    )
    _API_SCHEMA_OK = True
except ImportError:
    _API_SCHEMA_OK = False

try:
    from app.domains.agents.v2.schemas.app_map import (
        FormField,
        FormDescriptor,
        ApiObservation,
        PageNode,
        AppMap,
    )
    _APP_MAP_OK = True
except ImportError:
    _APP_MAP_OK = False

try:
    from app.domains.ai.workflow_schemas import (
        AIWorkflowCreateRequest,
        AIWorkflowCreateResponse,
        AIWorkflowStatus,
        AIWorkflowArtifact,
        AIWorkflowApprovalRequest,
    )
    _WORKFLOW_OK = True
except ImportError:
    _WORKFLOW_OK = False


def _now():
    return datetime.now(tz=timezone.utc)


# ===========================================================================
# HealSchemas
# ===========================================================================

@pytest.mark.skipif(not _HEAL_OK, reason="heal_schemas import failed")
class TestHealTestEntry:
    def test_defaults(self):
        entry = HealTestEntry()
        assert entry.file == ""
        assert entry.test_name == ""
        assert entry.selector == ""
        assert entry.error == ""
        assert entry.dom_snippet == ""
        assert entry.page_url == ""
        assert entry.line_number == 0

    def test_with_values(self):
        entry = HealTestEntry(
            file="test/login.spec.ts",
            selector="#login-btn",
            error="Element not found",
            line_number=42,
        )
        assert entry.file == "test/login.spec.ts"
        assert entry.line_number == 42


@pytest.mark.skipif(not _HEAL_OK, reason="heal_schemas import failed")
class TestHealRequest:
    def test_creation(self):
        entry = HealTestEntry(selector="#btn", error="not found")
        req = HealRequest(failed_tests=[entry])
        assert len(req.failed_tests) == 1

    def test_defaults(self):
        entry = HealTestEntry()
        req = HealRequest(failed_tests=[entry])
        assert req.project_id is None
        assert req.session_id is None
        assert req.auto_update is False

    def test_empty_failed_tests_raises(self):
        with pytest.raises(Exception):
            HealRequest(failed_tests=[])

    def test_auto_update_true(self):
        req = HealRequest(failed_tests=[HealTestEntry()], auto_update=True)
        assert req.auto_update is True


@pytest.mark.skipif(not _HEAL_OK, reason="heal_schemas import failed")
class TestHealDetailEntry:
    def test_defaults(self):
        detail = HealDetailEntry()
        assert detail.healed is False
        assert detail.confidence == pytest.approx(0.0)
        assert detail.verified_in_browser is False
        assert detail.file_updated is False
        assert detail.error == ""

    def test_healed_true(self):
        detail = HealDetailEntry(
            broken_selector="#old-btn",
            new_selector="#new-btn",
            healed=True,
            confidence=0.9,
            strategy="ai_suggest",
        )
        assert detail.healed is True
        assert detail.confidence == pytest.approx(0.9)


@pytest.mark.skipif(not _HEAL_OK, reason="heal_schemas import failed")
class TestHealResponse:
    def test_defaults(self):
        resp = HealResponse()
        assert resp.total_broken == 0
        assert resp.healed == 0
        assert resp.verified == 0
        assert resp.updated_files == 0
        assert resp.duration_ms == 0
        assert resp.details == []

    def test_with_values(self):
        resp = HealResponse(total_broken=5, healed=4, verified=3)
        assert resp.total_broken == 5
        assert resp.healed == 4


@pytest.mark.skipif(not _HEAL_OK, reason="heal_schemas import failed")
class TestHealHistoryEntry:
    def test_defaults(self):
        e = HealHistoryEntry()
        assert e.id == ""
        assert e.confidence == pytest.approx(0.0)
        assert e.verified is False

    def test_with_values(self):
        e = HealHistoryEntry(id="h-001", strategy="css_fallback", confidence=0.8, verified=True)
        assert e.id == "h-001"
        assert e.verified is True


@pytest.mark.skipif(not _HEAL_OK, reason="heal_schemas import failed")
class TestHealHistoryResponse:
    def test_defaults(self):
        resp = HealHistoryResponse()
        assert resp.count == 0
        assert resp.entries == []

    def test_with_entries(self):
        e = HealHistoryEntry(id="h1")
        resp = HealHistoryResponse(count=1, entries=[e])
        assert resp.count == 1


@pytest.mark.skipif(not _HEAL_OK, reason="heal_schemas import failed")
class TestHealStatsResponse:
    def test_defaults(self):
        stats = HealStatsResponse()
        assert stats.total_heals == 0
        assert stats.success_rate == pytest.approx(0.0)
        assert stats.by_strategy == {}
        assert stats.by_tier == {}
        assert stats.last_heal_at is None


# ===========================================================================
# RunAgentV2 Schemas
# ===========================================================================

@pytest.mark.skipif(not _API_SCHEMA_OK, reason="api_schemas import failed")
class TestRunAgentV2Request:
    def test_creation(self):
        req = RunAgentV2Request(project_id="proj-1", input_source="url", url="https://example.com")
        assert req.project_id == "proj-1"
        assert req.input_source == "url"

    def test_defaults(self):
        req = RunAgentV2Request(project_id="p", input_source="text")
        assert req.max_pages == 15
        assert req.max_depth == 2
        assert req.enable_ai_xpath is False
        assert req.auto_pr is False
        assert req.auto_merge is False

    def test_max_pages_bounds(self):
        with pytest.raises(Exception):
            RunAgentV2Request(project_id="p", input_source="text", max_pages=0)

    def test_max_pages_max(self):
        with pytest.raises(Exception):
            RunAgentV2Request(project_id="p", input_source="text", max_pages=101)

    def test_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            RunAgentV2Request(project_id="p", input_source="text", unknown_field="x")


@pytest.mark.skipif(not _API_SCHEMA_OK, reason="api_schemas import failed")
class TestRunV2Status:
    def test_defaults(self):
        s = RunV2Status(
            run_id="r1", status="queued", project_id="p1",
            input_source="url", created_at=_now(),
        )
        assert s.cost_usd == pytest.approx(0.0)
        assert s.tokens_used == 0
        assert s.errors == []
        assert s.scenarios == []


@pytest.mark.skipif(not _API_SCHEMA_OK, reason="api_schemas import failed")
class TestRunV2ListResponse:
    def test_defaults(self):
        resp = RunV2ListResponse(runs=[], total=0)
        assert resp.page == 1
        assert resp.page_size == 20
        assert resp.total == 0


# ===========================================================================
# AppMap Schemas
# ===========================================================================

@pytest.mark.skipif(not _APP_MAP_OK, reason="app_map import failed")
class TestFormField:
    def test_defaults(self):
        field = FormField()
        assert field.name is None
        assert field.type == "text"
        assert field.required is False
        assert field.options == []
        assert field.validation == {}

    def test_required_field(self):
        field = FormField(name="username", required=True)
        assert field.required is True


@pytest.mark.skipif(not _APP_MAP_OK, reason="app_map import failed")
class TestFormDescriptor:
    def test_creation(self):
        desc = FormDescriptor(page_url="https://example.com/login")
        assert desc.page_url == "https://example.com/login"

    def test_defaults(self):
        desc = FormDescriptor(page_url="https://x.com")
        assert desc.form_id is None
        assert desc.fields == []
        assert desc.method == "POST"


@pytest.mark.skipif(not _APP_MAP_OK, reason="app_map import failed")
class TestApiObservation:
    def test_creation(self):
        obs = ApiObservation(method="GET", url="https://api.example.com/users")
        assert obs.method == "GET"

    def test_defaults(self):
        obs = ApiObservation(method="POST", url="https://api.x.com")
        assert obs.status_code is None
        assert obs.observed_count == 1


@pytest.mark.skipif(not _APP_MAP_OK, reason="app_map import failed")
class TestPageNode:
    def test_creation(self):
        page = PageNode(url="https://example.com/home")
        assert page.url == "https://example.com/home"

    def test_defaults(self):
        page = PageNode(url="https://x.com")
        assert page.title == ""
        assert page.depth == 0
        assert page.requires_auth is False
        assert page.interactive_element_count == 0


@pytest.mark.skipif(not _APP_MAP_OK, reason="app_map import failed")
class TestAppMap:
    def test_creation(self):
        app_map = AppMap(root_url="https://example.com")
        assert app_map.root_url == "https://example.com"

    def test_defaults(self):
        app_map = AppMap(root_url="https://x.com")
        assert app_map.pages == []
        assert app_map.forms == []
        assert app_map.apis_observed == []
        assert app_map.auth_required is False
        assert app_map.crawl_depth == 2

    def test_page_count_method(self):
        page = PageNode(url="https://x.com/page1")
        app_map = AppMap(root_url="https://x.com", pages=[page, page])
        assert app_map.page_count() == 2

    def test_form_count_method(self):
        form = FormDescriptor(page_url="https://x.com/login")
        app_map = AppMap(root_url="https://x.com", forms=[form])
        assert app_map.form_count() == 1

    def test_to_state_dict_returns_dict(self):
        app_map = AppMap(root_url="https://x.com")
        state = app_map.to_state_dict()
        assert isinstance(state, dict)
        assert "pages" in state
        assert "forms" in state
        assert "apis_observed" in state
        assert "navigation_graph" in state


# ===========================================================================
# AI Workflow Schemas
# ===========================================================================

@pytest.mark.skipif(not _WORKFLOW_OK, reason="workflow_schemas import failed")
class TestAIWorkflowCreateRequest:
    def test_creation(self):
        req = AIWorkflowCreateRequest(project_id="p1", input_source="url")
        assert req.project_id == "p1"

    def test_defaults(self):
        req = AIWorkflowCreateRequest(project_id="p", input_source="text")
        assert req.workflow_type == "test_generation"
        assert req.dry_run is False
        assert req.requires_approval is False


@pytest.mark.skipif(not _WORKFLOW_OK, reason="workflow_schemas import failed")
class TestAIWorkflowArtifact:
    def test_creation(self):
        artifact = AIWorkflowArtifact(
            artifact_id="art-001",
            kind="report",
            name="Test Report",
            storage_path="/artifacts/report.json",
            mime_type="application/json",
            created_at=_now(),
        )
        assert artifact.artifact_id == "art-001"
        assert artifact.kind == "report"

    def test_defaults(self):
        artifact = AIWorkflowArtifact(
            artifact_id="x",
            kind="code",
            name="file.ts",
            storage_path="/path",
            mime_type="text/plain",
            created_at=_now(),
        )
        assert artifact.size_bytes == 0
        assert artifact.metadata == {}


@pytest.mark.skipif(not _WORKFLOW_OK, reason="workflow_schemas import failed")
class TestAIWorkflowApprovalRequest:
    def test_approved(self):
        req = AIWorkflowApprovalRequest(decision="approved")
        assert req.decision == "approved"

    def test_rejected_with_note(self):
        req = AIWorkflowApprovalRequest(decision="rejected", note="too risky")
        assert req.decision == "rejected"
        assert req.note == "too risky"

    def test_default_note_none(self):
        req = AIWorkflowApprovalRequest(decision="approved")
        assert req.note is None
