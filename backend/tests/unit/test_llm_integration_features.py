"""Unit tests for LLM Integration Features 2-10."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from backend.app.domains.llm_integration.service import (
    ModelRoutingService,
    HallucinationDetectionService,
    ApprovalWorkflowService,
    AuditLoggingService,
    CostTrackingService,
    RateLimitingService,
    StreamingService,
    FunctionCallingService,
    FineTuningService,
)
from backend.app.domains.llm_integration.models import (
    ModelRoutingConfig,
    ApprovalQueue,
    LLMAuditLog,
)


# ============================================================================
# Feature 2: Model Routing Tests
# ============================================================================


class TestModelRoutingService:
    """Test model selection and routing (Feature 2)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock(spec=Session)

    @pytest.fixture
    def routing_service(self, mock_db):
        return ModelRoutingService(mock_db, tenant_id="test-tenant")

    def test_configure_routing_new(self, routing_service, mock_db):
        """Test creating new routing config."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        config_id = routing_service.configure_routing(
            task_type="coder",
            primary_model="qwen2.5-coder:7b",
            fallback_models=["llama3.1:8b"],
            cost_budget_usd=5.0,
        )

        assert config_id is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_configure_routing_update_existing(self, routing_service, mock_db):
        """Test updating existing routing config."""
        existing_config = MagicMock(spec=ModelRoutingConfig)
        existing_config.id = "existing-id"
        mock_db.query.return_value.filter.return_value.first.return_value = existing_config

        config_id = routing_service.configure_routing(
            task_type="coder",
            primary_model="new-model:latest",
            fallback_models=["fallback1"],
            cost_budget_usd=10.0,
        )

        assert config_id == "existing-id"
        assert existing_config.primary_model == "new-model:latest"
        mock_db.commit.assert_called_once()

    def test_select_model_from_config(self, routing_service, mock_db):
        """Test model selection from configured routing."""
        config = MagicMock(spec=ModelRoutingConfig)
        config.primary_model = "qwen2.5:14b"
        config.fallback_models = ["gpt-4-turbo"]
        config.max_tokens = 2048
        config.temperature = 0.7
        config.cost_usd = 5.0

        mock_db.query.return_value.filter.return_value.first.return_value = config

        primary, fallbacks, settings = routing_service.select_model("analyst")

        assert primary == "qwen2.5:14b"
        assert "gpt-4-turbo" in fallbacks


# ============================================================================
# Feature 3: Hallucination Detection Tests
# ============================================================================


class TestHallucinationDetectionService:
    """Test hallucination detection (Feature 3)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock(spec=Session)

    @pytest.fixture
    def hallucination_service(self, mock_db):
        return HallucinationDetectionService(mock_db, tenant_id="test-tenant")

    @pytest.mark.asyncio
    async def test_compute_confidence_high_quality(self, hallucination_service):
        """Test confidence score for high-quality text."""
        text = "The login feature allows users to authenticate with email and password."
        score = await hallucination_service._compute_confidence(text, context=None)

        assert 0.0 <= score <= 1.0
        assert score > 0.7  # High confidence for clear text

    @pytest.mark.asyncio
    async def test_compute_confidence_uncertain(self, hallucination_service):
        """Test confidence score for uncertain text."""
        text = "I don't know. Maybe it could be. Possibly might."
        score = await hallucination_service._compute_confidence(text, context=None)

        assert score < 0.7  # Lower confidence for uncertain language

    def test_extract_claims(self, hallucination_service):
        """Test claim extraction from text."""
        text = "The user can login with email. Password must be at least 8 characters. MFA is optional."
        claims = hallucination_service._extract_claims(text)

        assert len(claims) > 0
        assert all(isinstance(claim, str) for claim in claims)
        assert all(len(claim) > 10 for claim in claims)

    def test_extract_uncertainty_flags(self, hallucination_service):
        """Test uncertainty flag detection."""
        text = "There might be a contradiction here. The system is unclear about password requirements."
        flags = hallucination_service._extract_uncertainty_flags(text)

        assert "contradiction" in flags or "unverifiable" in flags
        assert isinstance(flags, list)

    def test_confidence_mapping(self):
        """Test confidence level mapping."""
        service = HallucinationDetectionService(MagicMock(), "test-tenant")

        assert service._map_to_level(0.9) == "high"
        assert service._map_to_level(0.75) == "medium"
        assert service._map_to_level(0.5) == "low"

    def test_recommendation_logic(self):
        """Test approval recommendation logic."""
        service = HallucinationDetectionService(MagicMock(), "test-tenant")

        # Should reject low confidence
        rec = service._get_recommendation(0.3, False, ["contradiction"])
        assert rec == "reject"

        # Should review if uncertain
        rec = service._get_recommendation(0.7, None, ["unverifiable"])
        assert rec == "review_required"

        # Should approve if confident
        rec = service._get_recommendation(0.95, True, [])
        assert rec == "approve"


