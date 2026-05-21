"""Security: SQL injection, XSS, CRLF, path traversal tests."""

import pytest
from fastapi.testclient import TestClient


class TestSQLInjection:

    def test_project_name_sql_injection(self, client: TestClient, auth_headers):
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": "'; DROP TABLE tspm_projects; --"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        projects = client.get("/api/v1/tspm/projects", headers=auth_headers)
        assert projects.status_code == 200

    def test_scenario_search_sql_injection(self, client: TestClient, auth_headers):
        pid = client.post(
            "/api/v1/tspm/projects", json={"name": "SQLi Test"}, headers=auth_headers
        ).json()["id"]
        r = client.get(
            f"/api/v1/tspm/projects/{pid}/scenarios?q=' OR 1=1 --",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestXSS:

    def test_xss_in_scenario_title(self, client: TestClient, auth_headers):
        """XSS payload'u storage'a yazilmadan sanitize edilir.

        Backend schema `_strip_html` ile HTML tag'lerini kaldirir —
        kaydedilen deger icinde `<script>` / onerror vb. bulunmamali.
        (Defense-in-depth: frontend ayrica output encoding yapar.)
        """
        pid = client.post(
            "/api/v1/tspm/projects", json={"name": "XSS Test"}, headers=auth_headers
        ).json()["id"]
        payload = "<script>alert('xss')</script>"
        r = client.post(
            f"/api/v1/tspm/projects/{pid}/scenarios",
            json={"title": payload},
            headers=auth_headers,
        )
        assert r.status_code == 201
        stored_title = r.json()["title"]
        assert "<script>" not in stored_title
        assert "</script>" not in stored_title

    def test_xss_in_project_description(self, client: TestClient, auth_headers):
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": "XSS Desc", "description": "<img src=x onerror=alert(1)>"},
            headers=auth_headers,
        )
        assert r.status_code == 201


class TestCRLFInjection:

    def test_crlf_in_email(self, client: TestClient):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "test@test.com\r\nX-Injected: true", "password": "x"},
        )
        assert r.status_code in (401, 422)


class TestPathTraversal:

    def test_import_filename_traversal(self, client: TestClient, auth_headers):
        pid = client.post(
            "/api/v1/tspm/projects", json={"name": "Traversal"}, headers=auth_headers
        ).json()["id"]
        r = client.post(
            f"/api/v1/tspm/projects/{pid}/imports",
            json={"filename": "../../etc/passwd", "raw_text": "test"},
            headers=auth_headers,
        )
        assert r.status_code in (201, 400, 422)


class TestNullByteInjection:

    def test_null_byte_in_title(self, client: TestClient, auth_headers):
        pid = client.post(
            "/api/v1/tspm/projects", json={"name": "Null"}, headers=auth_headers
        ).json()["id"]
        r = client.post(
            f"/api/v1/tspm/projects/{pid}/scenarios",
            json={"title": "test\x00injection"},
            headers=auth_headers,
        )
        assert r.status_code in (201, 422)


class TestLargePayload:

    def test_oversized_json_body(self, client: TestClient, auth_headers):
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": "X" * 100_000, "description": "Y" * 100_000},
            headers=auth_headers,
        )
        assert r.status_code in (201, 413, 422, 500)


class TestUnicodeEmoji:

    def test_turkish_characters_and_emoji(self, client: TestClient, auth_headers):
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": "İŞ AKIŞI Öğrenci Çalışma 🚀"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert "İŞ" in r.json()["name"]
