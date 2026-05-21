"""Integration tests for CI/CD webhook endpoints (/api/v1/cicd/)."""

from __future__ import annotations

import uuid

import httpx
from fastapi.testclient import TestClient
from app.domains.cicd import router as cicd_router


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.get("timeout")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, headers=None):
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={"run_id": "fake-run", "accepted": True, "project_id": (json or {}).get("project_id")},
        )


class TestCicd:
    """CI/CD webhook ingestion and event listing tests."""

    PREFIX = "/api/v1/cicd"

    def test_github_webhook_persists_event(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db_ready: bool,
    ) -> None:
        """Posting a GitHub webhook should make the event visible in /events."""
        if not db_ready:
            return

        repo_name = f"bgts/test-{uuid.uuid4().hex[:8]}"
        payload = {
            "ref": "refs/heads/main",
            "after": "abc123def456",
            "repository": {"full_name": repo_name},
            "sender": {"login": "ci-bot"},
        }

        response = client.post(
            f"{self.PREFIX}/webhook/github",
            json=payload,
            headers={"X-GitHub-Event": "push"},
        )
        assert response.status_code == 200
        event_id = response.json()["event_id"]

        events_response = client.get(
            f"{self.PREFIX}/events?source=github&limit=20",
            headers=auth_headers,
        )
        assert events_response.status_code == 200

        body = events_response.json()
        assert body["total"] >= 1

        event = next((item for item in body["events"] if item["id"] == event_id), None)
        assert event is not None
        assert event["source"] == "github"
        assert event["event_type"] == "push"
        assert event["project_ref"] == repo_name
        assert event["payload_summary"]["ref"] == "refs/heads/main"

    def test_events_source_filter_returns_requested_provider(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db_ready: bool,
    ) -> None:
        """Filtering by source should only return matching CI/CD providers."""
        if not db_ready:
            return

        github_repo = f"bgts/github-{uuid.uuid4().hex[:8]}"
        jenkins_job = f"jenkins-job-{uuid.uuid4().hex[:8]}"

        client.post(
            f"{self.PREFIX}/webhook/github",
            json={"repository": {"full_name": github_repo}, "ref": "refs/heads/main"},
            headers={"X-GitHub-Event": "push"},
        )
        client.post(
            f"{self.PREFIX}/webhook/jenkins",
            json={"name": jenkins_job, "status": "SUCCESS"},
        )

        response = client.get(
            f"{self.PREFIX}/events?source=jenkins&limit=20",
            headers=auth_headers,
        )
        assert response.status_code == 200

        body = response.json()
        assert body["total"] >= 1
        assert all(event["source"] == "jenkins" for event in body["events"])
        assert any(event["project_ref"] == jenkins_job for event in body["events"])

    def test_github_webhook_invalid_signature(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setattr(cicd_router, "GITHUB_SECRET", "test-secret")
        response = client.post(
            f"{self.PREFIX}/webhook/github",
            json={"repository": {"full_name": "bgts/repo"}},
            headers={
                "X-GitHub-Event": "push",
                "X-Hub-Signature-256": "sha256=invalid",
            },
        )
        assert response.status_code == 401

    def test_github_webhook_missing_signature(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setattr(cicd_router, "GITHUB_SECRET", "test-secret")
        response = client.post(
            f"{self.PREFIX}/webhook/github",
            json={"repository": {"full_name": "bgts/repo"}},
            headers={"X-GitHub-Event": "push"},
        )
        assert response.status_code == 401

    def test_github_webhook_secret_required_mode(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setattr(cicd_router, "GITHUB_SECRET", "")
        monkeypatch.setenv("CICD_REQUIRE_WEBHOOK_SECRETS", "1")
        response = client.post(
            f"{self.PREFIX}/webhook/github",
            json={"repository": {"full_name": "bgts/repo"}},
            headers={"X-GitHub-Event": "push"},
        )
        assert response.status_code == 503

    def test_gitlab_webhook_invalid_token(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setattr(cicd_router, "GITLAB_TOKEN", "expected-token")
        response = client.post(
            f"{self.PREFIX}/webhook/gitlab",
            json={"object_kind": "pipeline"},
            headers={"X-Gitlab-Token": "wrong-token", "X-Gitlab-Event": "Pipeline Hook"},
        )
        assert response.status_code == 401

    def test_gitlab_webhook_secret_required_mode(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setattr(cicd_router, "GITLAB_TOKEN", "")
        monkeypatch.setenv("CICD_REQUIRE_WEBHOOK_SECRETS", "1")
        response = client.post(
            f"{self.PREFIX}/webhook/gitlab",
            json={"object_kind": "pipeline"},
            headers={"X-Gitlab-Event": "Pipeline Hook"},
        )
        assert response.status_code == 503

    def test_jenkins_webhook_invalid_token(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setattr(cicd_router, "JENKINS_TOKEN", "expected-token")
        response = client.post(
            f"{self.PREFIX}/webhook/jenkins",
            json={"name": "job-1"},
            headers={"X-Jenkins-Token": "wrong-token"},
        )
        assert response.status_code == 401

    def test_jenkins_webhook_secret_required_mode(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setattr(cicd_router, "JENKINS_TOKEN", "")
        monkeypatch.setenv("CICD_REQUIRE_WEBHOOK_SECRETS", "1")
        response = client.post(
            f"{self.PREFIX}/webhook/jenkins",
            json={"name": "job-1"},
        )
        assert response.status_code == 503

    def test_list_events_requires_auth(self, client: TestClient, db_ready: bool) -> None:
        if not db_ready:
            return

        response = client.get(f"{self.PREFIX}/events?limit=5")
        assert response.status_code == 401

    def test_quality_gate_requires_auth(self, client: TestClient) -> None:
        response = client.post(
            f"{self.PREFIX}/quality-gate/evaluate",
            json={
                "execution_summary": {"passed": 1, "failed": 0, "total": 1, "duration_s": 1},
                "gate_config": {},
            },
        )
        assert response.status_code == 401

    def test_impact_analysis_requires_auth(self, client: TestClient) -> None:
        response = client.post(
            f"{self.PREFIX}/impact-analysis/test-project",
            json={"changed_files": ["app/domains/auth/router.py"]},
        )
        assert response.status_code == 401

    def test_impact_analysis_requires_project_membership(
        self,
        client: TestClient,
        viewer_headers: dict[str, str],
        project_id: str,
    ) -> None:
        response = client.post(
            f"{self.PREFIX}/impact-analysis/{project_id}",
            json={"changed_files": ["app/domains/auth/router.py"]},
            headers=viewer_headers,
        )
        assert response.status_code == 403

    def test_trigger_requires_auth_when_ci_token_not_set(
        self,
        client: TestClient,
        monkeypatch,
        project_id: str,
    ) -> None:
        monkeypatch.setattr(cicd_router, "CI_TOKEN", "")
        monkeypatch.delenv("CICD_REQUIRE_TRIGGER_TOKEN", raising=False)
        response = client.post(
            f"{self.PREFIX}/trigger/{project_id}",
            json={"scenario_ids": []},
        )
        assert response.status_code == 401

    def test_trigger_rejects_non_member_without_ci_token(
        self,
        client: TestClient,
        monkeypatch,
        viewer_headers: dict[str, str],
        project_id: str,
    ) -> None:
        monkeypatch.setattr(cicd_router, "CI_TOKEN", "")
        monkeypatch.delenv("CICD_REQUIRE_TRIGGER_TOKEN", raising=False)
        response = client.post(
            f"{self.PREFIX}/trigger/{project_id}",
            json={"scenario_ids": []},
            headers=viewer_headers,
        )
        assert response.status_code == 403

    def test_trigger_requires_token_when_strict_mode_enabled(
        self,
        client: TestClient,
        monkeypatch,
        auth_headers: dict[str, str],
        project_id: str,
    ) -> None:
        monkeypatch.setattr(cicd_router, "CI_TOKEN", "")
        monkeypatch.setenv("CICD_REQUIRE_TRIGGER_TOKEN", "1")
        response = client.post(
            f"{self.PREFIX}/trigger/{project_id}",
            json={"scenario_ids": []},
            headers=auth_headers,
        )
        assert response.status_code == 503

    def test_trigger_accepts_valid_ci_token_without_user_session(
        self,
        client: TestClient,
        monkeypatch,
        project_id: str,
    ) -> None:
        monkeypatch.setattr(cicd_router, "CI_TOKEN", "expected-ci-token")
        monkeypatch.setattr(cicd_router.httpx, "AsyncClient", _FakeAsyncClient)
        response = client.post(
            f"{self.PREFIX}/trigger/{project_id}",
            json={"scenario_ids": ["sc-1"]},
            headers={"X-CI-Token": "expected-ci-token"},
        )
        assert response.status_code == 200
        assert response.json()["triggered"] is True
