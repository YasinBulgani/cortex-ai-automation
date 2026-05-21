"""OpenAPI schema validation tests."""
from fastapi.testclient import TestClient


class TestOpenAPI:

    def test_openapi_json_available(self, client: TestClient):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert "openapi" in schema
        assert schema["info"]["title"] == "TestwrightAI Platform API"

    def test_openapi_has_security_scheme(self, client: TestClient):
        schema = client.get("/openapi.json").json()
        assert "BearerAuth" in schema.get("components", {}).get("securitySchemes", {})

    def test_openapi_has_tags(self, client: TestClient):
        schema = client.get("/openapi.json").json()
        tag_names = [t["name"] for t in schema.get("tags", [])]
        for expected in ["auth", "tspm", "ai", "agents", "coverup", "cicd", "n8n", "playwright-mcp"]:
            assert expected in tag_names, f"Tag '{expected}' missing from OpenAPI schema"

    def test_all_tags_have_descriptions(self, client: TestClient):
        schema = client.get("/openapi.json").json()
        for tag in schema.get("tags", []):
            assert tag.get("description"), f"Tag '{tag['name']}' description'i bos"

    def test_openapi_has_tag_groups(self, client: TestClient):
        schema = client.get("/openapi.json").json()
        assert "x-tagGroups" in schema
        assert len(schema["x-tagGroups"]) >= 3

    def test_docs_endpoint(self, client: TestClient):
        r = client.get("/docs")
        assert r.status_code == 200

    def test_redoc_endpoint(self, client: TestClient):
        r = client.get("/redoc")
        assert r.status_code == 200

    def test_openapi_has_servers(self, client: TestClient):
        schema = client.get("/openapi.json").json()
        servers = schema.get("servers", [])
        assert len(servers) >= 1

    def test_openapi_paths_exist(self, client: TestClient):
        schema = client.get("/openapi.json").json()
        paths = schema.get("paths", {})
        # Check some key paths exist
        assert any("/auth/" in p for p in paths), "Auth paths missing"
        assert any("/coverup/" in p for p in paths), "CoverUp paths missing"
        assert any("/cicd/" in p for p in paths), "CI/CD paths missing"
        assert any("/n8n/" in p for p in paths), "n8n paths missing"

    def test_health_endpoint_has_response_example(self, client: TestClient):
        schema = client.get("/openapi.json").json()
        health = schema["paths"]["/health"]["get"]
        example = (
            health["responses"]["200"]["content"]["application/json"]["example"]
        )
        assert example["status"] == "ok"
        assert example["service"] == "bgts-backend"

    def test_ready_endpoint_has_response_examples(self, client: TestClient):
        schema = client.get("/openapi.json").json()
        ready = schema["paths"]["/ready"]["get"]
        example = ready["responses"]["200"]["content"]["application/json"]["example"]
        assert example["ready"] is True
        assert "checks" in example
        assert "503" in ready["responses"]

    def test_login_endpoint_has_response_examples(self, client: TestClient):
        schema = client.get("/openapi.json").json()
        login = schema["paths"]["/api/v1/auth/login"]["post"]
        example = login["responses"]["200"]["content"]["application/json"]["example"]
        assert "access_token" in example
        assert "refresh_token" in example
        assert login["responses"]["401"]["description"]

    def test_tspm_create_project_has_response_examples(self, client: TestClient):
        schema = client.get("/openapi.json").json()
        create_project = schema["paths"]["/api/v1/tspm/projects"]["post"]
        example = create_project["responses"]["201"]["content"]["application/json"]["example"]
        assert example["name"]
        assert example["archived"] is False

    def test_ai_chat_message_has_response_examples(self, client: TestClient):
        schema = client.get("/openapi.json").json()
        send_message = schema["paths"]["/api/v1/ai/chat/sessions/{session_id}/messages"]["post"]
        example = send_message["responses"]["200"]["content"]["application/json"]["example"]
        assert "user_message" in example
        assert "assistant_message" in example