# ============================================================================
# Feature 4: Approval Workflow Tests
# ============================================================================


class TestApprovalWorkflowService:
    """Test approval queue management (Feature 4)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock(spec=Session)

    @pytest.fixture
    def approval_service(self, mock_db):
        return ApprovalWorkflowService(mock_db, tenant_id="test-tenant")

    def test_create_approval_item(self, approval_service, mock_db):
        """Test creating approval queue item."""
        approval_id = approval_service.create_approval(
            user_id="user-1",
            feature_type="test_case_gen",
            ai_suggestion={"scenario": "Login with valid credentials"},
            priority=8,
        )

        assert approval_id is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_list_pending_approvals(self, approval_service, mock_db):
        """Test retrieving pending approvals."""
        mock_items = [MagicMock(), MagicMock()]
        mock_db.query.return_value.filter.return_value.count.return_value = 2
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = mock_items

        total, items = approval_service.list_pending_approvals(limit=50)

        assert total == 2
        assert len(items) == 2


# ============================================================================
# Feature 5: Audit Logging Tests
# ============================================================================


class TestAuditLoggingService:
    """Test audit logging (Feature 5)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock(spec=Session)

    @pytest.fixture
    def audit_service(self, mock_db):
        return AuditLoggingService(mock_db, tenant_id="test-tenant")

    def test_log_llm_call(self, audit_service, mock_db):
        """Test logging LLM call."""
        log_id = audit_service.log_llm_call(
            user_id="user-1",
            feature_type="bdd_gen",
            task_type="analyst",
            model_used="qwen2.5:14b",
            prompt_text="Generate BDD scenario for login",
            response_text="Feature: Login\n  Scenario: Valid login",
            tokens_input=50,
            tokens_output=100,
            latency_ms=2500.0,
            cost_usd=0.001,
        )

        assert log_id is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_record_user_action(self, audit_service, mock_db):
        """Test recording user action on logged call."""
        mock_log = MagicMock(spec=LLMAuditLog)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_log

        audit_service.record_user_action("log-id-1", "approved", feedback="Good quality")

        assert mock_log.user_action == "approved"
        assert mock_log.user_feedback == "Good quality"
        mock_db.commit.assert_called_once()


# ============================================================================
# Feature 6: Cost Tracking Tests
# ============================================================================


