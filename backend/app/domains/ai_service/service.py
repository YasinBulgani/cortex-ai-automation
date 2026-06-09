"""AI Service Core Logic - LLM-powered features implementation."""

import time
import json
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from backend.app.core.logger import get_logger
from backend.app.infra.database import get_db

from .llm_orchestrator import LLMOrchestrator
from .rag_service import RAGService
from .validator_service import HallucinationValidator
from .models import LLMCallLog, ApprovalQueue

logger = get_logger(__name__)


class BaseAIService:
    """Base class for all AI services."""

    def __init__(self, db, current_user):
        self.db = db
        self.current_user = current_user
        self.tenant_id = current_user.tenant_id
        self.llm = LLMOrchestrator()
        self.rag = RAGService(db=db, tenant_id=self.tenant_id)
        self.validator = HallucinationValidator()

    async def log_llm_call(
        self,
        feature: str,
        model: str,
        tokens_input: int,
        tokens_output: int,
        confidence_score: float,
        output_text: str = "",
    ):
        """Log LLM call for audit and cost tracking."""
        cost_usd = self.llm.calculate_cost(model, tokens_input, tokens_output)

        call_log = LLMCallLog(
            id=uuid4(),
            tenant_id=self.tenant_id,
            actor_user_id=self.current_user.id,
            event_type="llm_call",
            feature=feature,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=cost_usd,
            confidence_score=confidence_score,
            output_text=output_text[:500],  # truncate for storage
            created_at=datetime.utcnow(),
        )
        self.db.add(call_log)
        self.db.commit()

        return cost_usd


# ============================================================================
# Feature 1: BDD Generator Service
# ============================================================================

