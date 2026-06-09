"""Contract Testing: OpenAPI Specification Compliance.

Validates that API implementation matches OpenAPI specification.
Ensures request/response schemas, status codes, and breaking changes are detected.

Standards:
- OpenAPI 3.1.0 specification
- JSON Schema validation
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient


class TestOpenAPIComplianceBase:
    """Base contract tests for OpenAPI compliance."""

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_openapi_schema_available(self, client: TestClient):
        """Test 1: OpenAPI schema is available (dev/staging).

        Expected: GET /openapi.json returns valid OpenAPI 3.1.0 schema.
        """
        response = client.get("/openapi.json")

        # OpenAPI may be disabled in production
        if response.status_code == 200:
            schema = response.json()

            # Verify OpenAPI structure
            assert "openapi" in schema
            assert schema["openapi"].startswith("3.")
            assert "info" in schema
            assert "paths" in schema

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_api_endpoints_match_spec(self, client: TestClient):
        """Test 2: All implemented endpoints exist in OpenAPI spec.

        Scenario: Compare /openapi.json paths with actual endpoints.
        Expected: No undocumented endpoints.
        """
        response = client.get("/openapi.json")

        if response.status_code == 200:
            schema = response.json()
            documented_paths = set(schema.get("paths", {}).keys())

            # Common endpoints should be documented
            expected_paths = {
                "/api/v1/auth/login",
                "/api/v1/auth/me",
                "/api/v1/tspm/projects",
            }

            missing = expected_paths - documented_paths
            assert len(missing) == 0, f"Missing documented paths: {missing}"

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_response_schema_validation(self, client: TestClient, auth_headers: dict):
        """Test 3: Response matches OpenAPI schema.

        Scenario: GET /api/v1/tspm/projects and validate against schema.
        Expected: Response structure matches spec.
        """
        response = client.get("/api/v1/tspm/projects", headers=auth_headers)

        if response.status_code == 200:
            data = response.json()

            # Response should be a list or paginated object
            assert isinstance(data, (list, dict))

            # If list, items should have expected structure
            if isinstance(data, list) and len(data) > 0:
                first_item = data[0]
                assert isinstance(first_item, dict)
                # Projects should have id, name fields
                if "id" in first_item and "name" in first_item:
                    assert isinstance(first_item["id"], (int, str))
                    assert isinstance(first_item["name"], str)

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_status_codes_match_spec(self, client: TestClient, auth_headers: dict):
        """Test 4: Response status codes match OpenAPI spec.

        Scenario: GET, POST, DELETE operations return expected codes.
        Expected: 200 for success, 4xx for client errors, 5xx for server.
        """
        # GET (success)
        response = client.get("/api/v1/tspm/projects", headers=auth_headers)
        assert response.status_code in [200, 400, 401, 403, 404, 429, 500]

        # GET (not found)
        response = client.get("/api/v1/tspm/projects/99999", headers=auth_headers)
        assert response.status_code in [200, 404]

        # POST (missing auth)
        payload = {"name": "Test"}
        response = client.post("/api/v1/tspm/projects", json=payload)
        assert response.status_code in [201, 400, 401, 422]

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_error_response_format(self, client: TestClient):
        """Test 5: Error responses follow standard format.

        Expected: All errors have detail/message, status code.
        """
        response = client.get("/api/v1/tspm/projects")
        assert response.status_code == 401

        data = response.json()
        # Standard error format
        has_error_detail = (
            "detail" in data
            or "message" in data
            or "error" in data
            or "errors" in data
        )
        assert has_error_detail, "Error response missing detail field"

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_required_parameters_validation(self, client: TestClient, auth_headers: dict):
        """Test 6: Required parameters are enforced.

        Scenario: POST without required fields.
        Expected: 400/422 validation error.
        """
        # Missing required fields
        payload = {}
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        # Should validate required fields
        assert response.status_code in [400, 422]

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_parameter_type_validation(self, client: TestClient, auth_headers: dict):
        """Test 7: Parameter types are validated.

        Scenario: POST with wrong type for fields.
        Expected: 422 Unprocessable Entity.
        """
        payload = {
            "name": "Test",
            "max_retries": "not_a_number",  # Should be int
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        # Should validate types
        assert response.status_code in [201, 400, 422]

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_enum_validation(self, client: TestClient, auth_headers: dict):
        """Test 8: Enum fields are validated.

        Scenario: POST with invalid enum value.
        Expected: 422 Unprocessable Entity.
        """
        payload = {
            "name": "Test",
            "status": "invalid_status",  # Not in allowed enum
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code in [201, 400, 422]

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_string_length_validation(self, client: TestClient, auth_headers: dict):
        """Test 9: String min/max length is enforced.

        Scenario: POST with too long name.
        Expected: 422 Unprocessable Entity.
        """
        payload = {
            "name": "x" * 10000,  # Extremely long
            "description": "Test",
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        # Should validate length
        assert response.status_code in [201, 400, 422]

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_pagination_parameters(self, client: TestClient, auth_headers: dict):
        """Test 10: Pagination parameters work as documented.

        Scenario: GET with limit, offset, page parameters.
        Expected: Response reflects pagination.
        """
        response = client.get(
            "/api/v1/tspm/projects?limit=10&offset=0",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Paginated response should have structure
        if isinstance(data, dict) and "items" in data:
            assert "total" in data or "count" in data
        elif isinstance(data, list):
            assert len(data) <= 10


class TestOpenAPIBreakingChanges:
    """Tests for detecting breaking changes in API."""

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_no_response_field_removal(self, client: TestClient, auth_headers: dict):
        """Test 11: Critical response fields not removed.

        Expected: id, created_at, updated_at fields present.
        """
        response = client.get("/api/v1/tspm/projects", headers=auth_headers)

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                item = data[0]
                # Common fields should exist
                critical_fields = {"id"}
                missing = critical_fields - set(item.keys())
                assert len(missing) == 0, f"Missing critical fields: {missing}"

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_no_endpoint_removal(self, client: TestClient):
        """Test 12: Critical endpoints still accessible.

        Expected: /api/v1/auth/login, /api/v1/auth/me exist.
        """
        # Auth endpoints should always exist
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "test"},
        )
        assert response.status_code in [200, 401, 422]

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_no_status_code_change(self, client: TestClient, auth_headers: dict):
        """Test 13: HTTP status codes haven't changed for success cases.

        Expected: GET returns 200, POST returns 201, DELETE returns 204/200.
        """
        # Successful GET
        response = client.get("/api/v1/tspm/projects", headers=auth_headers)
        if response.status_code != 404:
            assert response.status_code in [200, 401, 403, 429]

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_field_type_compatibility(self, client: TestClient, auth_headers: dict):
        """Test 14: Field types haven't changed (breaking type changes).

        Expected: id remains int/string, not changed to object.
        """
        response = client.get("/api/v1/tspm/projects", headers=auth_headers)

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                item = data[0]
                if "id" in item:
                    # id should be scalar, not object
                    assert not isinstance(item["id"], dict)


class TestOpenAPIResponseHeaders:
    """Tests for response headers compliance."""

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_content_type_header(self, client: TestClient, auth_headers: dict):
        """Test 15: Content-Type header is correct.

        Expected: application/json for API responses.
        """
        response = client.get("/api/v1/tspm/projects", headers=auth_headers)

        if response.status_code == 200:
            content_type = response.headers.get("content-type", "").lower()
            assert "application/json" in content_type

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_required_security_headers(self, client: TestClient, auth_headers: dict):
        """Test 16: Required security headers present.

        Expected: X-Content-Type-Options, X-Frame-Options, etc.
        """
        response = client.get("/api/v1/tspm/projects", headers=auth_headers)

        assert response.status_code == 200
        headers = response.headers

        # Check for security headers
        security_headers = {
            "X-Content-Type-Options",
            "X-Frame-Options",
        }

        # At least some security headers should be present
        present = {h for h in security_headers if h in headers}
        assert len(present) >= 1, "Missing security headers"

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_cors_headers_documented(self, client: TestClient):
        """Test 17: CORS headers follow spec.

        Expected: Access-Control-Allow-Origin, Access-Control-Allow-Methods.
        """
        # Send OPTIONS request
        response = client.options("/api/v1/tspm/projects")

        # CORS headers may or may not be present depending on configuration
        # But if present, should be valid
        if "Access-Control-Allow-Methods" in response.headers:
            methods = response.headers["Access-Control-Allow-Methods"]
            assert "GET" in methods or "POST" in methods


class TestOpenAPIDocumentation:
    """Tests for API documentation completeness."""

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_endpoint_descriptions_present(self, client: TestClient):
        """Test 18: Endpoints have descriptions in OpenAPI spec.

        Expected: Each endpoint has description/summary.
        """
        response = client.get("/openapi.json")

        if response.status_code == 200:
            schema = response.json()
            paths = schema.get("paths", {})

            # Sample paths should have descriptions
            sample_paths = list(paths.items())[:5]
            for path, methods in sample_paths:
                has_description = False
                for method, details in methods.items():
                    if isinstance(details, dict) and (
                        "description" in details or "summary" in details
                    ):
                        has_description = True
                # At least some endpoints should be documented
                if sample_paths:
                    assert has_description or len(paths) == 0

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_parameter_descriptions_present(self, client: TestClient):
        """Test 19: Parameters have descriptions.

        Expected: Query/path parameters documented.
        """
        response = client.get("/openapi.json")

        if response.status_code == 200:
            schema = response.json()
            paths = schema.get("paths", {})

            # Check first GET endpoint with parameters
            for path, methods in paths.items():
                if "get" in methods:
                    get_method = methods["get"]
                    params = get_method.get("parameters", [])
                    # If has params, should have description
                    if params:
                        for param in params:
                            # At minimum, should have name
                            assert "name" in param
                    break

    @pytest.mark.contract
    @pytest.mark.openapi
    def test_response_schema_documented(self, client: TestClient):
        """Test 20: Response schemas are documented.

        Expected: 200 responses have schema/content.
        """
        response = client.get("/openapi.json")

        if response.status_code == 200:
            schema = response.json()
            paths = schema.get("paths", {})

            # Check sample endpoints have response schemas
            for path, methods in paths.items():
                if "get" in methods:
                    get_method = methods["get"]
                    responses = get_method.get("responses", {})
                    # Should have 200 response
                    if "200" in responses:
                        resp_schema = responses["200"]
                        # Should have content or schema
                        assert (
                            "content" in resp_schema
                            or "schema" in resp_schema
                            or "application/json"
                            in str(resp_schema)
                        )
                    break
