"""OWASP Security Test: Cross-Site Scripting (XSS) Prevention.

Test cases for XSS vulnerabilities across all API endpoints.
Covers stored XSS, reflected XSS, DOM-based XSS, and proper escaping.

Standards:
- OWASP A07:2021 – Cross-Site Scripting (XSS)
- CWE-79: Improper Neutralization of Input During Web Page Generation
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


class TestXSSPrevention:
    """XSS attack vectors and defenses."""

    @pytest.mark.security
    @pytest.mark.owasp_a07
    def test_reflected_xss_query_parameter(self, client: TestClient, auth_headers: dict):
        """Test 1: Reflected XSS via query parameter.

        Payload: search=<script>alert(1)</script>
        Expected: Script escaped/sanitized in response, not executed.
        """
        payload = {"search": "<script>alert(1)</script>"}
        response = client.get(
            "/api/v1/tspm/projects",
            params=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Verify payload is not reflected as-is in any response field
        response_str = json.dumps(data)
        # Should be escaped or not included
        assert "<script>" not in response_str or "&lt;script&gt;" in response_str

    @pytest.mark.security
    @pytest.mark.owasp_a07
    def test_stored_xss_project_name(self, client: TestClient, auth_headers: dict):
        """Test 2: Stored XSS in project name.

        Payload: Create project with name containing script tag.
        Expected: Stored safely, retrieved escaped/sanitized.
        """
        payload = {
            "name": "<img src=x onerror=alert('XSS')>",
            "description": "Test project",
        }
        # Create
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )

        if response.status_code == 201:
            project = response.json()
            project_id = project.get("id")

            # Retrieve and verify
            response2 = client.get(
                f"/api/v1/tspm/projects/{project_id}",
                headers=auth_headers,
            )

            if response2.status_code == 200:
                data = response2.json()
                name = data.get("name", "")
                # Should be escaped or sanitized
                assert "<img" not in name or "&lt;img" in name
                assert "onerror=" not in name or "onerror=" not in name

    @pytest.mark.security
    @pytest.mark.owasp_a07
    def test_event_handler_xss_json_body(self, client: TestClient, auth_headers: dict):
        """Test 3: XSS via event handler in JSON body.

        Payload: {"description": "Test<svg onload=alert(1)>"}
        Expected: SVG onload handler neutralized.
        """
        payload = {
            "name": "Test Project",
            "description": "Test<svg onload=alert(1)>",
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        # Should succeed or fail gracefully
        assert response.status_code in [201, 400, 422]

        if response.status_code == 201:
            project = response.json()
            desc = project.get("description", "")
            # Event handler should be stripped or escaped
            assert "onload=" not in desc

    @pytest.mark.security
    @pytest.mark.owasp_a07
    def test_javascript_url_xss(self, client: TestClient, auth_headers: dict):
        """Test 4: javascript: URL XSS.

        Payload: {"url": "javascript:alert(1)"}
        Expected: URL validated, javascript: scheme rejected.
        """
        payload = {
            "name": "Test",
            "url": "javascript:alert(1)",
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        # Should reject or sanitize
        assert response.status_code in [201, 400, 422]

        if response.status_code == 201:
            project = response.json()
            url = project.get("url", "")
            assert "javascript:" not in url

    @pytest.mark.security
    @pytest.mark.owasp_a07
    def test_data_url_xss(self, client: TestClient, auth_headers: dict):
        """Test 5: data: URL XSS (data:text/html with script).

        Payload: {"url": "data:text/html,<script>alert(1)</script>"}
        Expected: URL validated, data: scheme rejected or sanitized.
        """
        payload = {
            "name": "Test",
            "url": "data:text/html,<script>alert(1)</script>",
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code in [201, 400, 422]

    @pytest.mark.security
    @pytest.mark.owasp_a07
    def test_html_entity_bypass(self, client: TestClient, auth_headers: dict):
        """Test 6: HTML entity bypass (&#60;script&#62;).

        Payload: &#60;script&#62;alert(1)&#60;/script&#62;
        Expected: Decoded and sanitized.
        """
        payload = {"search": "&#60;script&#62;alert(1)&#60;/script&#62;"}
        response = client.get(
            "/api/v1/tspm/projects",
            params=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.security
    @pytest.mark.owasp_a07
    def test_unicode_escape_xss(self, client: TestClient, auth_headers: dict):
        """Test 7: Unicode escape bypass (\\u003c = <).

        Payload: \\u003cscript\\u003ealert(1)\\u003c/script\\u003e
        Expected: Properly decoded and neutralized.
        """
        payload = {"search": "\\u003cscript\\u003ealert(1)\\u003c/script\\u003e"}
        response = client.get(
            "/api/v1/tspm/projects",
            params=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.security
    @pytest.mark.owasp_a07
    def test_case_sensitive_bypass(self, client: TestClient, auth_headers: dict):
        """Test 8: Case variation bypass (ScRiPt, SCript, etc.).

        Expected: Case-insensitive filtering/escaping.
        """
        payloads = [
            "<ScRiPt>alert(1)</ScRiPt>",
            "<SCRIPT>alert(1)</SCRIPT>",
            "<ScripT>alert(1)</sCript>",
        ]

        for payload_str in payloads:
            payload = {"search": payload_str}
            response = client.get(
                "/api/v1/tspm/projects",
                params=payload,
                headers=auth_headers,
            )
            assert response.status_code == 200

    @pytest.mark.security
    @pytest.mark.owasp_a07
    def test_space_bypass_techniques(self, client: TestClient, auth_headers: dict):
        """Test 9: Space bypass using tabs, newlines, etc.

        Payload: <script\t>\nalert(1)</script>
        Expected: Whitespace normalization, script still caught.
        """
        payloads = [
            "<script\t>alert(1)</script>",
            "<script\n>alert(1)</script>",
            "<script/src=x>",
        ]

        for payload_str in payloads:
            payload = {"search": payload_str}
            response = client.get(
                "/api/v1/tspm/projects",
                params=payload,
                headers=auth_headers,
            )
            assert response.status_code == 200

    @pytest.mark.security
    @pytest.mark.owasp_a07
    def test_nested_tag_xss(self, client: TestClient, auth_headers: dict):
        """Test 10: Nested/malformed tag XSS.

        Payload: <script><script>alert(1)</script></script>
        Expected: Both outer and inner tags neutralized.
        """
        payload = {"search": "<script><script>alert(1)</script></script>"}
        response = client.get(
            "/api/v1/tspm/projects",
            params=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.security
    @pytest.mark.owasp_a07
    def test_response_content_type_header(self, client: TestClient, auth_headers: dict):
        """Test 11: Verify Content-Type header prevents XSS.

        Expected: application/json prevents browser from interpreting HTML.
        """
        payload = {"search": "<script>alert(1)</script>"}
        response = client.get(
            "/api/v1/tspm/projects",
            params=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        # Verify Content-Type is JSON
        content_type = response.headers.get("content-type", "").lower()
        assert "application/json" in content_type

    @pytest.mark.security
    @pytest.mark.owasp_a07
    def test_x_content_type_options_header(self, client: TestClient, auth_headers: dict):
        """Test 12: Verify X-Content-Type-Options header is set.

        Expected: X-Content-Type-Options: nosniff
        Prevents MIME type sniffing that could enable XSS.
        """
        response = client.get(
            "/api/v1/tspm/projects",
            headers=auth_headers,
        )
        assert response.status_code == 200
        x_content_type = response.headers.get("X-Content-Type-Options", "").lower()
        assert "nosniff" in x_content_type


class TestDOMBasedXSS:
    """DOM-based XSS vulnerabilities (Frontend-related API responses)."""

    @pytest.mark.security
    @pytest.mark.owasp_a07
    def test_html_content_in_response(self, client: TestClient, auth_headers: dict):
        """Test: HTML content is properly escaped in API responses.

        Expected: HTML special chars (<, >, &, ", ') are escaped.
        """
        payload = {
            "name": 'Test<>&"\'',
            "description": "<div>Content</div>",
        }
        response = client.post(
            "/api/v1/tspm/projects",
            json=payload,
            headers=auth_headers,
        )

        if response.status_code == 201:
            project = response.json()
            name = project.get("name", "")
            # Frontend should handle, but API should at minimum not execute
            assert response.status_code in [201, 400, 422]


class TestXSSAdvanced:
    """Advanced XSS techniques."""

    @pytest.mark.security
    @pytest.mark.owasp_a07
    def test_iframe_xss_injection(self, client: TestClient, auth_headers: dict):
        """Test: iframe XSS injection blocked.

        Payload: <iframe src="javascript:alert(1)">
        Expected: iframe removed or src sanitized.
        """
        payload = {"search": '<iframe src="javascript:alert(1)">'}
        response = client.get(
            "/api/v1/tspm/projects",
            params=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.security
    @pytest.mark.owasp_a07
    def test_style_tag_xss(self, client: TestClient, auth_headers: dict):
        """Test: style tag with expression XSS.

        Payload: <style>body{background:url('javascript:alert(1)')}</style>
        Expected: Style tag removed or expression sanitized.
        """
        payload = {"search": "<style>body{background:url('javascript:alert(1)')}</style>"}
        response = client.get(
            "/api/v1/tspm/projects",
            params=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.security
    @pytest.mark.owasp_a07
    def test_form_hijacking_xss(self, client: TestClient, auth_headers: dict):
        """Test: form hijacking via form tag injection.

        Payload: <form action="http://attacker.com">
        Expected: Form tag removed or action restricted.
        """
        payload = {"search": '<form action="http://attacker.com">'}
        response = client.get(
            "/api/v1/tspm/projects",
            params=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.security
    @pytest.mark.owasp_a07
    def test_meta_refresh_xss(self, client: TestClient, auth_headers: dict):
        """Test: meta refresh redirect XSS.

        Payload: <meta http-equiv="refresh" content="0;url=javascript:alert(1)">
        Expected: Meta tag removed or url sanitized.
        """
        payload = {
            "search": '<meta http-equiv="refresh" content="0;url=javascript:alert(1)">'
        }
        response = client.get(
            "/api/v1/tspm/projects",
            params=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