class BDDGeneratorService(BaseAIService):
    """Generate BDD test cases from user stories."""

    async def generate(
        self,
        story: str,
        project_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate BDD test cases."""
        start_time = time.time()

        # Retrieve RAG context (DSL phrases, past test patterns, project specifics)
        rag_context = await self.rag.retrieve(
            query=story,
            source_types=["dsl_phrases", "test_cases", "requirements"],
            top_k=5,
        )

        # Build prompt
        system_prompt = """You are a QA expert. Generate BDD test cases from user stories.
Output ONLY valid Gherkin syntax. Format:
Feature: Feature Name
  Scenario: Scenario name
    Given [precondition]
    When [action]
    Then [expected result]
"""
        user_prompt = f"""Generate BDD test cases for: {story}

Recent patterns from project:
{json.dumps(rag_context, indent=2)}

Generate 3-5 scenarios covering happy path and error cases."""

        # Call LLM
        llm_response = await self.llm.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            task_type="ANALYZE",
            max_tokens=2000,
        )

        tokens_input = len(user_prompt.split()) * 1.3  # rough estimation
        tokens_output = len(llm_response["output"].split()) * 1.3

        # Parse BDD output
        test_cases = self._parse_bdd_output(llm_response["output"])

        # Validate (hallucination check)
        confidence_score = await self.validator.validate_bdd(
            output=llm_response["output"],
            context=rag_context,
        )

        # Log
        await self.log_llm_call(
            feature="bdd_generation",
            model=llm_response["model"],
            tokens_input=int(tokens_input),
            tokens_output=int(tokens_output),
            confidence_score=confidence_score,
            output_text=llm_response["output"],
        )

        execution_time_ms = int((time.time() - start_time) * 1000)

        return {
            "test_cases": test_cases,
            "confidence_score": confidence_score,
            "execution_time_ms": execution_time_ms,
        }

    def _parse_bdd_output(self, text: str) -> List[Dict[str, Any]]:
        """Parse Gherkin text into test case objects."""
        # TODO: Implement proper Gherkin parser
        # For now, return mock structure
        return [
            {
                "scenario_name": "Login success",
                "given": ["user is on login page"],
                "when": ["user enters valid credentials"],
                "then": ["user is logged in", "dashboard is displayed"],
                "priority": "high",
            }
        ]


# ============================================================================
# Feature 2: Test Improver Service
# ============================================================================

class TestImproverService(BaseAIService):
    """Suggest improvements for existing test cases."""

    async def improve(
        self,
        test_case_id: str,
        project_id: str,
    ) -> Dict[str, Any]:
        """Suggest test improvements."""
        # Fetch test case from DB
        test_case = self.db.query("test_management_test_cases").filter_by(id=test_case_id).first()
        if not test_case:
            raise ValueError(f"Test case {test_case_id} not found")

        # Build RAG context
        rag_context = await self.rag.retrieve(
            query=test_case.title,
            source_types=["test_cases", "best_practices"],
            top_k=3,
        )

        # Call LLM
        llm_response = await self.llm.call(
            system_prompt="You are a QA expert. Suggest improvements for test cases.",
            user_prompt=f"""Analyze this test case for improvements:
Title: {test_case.title}
Description: {test_case.description}
Steps: {json.dumps(test_case.steps)}

Recent similar test cases:
{json.dumps(rag_context, indent=2)}

Suggest improvements in JSON format: {{"improvements": [{{"type": "...", "description": "...", "suggestion": "...", "priority": "..."}}]}}""",
            task_type="ANALYZE",
            max_tokens=1500,
        )

        # Parse suggestions
        suggestions = self._parse_suggestions(llm_response["output"])
        quality_score = await self.validator.validate_suggestions(suggestions)

        # Log
        tokens = (len(str(test_case).split()) + len(llm_response["output"].split())) * 1.3
        await self.log_llm_call(
            feature="test_improvement",
            model=llm_response["model"],
            tokens_input=int(tokens * 0.6),
            tokens_output=int(tokens * 0.4),
            confidence_score=quality_score,
        )

        return {
            "suggestions": suggestions,
            "quality_score": quality_score,
        }

    def _parse_suggestions(self, text: str) -> List[Dict[str, Any]]:
        """Parse improvement suggestions."""
        # TODO: Parse JSON from LLM output
        return [
            {
                "type": "clarity",
                "description": "Steps are unclear",
                "suggested_change": "Clarify step descriptions",
                "priority": "high",
            }
        ]


# ============================================================================
# Feature 3: Missing Test Suggester Service
# ============================================================================

class MissingTestSuggesterService(BaseAIService):
    """Analyze coverage and suggest missing tests."""

    async def suggest(
        self,
        project_id: str,
        requirement_ids: Optional[List[str]] = None,
        min_confidence: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Suggest missing test cases."""
        # Get coverage data
        coverage_data = self._get_coverage_data(project_id, requirement_ids)

        # RAG retrieve related test cases
        rag_context = await self.rag.retrieve(
            query="test case coverage patterns",
            source_types=["test_cases", "requirements"],
            top_k=10,
        )

        # Call LLM
        llm_response = await self.llm.call(
            system_prompt="You are a QA test design expert. Analyze coverage gaps and suggest missing test cases.",
            user_prompt=f"""Coverage analysis:
{json.dumps(coverage_data, indent=2)}

Project test patterns:
{json.dumps(rag_context, indent=2)}

For each gap, suggest 1-2 missing test cases in JSON format: {{"suggestions": [...]}}""",
            task_type="ANALYZE",
            max_tokens=2000,
        )

        suggestions = self._parse_missing_suggestions(llm_response["output"], min_confidence)

        # Log
        await self.log_llm_call(
            feature="missing_tests",
            model=llm_response["model"],
            tokens_input=int(len(str(coverage_data).split()) * 1.3),
            tokens_output=int(len(llm_response["output"].split()) * 1.3),
            confidence_score=0.8,  # TODO: Calculate real confidence
        )

        return suggestions

    def _get_coverage_data(self, project_id: str, requirement_ids: Optional[List[str]]) -> Dict:
        """Fetch coverage metrics for project."""
        # TODO: Query coverage data from DB
        return {
            "total_requirements": 50,
            "tested": 35,
            "gap_percentage": 30,
            "untested_requirements": ["REQ-001", "REQ-005", "REQ-010"],
        }

    def _parse_missing_suggestions(self, text: str, min_confidence: float) -> List[Dict]:
        """Parse missing test suggestions."""
        # TODO: Parse from LLM output
        return [
            {
                "scenario_name": "Error handling for invalid input",
                "description": "Cover edge case when user enters invalid format",
                "suggestion_type": "missing_error_path",
                "coverage_impact": 0.15,
                "confidence_score": 0.85,
                "estimated_effort_hours": 2,
            }
        ]


# ============================================================================
# Feature 4: Regression Selector Service
# ============================================================================

class RegressionSelectorService(BaseAIService):
    """Select optimal regression test suite based on code changes."""

    async def select(
        self,
        project_id: str,
        code_changes: Dict[str, Any],
        max_test_count: int = 50,
    ) -> Dict[str, Any]:
        """Select regression suite."""
        # Analyze code impact
        impact_analysis = self._analyze_impact(code_changes)

        # RAG retrieve related tests
        rag_context = await self.rag.retrieve(
            query=f"tests for {' '.join(code_changes.keys())}",
            source_types=["test_cases"],
            top_k=50,
        )

        # Call LLM to select
        llm_response = await self.llm.call(
            system_prompt="You are a test strategist. Select optimal regression suite based on code impact.",
            user_prompt=f"""Code changes impact:
{json.dumps(impact_analysis, indent=2)}

Available tests:
{json.dumps(rag_context[:20], indent=2)}

Select {max_test_count} most relevant tests. Output JSON: {{"selected_test_ids": [...]}}""",
            task_type="FAST",
            max_tokens=1000,
        )

        selected_ids = self._parse_selected_tests(llm_response["output"])
        coverage = len(selected_ids) / len(rag_context) if rag_context else 0

        # Log
        await self.log_llm_call(
            feature="regression_selection",
            model=llm_response["model"],
            tokens_input=int(len(str(impact_analysis).split()) * 1.3),
            tokens_output=int(len(llm_response["output"].split()) * 1.3),
            confidence_score=0.8,
        )

        return {
            "selected_test_ids": selected_ids[:max_test_count],
            "coverage_prediction": min(coverage, 1.0),
            "estimated_duration_minutes": len(selected_ids) * 2,  # rough estimate
        }

    def _analyze_impact(self, code_changes: Dict[str, Any]) -> Dict:
        """Analyze impact of code changes."""
        # TODO: Real impact analysis
        return {
            "affected_files": list(code_changes.keys()),
            "impact_level": "high",
            "affected_modules": ["auth", "test_management"],
        }

    def _parse_selected_tests(self, text: str) -> List[str]:
        """Parse selected test IDs."""
        # TODO: Parse from JSON
        return ["test_001", "test_002", "test_005"]


# ============================================================================
# Feature 5: RCA (Root Cause Analysis) Service
# ============================================================================

class RCAService(BaseAIService):
    """Analyze defects and suggest root causes."""

    async def analyze(
        self,
        defect_id: str,
        error_log: Optional[str],
        reproduction_steps: Optional[str],
    ) -> Dict[str, Any]:
        """Analyze defect and find root causes."""
        # Fetch defect
        defect = self.db.query("sd_defects").filter_by(id=defect_id).first()
        if not defect:
            raise ValueError(f"Defect {defect_id} not found")

        # RAG retrieve similar defects
        rag_context = await self.rag.retrieve(
            query=defect.description,
            source_types=["defects", "code"],
            top_k=5,
        )

        # Call LLM
        llm_response = await self.llm.call(
            system_prompt="You are a debugging expert. Analyze defect description and logs to find root causes.",
            user_prompt=f"""Defect: {defect.description}
Error log: {error_log or 'N/A'}
Reproduction: {reproduction_steps or 'N/A'}

Similar past defects:
{json.dumps(rag_context, indent=2)}

Provide root cause analysis in JSON: {{"root_causes": [{{"description": "...", "likelihood": 0.8, "components": [], "fix": "..."}}]}}""",
            task_type="ANALYZE",
            max_tokens=1500,
        )

        root_causes = self._parse_rca(llm_response["output"])
        similar_defects = self._find_similar_defects(rag_context)
        confidence = await self.validator.validate_rca(root_causes, rag_context)

        # Log
        await self.log_llm_call(
            feature="defect_analysis",
            model=llm_response["model"],
            tokens_input=int((len(defect.description.split()) + len(str(error_log or "").split())) * 1.3),
            tokens_output=int(len(llm_response["output"].split()) * 1.3),
            confidence_score=confidence,
        )

        return {
            "root_causes": root_causes,
            "confidence_score": confidence,
            "similar_defect_ids": similar_defects,
        }

    def _parse_rca(self, text: str) -> List[Dict]:
        """Parse root cause analysis."""
        # TODO: Parse from JSON
        return [
            {
                "description": "Null pointer in auth service",
                "likelihood": 0.85,
                "affected_components": ["auth", "jwt_handler"],
                "suggested_fix": "Add null check before token validation",
            }
        ]

    def _find_similar_defects(self, rag_context: List[Dict]) -> List[str]:
        """Find similar defects from context."""
        # TODO: Extract defect IDs from RAG results
        return ["defect_123", "defect_456"]


# ============================================================================
# Feature 6: Release Notes Generator Service
# ============================================================================

class ReleaseNotesGeneratorService(BaseAIService):
    """Generate release notes from test results and fixes."""

    async def generate(
        self,
        project_id: str,
        version: str,
        fixed_defect_ids: List[str],
        new_features: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate release notes."""
        # Fetch defect details
        defects = self._get_defect_details(fixed_defect_ids)

        # Build content
        llm_response = await self.llm.call(
            system_prompt="You are a technical writer. Create professional release notes.",
            user_prompt=f"""Generate release notes for v{version}

Fixed defects:
{json.dumps(defects, indent=2)}

New features:
{json.dumps(new_features or [], indent=2)}

Format in Markdown with sections: Features, Bug Fixes, Improvements, Known Issues.""",
            task_type="FAST",
            max_tokens=1500,
        )

        content = llm_response["output"]

        # Log
        await self.log_llm_call(
            feature="release_notes",
            model=llm_response["model"],
            tokens_input=int((len(str(defects).split()) + len(str(new_features or []).split())) * 1.3),
            tokens_output=int(len(content.split()) * 1.3),
            confidence_score=0.9,
            output_text=content,
        )

        return {
            "content": content,
            "format": "markdown",
        }

    def _get_defect_details(self, defect_ids: List[str]) -> List[Dict]:
        """Fetch defect details."""
        # TODO: Query defects from DB
        return [
            {
                "id": "DEF-001",
                "title": "Login timeout issue",
                "severity": "high",
            }
        ]


# ============================================================================
# Feature 7: Hallucination Validator Service
# ============================================================================

class HallucinationValidatorService(BaseAIService):
    """Validate LLM outputs for hallucinations."""

    async def validate(
        self,
        output_text: str,
        output_type: str,
        source_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate LLM output."""
        # Run validator
        is_valid, confidence, risks = await self.validator.validate(
            output=output_text,
            output_type=output_type,
            context=source_context,
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(risks)

        # Log
        await self.log_llm_call(
            feature="output_validation",
            model="validator",
            tokens_input=len(output_text.split()),
            tokens_output=0,
            confidence_score=confidence,
        )

        return {
            "is_valid": is_valid,
            "confidence_score": confidence,
            "hallucination_risks": risks,
            "recommendations": recommendations,
        }

    def _generate_recommendations(self, risks: List[Dict]) -> List[str]:
        """Generate recommendations based on risks."""
        if not risks:
            return ["Output looks good!"]

        recs = []
        for risk in risks:
            if risk["risk_type"] == "ungrounded_claim":
                recs.append("Verify output against source materials before using")
            elif risk["risk_type"] == "contradiction":
                recs.append("Review logic for internal inconsistencies")
            elif risk["risk_type"] == "invalid_syntax":
                recs.append("Run syntax checker before executing generated code")

        return recs
