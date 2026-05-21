"""Tests for Artifacts — /api/v1/artifacts endpoints."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.domains.artifacts import router as artifacts_router


class TestArtifactDownload:

    def test_download_nonexistent_artifact_returns_404(
        self, client: TestClient, auth_headers
    ):
        r = client.get(
            "/api/v1/artifacts/00000000-0000-0000-0000-000000000000/download",
            headers=auth_headers,
        )
        assert r.status_code == 404

    def test_download_requires_auth(self, client: TestClient):
        r = client.get("/api/v1/artifacts/fake-id/download")
        assert r.status_code == 401

    def test_download_requires_owner_scope(self, client: TestClient):
        fake_artifact = SimpleNamespace(
            storage_path=__file__,
            mime_type="text/plain",
            job=SimpleNamespace(created_by="owner-user"),
        )

        class _FakeDb:
            def get(self, model, artifact_id):
                return fake_artifact

        def _fake_get_db():
            yield _FakeDb()

        def _fake_user():
            return SimpleNamespace(id="viewer-user", roles=[])

        app = client.app
        app.dependency_overrides[artifacts_router.get_db] = _fake_get_db
        app.dependency_overrides[artifacts_router.get_current_user] = _fake_user
        try:
            response = client.get("/api/v1/artifacts/fake-id/download")
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(artifacts_router.get_db, None)
            app.dependency_overrides.pop(artifacts_router.get_current_user, None)
