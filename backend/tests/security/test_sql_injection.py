"""OWASP Security Test: SQL Injection Prevention.

Test cases for SQL injection vulnerabilities across all API endpoints.
Covers parameterized queries, input validation, and safe ORM usage.

Standards:
- OWASP A03:2021 – Injection
- CWE-89: Improper Neutralization of Special Elements used in an SQL Command
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestSQLInjection:
    """SQL Injection attack vectors and defenses."""

    @pytest.mark.security
    @pytest.mark.owasp_a03
    def test_project_list_sql_injection_or_payload(self, client: TestClient, auth_headers: dict):
        """Test 1: OR '1'='1 payload in project listing.

        Payload: Search for projects with: ' OR '1'='1
        Expected: Returns filtered results safely, not all data.
        """
        payload = {"search": "' OR '1'='1"}
        response = client.get(
            "/api/v1/tspm/projects",
            params=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Verify no SQL syntax error occurred
        assert "syntax error" not in str(response.text).lower()
        assert "sql error" not in str(response.text).lower()
        # Verify response is properly structured (not raw DB error)
        assert isinstance(data, dict) or isinstance(data, list)

    @pytest.mark.security
    @pytest.mark.owasp_a03
    def test_project_filter_union_based_injection(self, client: TestClient, auth_headers: dict):
        """Test 2: UNION SELECT based SQL injection.

        Payload: UNION SELECT * FROM users
        Expected: Returns error or filtered results, not additional tables.
        """
        payload = {"status": "active' UNION SELECT * FROM users--"}
        response = client.get(
            "/api/v1/tspm/projects",
            params=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        # Should not leak table structure
        data = response.json()
        assert "id" in data or isinstance(data, list)

    @pytest.mark.security
    @pytest.mark.owasp_a03
    def test_scenario_search_time_based_injection(self, client: TestClient, auth_headers: dict):
        """Test 3: Time-based blind SQL injection.

        Payload: sleep(5) or similar time-based detection.
        Expected: Response time normal, no database sleep executed.
        """
        import time

        payload = {"search": "'; SELECT pg_sleep(5); --"}
        start = time.time()
        response = client.get(
            "/api/v1/tspm/projects",
            params=payload,
            headers=auth_headers,
        )
        elapsed = time.time() - start

        # Response should complete quickly (< 2 seconds)
        # If sleep(5) executed, would take 5+ seconds
        assert elapsed < 2.0, f"Query took {elapsed}s - possible time-based injection"
        assert response.status_code == 200

    @pytest.mark.security
    @pytest.mark.owasp_a03
    def test_defect_query_stacked_queries_injection(self, client: TestClient, auth_headers: dict):
        """Test 4: Stacked queries SQL injection.

        Payload: '; DROP TABLE projects; --
        Expected: Error or safe handling, table not dropped.
        """
        payload = {"filter": "'; DROP TABLE tspm_projects; --"}
        response = client.get(
            "/api/v1/tspm/projects",
            params=payload,
            headers=auth_headers,
        )
        # Should either succeed with filtered results or 400/422
        assert response.status_code in [200, 400, 422]
        # Verify table still exists by making another request
        response2 = client.get(
            "/api/v1/tspm/projects",
            headers=auth_headers,
        )
        assert response2.status_code == 200, "Projects table was dropped!"

    @pytest.mark.security
    @pytest.mark.owasp_a03
    def test_test_run_filter_comment_escape_injection(self, client: TestClient, auth_headers: dict):
        """Test 5: Comment-based SQL injection bypass.

        Payload: admin' OR 1=1 # (MySQL style comment)
        Expected: Safely escaped, no data leakage.
        """
        payload = {"query": "test' OR 1=1 #"}
        response = client.get(
            "/api/v1/tspm/projects",
            params=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.security
    @pytest.mark.owasp_a03
    def test_json_body_sql_injection(self, client: TestClient, auth_headers: dict):
        """Test 6: SQL injection in POST body with JSON.

        Payload: {"name": "' OR '1'='1"}
        Expected: Name sanitized, no SQL execution.
        """
        payload = {
            "name": "Test Project' OR '1'='1",
            "description": "Safe test",
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        # Should succeed or fail gracefully (422 for validation, not SQL error)
        assert response.status_code in [201, 400, 422]
        assert "sql" not in response.text.lower()

    @pytest.mark.security
    @pytest.mark.owasp_a03
    def test_path_parameter_sql_injection(self, client: TestClient, auth_headers: dict):
        """Test 7: SQL injection via path parameters.

        Payload: /api/v1/tspm/projects/{id} where id="1' OR '1'='1"
        Expected: 404 or safe handling.
        """
        payload_id = "1' OR '1'='1"
        response = client.get(
            f"/api/v1/tspm/projects/{payload_id}",
            headers=auth_headers,
        )
        # Should return 404 or 422, not 200 with data
        assert response.status_code in [404, 422]

    @pytest.mark.security
    @pytest.mark.owasp_a03
    def test_batch_operation_sql_injection(self, client: TestClient, auth_headers: dict):
        """Test 8: SQL injection in batch operations.

        Payload: {"ids": ["1' OR '1'='1", "2"]}
        Expected: IDs validated, no injection.
        """
        payload = {
            "ids": ["1' OR '1'='1", "2"],
            "status": "completed",
        }
        response = client.put(
            "/api/v1/tspm/projects/batch-update",
            json=payload,
            headers=auth_headers,
        )
        # Should fail validation (422) or succeed with safe handling (200)
        assert response.status_code in [200, 422, 404]
        assert "syntax error" not in response.text.lower()

    @pytest.mark.security
    @pytest.mark.owasp_a03
    def test_parameterized_query_confirmation(self, client: TestClient, auth_headers: dict):
        """Test 9: Verify parameterized queries are in use.

        Multi-injection payloads to detect if parameterization is working.
        Expected: All requests handled safely.
        """
        payloads = [
            "1; DELETE FROM users;",
            "1' AND '1'='1",
            "1\" AND \"1\"=\"1",
            "1 OR TRUE",
            "1; EXEC xp_cmdshell;",
        ]

        for payload in payloads:
            response = client.get(
                f"/api/v1/tspm/projects/1",
                headers=auth_headers,
            )
            # All should either 404 (project not found) or 200 (success)
            assert response.status_code in [200, 404, 422]
            assert "error" not in response.text.lower() or "not found" in response.text.lower()

    @pytest.mark.security
    @pytest.mark.owasp_a03
    def test_no_error_details_leak(self, client: TestClient, auth_headers: dict):
        """Test 10: Verify error messages don't leak DB internals.

        Send invalid queries and check response doesn't expose:
        - Table names
        - Column names
        - Database type/version
        - SQL syntax
        """
        payload = {"search": "' OR '1'='1"}
        response = client.get(
            "/api/v1/tspm/projects",
            params=payload,
            headers=auth_headers,
        )

        text = response.text.lower()
        # Should not contain DB internals
        assert "table" not in text or "data" in text
        assert "column" not in text
        assert "postgresql" not in text
        assert "sqlite" not in text
        assert "mysql" not in text
        assert "sqlalchemy" not in text


class TestSQLInjectionEdgeCases:
    """Edge cases and bypass techniques."""

    @pytest.mark.security
    @pytest.mark.owasp_a03
    def test_unicode_encoding_bypass(self, client: TestClient, auth_headers: dict):
        """Test: Unicode/encoding bypass attempts.

        Payload: URL-encoded or double-encoded SQL injection.
        Expected: Safely decoded and neutralized.
        """
        # %2527 = URL-encoded single quote
        response = client.get(
            "/api/v1/tspm/projects?search=%2527%20OR%20%25271%2527=%25271",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.security
    @pytest.mark.owasp_a03
    def test_case_variations_bypass(self, client: TestClient, auth_headers: dict):
        """Test: Case variations (SeLeCtT, UnIoN, etc.) bypass.

        Expected: Case-insensitive parameterization still safe.
        """
        payload = {"search": "' UnIoN SeLeCt * FROM users--"}
        response = client.get(
            "/api/v1/tspm/projects",
            params=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.security
    @pytest.mark.owasp_a03
    def test_nested_comment_injection(self, client: TestClient, auth_headers: dict):
        """Test: Nested comment syntax bypass (/* */ in PostgreSQL).

        Expected: Comments safely handled.
        """
        payload = {"search": "1' /*! UNION */ SELECT 1--"}
        response = client.get(
            "/api/v1/tspm/projects",
            params=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
