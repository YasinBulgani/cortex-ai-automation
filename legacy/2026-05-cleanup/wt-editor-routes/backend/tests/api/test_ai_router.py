"""AI router error response contract tests."""

from fastapi.testclient import TestClient

from app.domains.ai import router as ai_router


class TestAiRouterErrors:
    def test_assert_advisor_returns_structured_500_detail(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        monkeypatch,
    ) -> None:
        async def _boom(*args, **kwargs):
            raise RuntimeError("provider timeout")

        monkeypatch.setattr(ai_router, "async_call_llm", _boom)

        response = client.post(
            "/api/v1/ai/assert-advisor",
            json={
                "source_code": "expect(response.status).toBe(200)",
                "file_path": "tests/example.spec.ts",
            },
            headers=auth_headers,
        )

        assert response.status_code == 500
        body = response.json()
        assert isinstance(body["detail"], dict)
        assert body["detail"] == {
            "code": "ai_assert_advisor_failed",
            "message": "AI assertion analizi hatası",
            "error_type": "RuntimeError",
            "details": "provider timeout",
        }

    def test_qa_plan_requires_project_id(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = client.post(
            "/api/v1/ai/qa/plan",
            json={"goal": "Kapsami artir"},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "project_id query parametresi gerekli"

    def test_qa_plan_requires_project_membership(
        self,
        client: TestClient,
        viewer_headers: dict[str, str],
        project_id: str,
    ) -> None:
        response = client.post(
            f"/api/v1/ai/qa/plan?project_id={project_id}",
            json={"goal": "Kapsami artir"},
            headers=viewer_headers,
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Bu projeye erişim yetkiniz yok"

    def test_nl_generate_requires_project_membership(
        self,
        client: TestClient,
        viewer_headers: dict[str, str],
        project_id: str,
    ) -> None:
        response = client.post(
            f"/api/v1/ai/nl-test/generate?project_id={project_id}",
            json={"text": "Login endpoint icin negatif test yaz", "output_format": "api_test"},
            headers=viewer_headers,
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Bu projeye erişim yetkiniz yok"

    def test_nl_generate_rejects_invalid_format(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
    ) -> None:
        response = client.post(
            f"/api/v1/ai/nl-test/generate?project_id={project_id}",
            json={"text": "Login endpoint icin test yaz", "output_format": "invalid"},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "Gecersiz output_format" in response.json()["detail"]

    def test_chat_session_create_requires_project_membership(
        self,
        client: TestClient,
        viewer_headers: dict[str, str],
        project_id: str,
    ) -> None:
        response = client.post(
            "/api/v1/ai/chat/sessions",
            json={"project_id": project_id, "title": "Unauthorized"},
            headers=viewer_headers,
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Bu projeye erişim yetkiniz yok"
