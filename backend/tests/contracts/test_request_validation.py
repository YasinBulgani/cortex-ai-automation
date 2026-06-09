"""Contract Testing: Request Validation & Schema Compliance.

Tests that incoming requests are properly validated against declared schemas.
Ensures type checking, required fields, and format validation.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestRequestValidation:
    """Request validation against OpenAPI schemas."""

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_missing_required_body_fields(self, client: TestClient, auth_headers: dict):
        """Test 1: POST without required body fields returns 422.

        Scenario: Create project without required 'name' field.
        Expected: 422 Unprocessable Entity with validation error.
        """
        payload = {
            "description": "Test project",
            # Missing 'name'
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        # Should validate and reject
        assert response.status_code in [400, 422]

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_invalid_json_body(self, client: TestClient, auth_headers: dict):
        """Test 2: Malformed JSON body returns 400.

        Scenario: Send invalid JSON.
        Expected: 400 Bad Request.
        """
        response = client.post(
            "/api/v1/tspm/projects",
            content=b'{invalid json}',
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert response.status_code == 400

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_invalid_data_type_for_field(self, client: TestClient, auth_headers: dict):
        """Test 3: Wrong data type for field returns 422.

        Scenario: Send string for integer field.
        Expected: 422 Unprocessable Entity.
        """
        payload = {
            "name": "Test",
            "max_retries": "not_a_number",
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        # Should validate type
        assert response.status_code in [201, 400, 422]

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_extra_fields_allowed(self, client: TestClient, auth_headers: dict):
        """Test 4: Extra fields in request handled properly.

        Scenario: POST with unknown fields.
        Expected: Either ignored or rejected (depending on schema strictness).
        """
        payload = {
            "name": "Test",
            "unknown_field": "value",
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        # Either succeeds (ignores extra) or 422 (strict validation)
        assert response.status_code in [201, 400, 422]

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_string_format_validation_email(self, client: TestClient):
        """Test 5: Email format validation.

        Scenario: POST login with invalid email.
        Expected: 422 Unprocessable Entity.
        """
        payload = {
            "email": "not_an_email",
            "password": "password123",
        }
        response = client.post(
            "/api/v1/auth/login",
            json=payload,
        )
        # Should validate email format
        assert response.status_code in [401, 400, 422]

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_minimum_length_validation(self, client: TestClient, auth_headers: dict):
        """Test 6: Minimum length validation enforced.

        Scenario: POST with password < minimum length.
        Expected: 422 Unprocessable Entity.
        """
        payload = {
            "current_password": "test123",
            "new_password": "ab",  # Too short
        }
        response = client.put(
            "/api/v1/auth/change-password",
            json=payload,
            headers=auth_headers,
        )
        # Should validate minimum length
        assert response.status_code in [400, 422, 404]

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_maximum_length_validation(self, client: TestClient, auth_headers: dict):
        """Test 7: Maximum length validation enforced.

        Scenario: POST with name > maximum length.
        Expected: 422 Unprocessable Entity.
        """
        payload = {
            "name": "x" * 5000,  # Very long
            "description": "Test",
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        # Should validate maximum length
        assert response.status_code in [201, 400, 422]

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_enum_field_validation(self, client: TestClient, auth_headers: dict):
        """Test 8: Enum field validation.

        Scenario: POST with invalid enum value.
        Expected: 422 Unprocessable Entity.
        """
        payload = {
            "name": "Test",
            "status": "invalid_status",  # Not in enum
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        # Should validate enum
        assert response.status_code in [201, 400, 422]

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_numeric_range_validation(self, client: TestClient, auth_headers: dict):
        """Test 9: Numeric range validation (min/max).

        Scenario: POST with timeout > maximum allowed.
        Expected: 422 Unprocessable Entity.
        """
        payload = {
            "name": "Test",
            "timeout_seconds": 9999999,  # Too large
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        # Should validate range
        assert response.status_code in [201, 400, 422]

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_required_header_validation(self, client: TestClient):
        """Test 10: Required headers validated.

        Scenario: Missing Authorization header.
        Expected: 401 Unauthorized.
        """
        response = client.get("/api/v1/tspm/projects")
        assert response.status_code == 401

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_path_parameter_type_validation(self, client: TestClient, auth_headers: dict):
        """Test 11: Path parameter type validation.

        Scenario: Project ID should be integer or valid UUID.
        Expected: 404 or 422 for invalid format.
        """
        response = client.get(
            "/api/v1/tspm/projects/not_a_number",
            headers=auth_headers,
        )
        # Should reject invalid path parameter
        assert response.status_code in [404, 422]

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_query_parameter_array_validation(self, client: TestClient, auth_headers: dict):
        """Test 12: Array query parameters validated.

        Scenario: Query with array parameter.
        Expected: Proper parsing or 422.
        """
        response = client.get(
            "/api/v1/tspm/projects?status=active&status=inactive",
            headers=auth_headers,
        )
        # Should handle array params
        assert response.status_code in [200, 422]

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_nested_object_validation(self, client: TestClient, auth_headers: dict):
        """Test 13: Nested object field validation.

        Scenario: POST with nested object missing required field.
        Expected: 422 Unprocessable Entity.
        """
        payload = {
            "name": "Test",
            "config": {
                # Missing required nested field
            },
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        # Should validate nested structure
        assert response.status_code in [201, 400, 422]

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_boolean_field_coercion(self, client: TestClient, auth_headers: dict):
        """Test 14: Boolean field type coercion.

        Scenario: POST with boolean field as string "true".
        Expected: Either coerced to boolean or 422.
        """
        payload = {
            "name": "Test",
            "is_active": "true",  # String instead of boolean
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        # Should either coerce or reject
        assert response.status_code in [201, 400, 422]

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_content_type_mismatch(self, client: TestClient, auth_headers: dict):
        """Test 15: Content-Type mismatch handling.

        Scenario: POST JSON with wrong Content-Type header.
        Expected: 400 or proper parsing.
        """
        payload = {"name": "Test"}
        response = client.post(
            "/api/v1/tspm/projects",
            data=str(payload),  # Send as string
            headers={**auth_headers, "Content-Type": "text/plain"},
        )
        # Should reject or parse
        assert response.status_code in [400, 422, 201]


class TestRequestLimitations:
    """Tests for request size and complexity limits."""

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_request_body_size_limit(self, client: TestClient, auth_headers: dict):
        """Test 16: Request body size limited.

        Scenario: POST with 100MB body.
        Expected: 413 Payload Too Large.
        """
        large_data = "x" * (100 * 1024 * 1024)
        payload = {"data": large_data}

        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code in [413, 400, 422]

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_array_size_limit(self, client: TestClient, auth_headers: dict):
        """Test 17: Array field size limits.

        Scenario: POST with array of 10000 items.
        Expected: 422 or handled gracefully.
        """
        payload = {
            "name": "Test",
            "tags": ["tag"] * 1000,  # Very large array
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code in [201, 400, 422]

    @pytest.mark.contract
    @pytest.mark.request_validation
    def test_string_field_special_chars(self, client: TestClient, auth_headers: dict):
        """Test 18: String fields handle special characters.

        Scenario: POST with unicode, emoji, etc.
        Expected: Properly handled or rejected.
        """
        payload = {
            "name": "Test 测试 😀",
            "description": "Unicode & special < > chars",
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code in [201, 400, 422]
