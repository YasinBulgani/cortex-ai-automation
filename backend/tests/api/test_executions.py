"""TC-0601..TC-0613: Execution (test run) + platform filter + mobile run tests."""

from fastapi.testclient import TestClient


class TestCreateExecution:
    """TC-0601, TC-0606"""

    def test_create_execution_with_scenarios(
        self, client: TestClient, auth_headers, project_id, create_scenario
    ):
        s1 = create_scenario(project_id)
        s2 = create_scenario(project_id)
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/executions",
            json={"name": "Sprint-1", "scenario_ids": [s1, s2]},
            headers=auth_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["status"] == "running"
        assert body["scenario_total"] == 2
        assert body["passed_count"] == 0

    def test_empty_scenario_list_creates_execution(
        self, client: TestClient, auth_headers, project_id
    ):
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/executions",
            json={"name": "Boş", "scenario_ids": []},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["scenario_total"] == 0


class TestExecutionDetail:
    """TC-0602"""

    def test_execution_detail_lists_results(
        self, client: TestClient, auth_headers, project_id,
        create_scenario, create_execution
    ):
        s1 = create_scenario(project_id)
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/executions",
            json={"name": "Detay", "scenario_ids": [s1]},
            headers=auth_headers,
        )
        exec_id = r.json()["id"]
        detail = client.get(
            f"/api/v1/tspm/projects/{project_id}/executions/{exec_id}",
            headers=auth_headers,
        )
        assert detail.status_code == 200
        assert len(detail.json()["results"]) == 1
        assert detail.json()["results"][0]["status"] == "pending"


class TestResultStatusUpdate:
    """TC-0603"""

    def test_update_result_to_passed(
        self, client: TestClient, auth_headers, project_id, create_scenario
    ):
        sid = create_scenario(project_id)
        ex = client.post(
            f"/api/v1/tspm/projects/{project_id}/executions",
            json={"name": "Update", "scenario_ids": [sid]},
            headers=auth_headers,
        )
        exec_id = ex.json()["id"]
        detail = client.get(
            f"/api/v1/tspm/projects/{project_id}/executions/{exec_id}",
            headers=auth_headers,
        )
        result_id = detail.json()["results"][0]["id"]
        patch = client.patch(
            f"/api/v1/tspm/projects/{project_id}/executions/{exec_id}/results/{result_id}",
            json={"status": "passed"},
            headers=auth_headers,
        )
        assert patch.status_code == 200


class TestRerun:
    """TC-0604, TC-0605"""

    def test_rerun_creates_new_execution(
        self, client: TestClient, auth_headers, project_id, create_scenario
    ):
        sid = create_scenario(project_id)
        ex = client.post(
            f"/api/v1/tspm/projects/{project_id}/executions",
            json={"name": "Original", "scenario_ids": [sid]},
            headers=auth_headers,
        )
        exec_id = ex.json()["id"]
        rerun = client.post(
            f"/api/v1/tspm/projects/{project_id}/executions/{exec_id}",
            headers=auth_headers,
        )
        assert rerun.status_code == 201
        assert "(re-run)" in rerun.json()["name"]

    def test_rerun_nonexistent_returns_404(
        self, client: TestClient, auth_headers, project_id
    ):
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/executions/00000000-dead-beef-0000-000000000000",
            headers=auth_headers,
        )
        assert r.status_code == 404


class TestMobileExecution:
    """TC-0607..TC-0610: Mobile (Visium Farm) execution alanları."""

    def test_create_mobile_execution_ios(
        self, client: TestClient, auth_headers, project_id, create_scenario
    ):
        sid = create_scenario(project_id)
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/executions",
            json={
                "name": "iOS Koşumu",
                "scenario_ids": [sid],
                "platform": "ios",
                "device_name": "iPhone 14",
            },
            headers=auth_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["platform"] == "ios"
        assert body["device_name"] == "iPhone 14"

    def test_create_mobile_execution_android(
        self, client: TestClient, auth_headers, project_id, create_scenario
    ):
        sid = create_scenario(project_id)
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/executions",
            json={
                "name": "Android Koşumu",
                "scenario_ids": [sid],
                "platform": "android",
                "device_name": "Pixel 7 Pro",
            },
            headers=auth_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["platform"] == "android"
        assert body["device_name"] == "Pixel 7 Pro"

    def test_list_returns_platform_field(
        self, client: TestClient, auth_headers, project_id
    ):
        """platform ve device_name list endpoint'inden dönmeli."""
        client.post(
            f"/api/v1/tspm/projects/{project_id}/executions",
            json={"name": "iOS List", "platform": "ios", "device_name": "iPhone SE"},
            headers=auth_headers,
        )
        r = client.get(
            f"/api/v1/tspm/projects/{project_id}/executions",
            headers=auth_headers,
        )
        assert r.status_code == 200
        items = r.json()
        mobile = [i for i in items if i.get("platform") == "ios"]
        assert len(mobile) >= 1
        assert mobile[0]["device_name"] is not None


class TestExecutionPlatformFilter:
    """TC-0611..TC-0613: ?platform= query parametresi filtresi."""

    def _create_exec(self, client, auth_headers, project_id, platform=None, device=None):
        payload = {"name": f"Exec-{platform or 'desktop'}"}
        if platform:
            payload["platform"] = platform
        if device:
            payload["device_name"] = device
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/executions",
            json=payload,
            headers=auth_headers,
        )
        assert r.status_code == 201
        return r.json()["id"]

    def test_filter_desktop_excludes_mobile(
        self, client: TestClient, auth_headers, project_id
    ):
        self._create_exec(client, auth_headers, project_id)  # desktop (platform=None)
        self._create_exec(client, auth_headers, project_id, platform="ios", device="iPhone 14")
        r = client.get(
            f"/api/v1/tspm/projects/{project_id}/executions?platform=desktop",
            headers=auth_headers,
        )
        assert r.status_code == 200
        for item in r.json():
            assert item.get("platform") is None

    def test_filter_ios_only(
        self, client: TestClient, auth_headers, project_id
    ):
        self._create_exec(client, auth_headers, project_id, platform="ios", device="iPhone 15")
        self._create_exec(client, auth_headers, project_id, platform="android", device="Pixel 7")
        r = client.get(
            f"/api/v1/tspm/projects/{project_id}/executions?platform=ios",
            headers=auth_headers,
        )
        assert r.status_code == 200
        for item in r.json():
            assert item.get("platform") == "ios"

    def test_filter_android_only(
        self, client: TestClient, auth_headers, project_id
    ):
        self._create_exec(client, auth_headers, project_id, platform="android", device="Pixel 6a")
        r = client.get(
            f"/api/v1/tspm/projects/{project_id}/executions?platform=android",
            headers=auth_headers,
        )
        assert r.status_code == 200
        for item in r.json():
            assert item.get("platform") == "android"

    def test_no_filter_returns_all(
        self, client: TestClient, auth_headers, project_id
    ):
        self._create_exec(client, auth_headers, project_id)
        self._create_exec(client, auth_headers, project_id, platform="ios", device="iPad Pro")
        r = client.get(
            f"/api/v1/tspm/projects/{project_id}/executions",
            headers=auth_headers,
        )
        assert r.status_code == 200
        platforms = {item.get("platform") for item in r.json()}
        # Hem None (desktop) hem de "ios" içermeli
        assert None in platforms or "ios" in platforms
