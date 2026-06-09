"""Integration tests for AI Service endpoints - full flow E2E."""

import pytest
import json
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def ai_client(client, auth_headers):
    """Client with auth headers for AI endpoints."""
    return client, auth_headers


class TestBDDGeneration:
    """Test BDD generation endpoint."""

    def test_generate_bdd_success(self, ai_client):
        """Generate valid BDD test cases from story."""
        client, headers = ai_client

        response = client.post(
            "/api/v1/ai-service/generate-bdd",
            json={
                "story": "As a user, I want to login with email and password",
                "project_id": "test-project-001",
                "context": {"app_type": "web"},
            },
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert len(data["test_cases"]) > 0
        assert "confidence_score" in data
        assert data["confidence_score"] >= 0.7

        # Verify test case structure
        test_case = data["test_cases"][0]
        assert "scenario_name" in test_case
        assert "given" in test_case
        assert "when" in test_case
        assert "then" in test_case

    def test_generate_bdd_invalid_story(self, ai_client):
        """Handle invalid story input."""
        client, headers = ai_client

        response = client.post(
            "/api/v1/ai-service/generate-bdd",
            json={
                "story": "",  # Empty story
                "project_id": "test-project-001",
            },
            headers=headers,
        )

        assert response.status_code == 422  # Validation error


class TestTestImprovement:
    """Test improvement suggestions."""

    def test_improve_test_success(self, ai_client):
        """Get improvement suggestions for test case."""
        client, headers = ai_client

        response = client.post(
            "/api/v1/ai-service/improve-test",
            json={
                "test_case_id": "test-case-001",
                "project_id": "test-project-001",
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "suggestions" in data
        assert "quality_score" in data
        assert 0 <= data["quality_score"] <= 1


class TestMissingTestSuggestions:
    """Test missing test detection."""

    def test_suggest_missing_tests(self, ai_client):
        """Suggest missing test cases based on coverage gaps."""
        client, headers = ai_client

        response = client.post(
            "/api/v1/ai-service/suggest-missing-tests",
            json={
                "project_id": "test-project-001",
                "min_confidence": 0.75,
            },
            headers=headers,
        )

        assert response.status_code == 200
        suggestions = response.json()

        # Should be a list
        assert isinstance(suggestions, list)

        # Each suggestion should have required fields
        for suggestion in suggestions[:3]:  # Check first 3
            assert "scenario_name" in suggestion
            assert "confidence_score" in suggestion
            assert 0 <= suggestion["confidence_score"] <= 1


class TestRegressionSelection:
    """Test regression suite selection."""

    def test_select_regression_suite(self, ai_client):
        """Select regression tests based on code changes."""
        client, headers = ai_client

        response = client.post(
            "/api/v1/ai-service/select-regression-suite",
            json={
                "project_id": "test-project-001",
                "code_changes": {
                    "auth/login.py": ["login_handler", "verify_token"],
                    "auth/mfa.py": ["enable_mfa"],
                },
                "max_test_count": 50,
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "selected_test_ids" in data
        assert isinstance(data["selected_test_ids"], list)
        assert "coverage_prediction" in data
        assert 0 <= data["coverage_prediction"] <= 1


class TestDefectAnalysis:
    """Test defect RCA analysis."""

    def test_analyze_defect(self, ai_client):
        """Analyze defect and suggest root cause."""
        client, headers = ai_client

        response = client.post(
            "/api/v1/ai-service/analyze-defect",
            json={
                "defect_id": "defect-001",
                "error_log": "TypeError: NoneType object is not subscriptable at auth/mfa.py:42",
                "reproduction_steps": "1. Enable MFA\n2. Attempt login\n3. Get error",
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "root_causes" in data
        assert "confidence_score" in data
        assert len(data["root_causes"]) > 0

        # Check root cause structure
        rca = data["root_causes"][0]
        assert "description" in rca
        assert "likelihood" in rca


class TestReleaseNotes:
    """Test release notes generation."""

    def test_generate_release_notes(self, ai_client):
        """Generate release notes from test results and fixes."""
        client, headers = ai_client

        response = client.post(
            "/api/v1/ai-service/generate-release-notes",
            json={
                "project_id": "test-project-001",
                "version": "1.2.0",
                "fixed_defect_ids": ["def-001", "def-002"],
                "new_features": [
                    {"name": "MFA Support", "description": "Two-factor authentication"},
                    {"name": "API Rate Limiting", "description": "Protection against abuse"},
                ],
            },
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "content" in data
        assert data["format"] in ["markdown", "html", "text"]
        assert len(data["content"]) > 0


class TestHallucinationValidation:
    """Test hallucination detection."""

    def test_validate_valid_output(self, ai_client):
        """Validate correct output."""
        client, headers = ai_client

        response = client.post(
            "/api/v1/ai-service/validate-output",
            json={
                "output_text": "Feature: Login\n  Scenario: Valid login\n    Given user on page\n    When user enters password\n    Then user logged in",
                "output_type": "bdd",
                "source_context": "Login feature with email and password",
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data
        assert "confidence_score" in data
        assert isinstance(data["hallucination_risks"], list)

    def test_validate_invalid_output(self, ai_client):
        """Detect hallucinations in output."""
        client, headers = ai_client

        response = client.post(
            "/api/v1/ai-service/validate-output",
            json={
                "output_text": "This is not BDD format at all",
                "output_type": "bdd",
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Invalid output should have low confidence or risks
        assert data["confidence_score"] < 0.7 or len(data["hallucination_risks"]) > 0


class TestAIServiceAuth:
    """Test authentication and authorization."""

    def test_ai_service_requires_auth(self, client):
        """AI endpoints require authentication."""
        response = client.post(
            "/api/v1/ai-service/generate-bdd",
            json={
                "story": "Test story",
                "project_id": "test-project-001",
            },
        )

        assert response.status_code == 401

    def test_ai_service_requires_permission(self, client, auth_headers_no_ai):
        """AI endpoints require ai.generate permission."""
        response = client.post(
            "/api/v1/ai-service/generate-bdd",
            json={
                "story": "Test story",
                "project_id": "test-project-001",
            },
            headers=auth_headers_no_ai,
        )

        assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
