"""TC-1101..TC-1112: Schedule tests (desktop + Visium Farm mobil)."""

from fastapi.testclient import TestClient


class TestCreateSchedule:
    """TC-1101, TC-1105"""

    def test_create_schedule_success(
        self, client: TestClient, auth_headers, project_id, create_scenario
    ):
        sid = create_scenario(project_id)
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/schedules",
            json={"name": "Gece Koşusu", "cron_expression": "0 2 * * *", "scenario_ids": [sid]},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["is_active"] is True

    def test_empty_cron_returns_422(
        self, client: TestClient, auth_headers, project_id
    ):
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/schedules",
            json={"name": "Bad", "cron_expression": ""},
            headers=auth_headers,
        )
        assert r.status_code == 422


class TestTriggerSchedule:
    """TC-1102, TC-1103, TC-1104"""

    def test_trigger_creates_execution(
        self, client: TestClient, auth_headers, project_id,
        create_scenario, create_schedule
    ):
        sid = create_scenario(project_id)
        sched_id = create_schedule(project_id, scenario_ids=[sid])
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/schedules/{sched_id}/trigger",
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert "Scheduled:" in r.json()["name"]

    def test_trigger_empty_schedule_returns_400(
        self, client: TestClient, auth_headers, project_id, create_schedule
    ):
        sched_id = create_schedule(project_id)
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/schedules/{sched_id}/trigger",
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_trigger_uses_regression_set_fallback(
        self, client: TestClient, auth_headers, project_id,
        create_scenario, create_regression_set
    ):
        sid = create_scenario(project_id)
        rs_id = create_regression_set(project_id)
        client.post(
            f"/api/v1/tspm/projects/{project_id}/regression-sets/{rs_id}/add",
            json={"scenario_ids": [sid]},
            headers=auth_headers,
        )
        sched = client.post(
            f"/api/v1/tspm/projects/{project_id}/schedules",
            json={
                "name": "Fallback",
                "cron_expression": "0 3 * * *",
                "regression_set_id": rs_id,
            },
            headers=auth_headers,
        )
        sched_id = sched.json()["id"]
        trigger = client.post(
            f"/api/v1/tspm/projects/{project_id}/schedules/{sched_id}/trigger",
            headers=auth_headers,
        )
        assert trigger.status_code == 201
        assert trigger.json()["scenario_total"] >= 1


class TestMobileSchedule:
    """TC-1106..TC-1112: Visium Farm mobil zamanlayıcı."""

    def test_create_mobile_schedule_ios(
        self, client: TestClient, auth_headers, project_id, create_scenario
    ):
        sid = create_scenario(project_id)
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/schedules",
            json={
                "name": "iOS Gece Koşusu",
                "cron_expression": "0 2 * * *",
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
        assert body["is_active"] is True

    def test_create_mobile_schedule_android(
        self, client: TestClient, auth_headers, project_id, create_scenario
    ):
        sid = create_scenario(project_id)
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/schedules",
            json={
                "name": "Android Sabah Koşusu",
                "cron_expression": "0 6 * * *",
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

    def test_mobile_schedule_platform_in_list(
        self, client: TestClient, auth_headers, project_id, create_scenario
    ):
        """list endpoint mobile schedule'ı platform bilgisiyle döndürmeli."""
        sid = create_scenario(project_id)
        client.post(
            f"/api/v1/tspm/projects/{project_id}/schedules",
            json={
                "name": "List Testi iOS",
                "cron_expression": "0 3 * * *",
                "scenario_ids": [sid],
                "platform": "ios",
                "device_name": "iPhone SE",
            },
            headers=auth_headers,
        )
        r = client.get(
            f"/api/v1/tspm/projects/{project_id}/schedules",
            headers=auth_headers,
        )
        assert r.status_code == 200
        mobile = [s for s in r.json() if s.get("platform") == "ios"]
        assert len(mobile) >= 1
        assert mobile[0]["device_name"] is not None

    def test_update_schedule_adds_platform(
        self, client: TestClient, auth_headers, project_id, create_schedule
    ):
        """Mevcut desktop schedule'a platform eklenebilmeli."""
        sched_id = create_schedule(project_id)
        r = client.put(
            f"/api/v1/tspm/projects/{project_id}/schedules/{sched_id}",
            json={"platform": "android", "device_name": "Pixel 6a"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["platform"] == "android"
        assert body["device_name"] == "Pixel 6a"

    def test_mobile_schedule_deactivate_toggle(
        self, client: TestClient, auth_headers, project_id, create_scenario
    ):
        sid = create_scenario(project_id)
        create_r = client.post(
            f"/api/v1/tspm/projects/{project_id}/schedules",
            json={
                "name": "Toggle iOS",
                "cron_expression": "0 1 * * *",
                "scenario_ids": [sid],
                "platform": "ios",
                "device_name": "iPad Pro",
            },
            headers=auth_headers,
        )
        sched_id = create_r.json()["id"]
        toggle = client.put(
            f"/api/v1/tspm/projects/{project_id}/schedules/{sched_id}",
            json={"is_active": False},
            headers=auth_headers,
        )
        assert toggle.status_code == 200
        assert toggle.json()["is_active"] is False
        # platform korunmuş olmalı
        assert toggle.json()["platform"] == "ios"

    def test_desktop_schedule_has_null_platform(
        self, client: TestClient, auth_headers, project_id, create_scenario
    ):
        """platform verilmeden oluşturulan schedule'da platform None olmalı."""
        sid = create_scenario(project_id)
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/schedules",
            json={
                "name": "Desktop Schedule",
                "cron_expression": "0 4 * * *",
                "scenario_ids": [sid],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body.get("platform") is None
        assert body.get("device_name") is None