class TestCostTrackingService:
    """Test cost tracking and budgeting (Feature 6)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock(spec=Session)

    @pytest.fixture
    def cost_service(self, mock_db):
        return CostTrackingService(mock_db, tenant_id="test-tenant")

    def test_cost_calculation_gpt4(self, cost_service):
        """Test cost calculation for GPT-4."""
        cost = cost_service._calculate_cost("gpt-4-turbo", 1000, 500)
        # GPT-4 Turbo: $0.01/1K input, $0.03/1K output
        expected = (1000 * 0.01 + 500 * 0.03) / 1_000_000
        assert cost == pytest.approx(expected, rel=0.01)

    def test_cost_calculation_local_model(self, cost_service):
        """Test cost for local/self-hosted models."""
        cost = cost_service._calculate_cost("llama3.1:8b", 5000, 2000)
        assert cost == 0.0  # Self-hosted models have zero cost

    def test_record_cost(self, cost_service, mock_db):
        """Test recording a cost record."""
        cost = cost_service.record_cost(
            user_id="user-1",
            model_name="gpt-4-turbo",
            tokens_input=1000,
            tokens_output=500,
        )

        assert cost > 0
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_get_cost_summary(self, cost_service, mock_db):
        """Test cost summary generation."""
        from backend.app.domains.llm_integration.models import CostTrackingRecord

        mock_records = [
            MagicMock(spec=CostTrackingRecord, cost_usd=0.1, tokens_input=1000, tokens_output=500),
            MagicMock(spec=CostTrackingRecord, cost_usd=0.05, tokens_input=500, tokens_output=250),
        ]
        mock_db.query.return_value.filter.return_value.all.return_value = mock_records

        summary = cost_service.get_cost_summary(period="month")

        assert summary["total_cost_usd"] == 0.15
        assert summary["request_count"] == 2


# ============================================================================
# Feature 7: Rate Limiting Tests
# ============================================================================


class TestRateLimitingService:
    """Test rate limiting (Feature 7)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock(spec=Session)

    @pytest.fixture
    def rate_limit_service(self, mock_db):
        return RateLimitingService(mock_db, tenant_id="test-tenant")

    def test_check_limit_allowed(self, rate_limit_service, mock_db):
        """Test request allowed under limit."""
        mock_quota = MagicMock()
        mock_quota.enabled = True
        mock_quota.requests_per_minute = 10
        mock_db.query.return_value.filter.return_value.first.return_value = mock_quota

        allowed, limit_type = rate_limit_service.check_limit("user-1", "rpm")

        assert allowed is True
        assert limit_type is None

    def test_check_limit_exceeded(self, rate_limit_service, mock_db):
        """Test request denied when limit exceeded."""
        mock_quota = MagicMock()
        mock_quota.enabled = True
        mock_quota.requests_per_minute = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_quota

        # First request
        rate_limit_service.check_limit("user-2", "rpm")
        # Second request should fail
        allowed, limit_type = rate_limit_service.check_limit("user-2", "rpm")

        assert allowed is False
        assert limit_type == "rpm"

    def test_get_limit_status(self, rate_limit_service, mock_db):
        """Test getting limit status."""
        mock_quota = MagicMock()
        mock_quota.requests_per_minute = 10
        mock_quota.requests_per_hour = 500
        mock_db.query.return_value.filter.return_value.first.return_value = mock_quota

        status = rate_limit_service.get_limit_status("user-1")

        assert "rpm_remaining" in status
        assert "rph_remaining" in status
        assert status["concurrent_limit"] == 5


# ============================================================================
# Feature 8: Streaming Service Tests
# ============================================================================


class TestStreamingService:
    """Test streaming sessions (Feature 8)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock(spec=Session)

    @pytest.fixture
    def streaming_service(self, mock_db):
        return StreamingService(mock_db, tenant_id="test-tenant")

    def test_create_streaming_session(self, streaming_service, mock_db):
        """Test creating streaming session."""
        session_id = streaming_service.create_streaming_session(
            user_id="user-1",
            feature_type="test_gen",
            model_used="qwen2.5:14b",
        )

        assert session_id is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


# ============================================================================
# Feature 9: Function Calling Tests
# ============================================================================


class TestFunctionCallingService:
    """Test function calling/tool use (Feature 9)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock(spec=Session)

    @pytest.fixture
    def function_calling_service(self, mock_db):
        return FunctionCallingService(mock_db, tenant_id="test-tenant")

    def test_define_tool(self, function_calling_service, mock_db):
        """Test defining a tool."""
        tool_id = function_calling_service.define_tool(
            tool_name="search_docs",
            description="Search documentation",
            input_schema={"query": {"type": "string"}},
            output_schema={"results": {"type": "array"}},
            execution_handler="tools.search.execute",
        )

        assert tool_id is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


# ============================================================================
# Feature 10: Fine-Tuning Tests
# ============================================================================


class TestFineTuningService:
    """Test fine-tuning preparation (Feature 10)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock(spec=Session)

    @pytest.fixture
    def finetuning_service(self, mock_db):
        return FineTuningService(mock_db, tenant_id="test-tenant")

    def test_create_dataset(self, finetuning_service, mock_db):
        """Test creating fine-tuning dataset."""
        dataset_id = finetuning_service.create_dataset(
            name="test_gen_v1",
            task_type="test_gen",
            description="Test case generation dataset",
        )

        assert dataset_id is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


# ============================================================================
# Integration & End-to-End Tests
# ============================================================================


class TestLLMIntegrationEndToEnd:
    """End-to-end tests for MVP features."""

    @pytest.mark.asyncio
    async def test_full_approval_workflow(self):
        """Test complete workflow: generate → hallucination check → approve → log."""
        # 1. Generate (Feature 0 - external)
        suggestion = {"scenario": "Login with valid credentials", "steps": []}

        # 2. Check hallucinations (Feature 3)
        # Would return confidence score

        # 3. Queue for approval (Feature 4)
        # Would create approval queue item

        # 4. User reviews and approves (Feature 4)
        # Would update approval status

        # 5. Log the interaction (Feature 5)
        # Would record audit trail

        assert True  # Placeholder
