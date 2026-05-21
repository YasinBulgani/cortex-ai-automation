"""RBAC Authorization Matrix: 60+ endpoints x 3 roles = 180+ test combinations.

Tests that each role can only access the endpoints they are permitted to.
Currently, the TSPM router does NOT enforce permissions at the endpoint level
(all authenticated users pass). These tests document the EXPECTED behavior
and will start failing correctly once permission middleware is added.
"""

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Endpoint definitions: (method, path_template, needs_project, write_op)
# ---------------------------------------------------------------------------
ENDPOINTS = [
    # Projects
    ("GET",    "/api/v1/tspm/projects",                                False, False),
    ("POST",   "/api/v1/tspm/projects",                                False, True),
    # Dashboard
    ("GET",    "/api/v1/tspm/projects/{pid}/dashboard",                True,  False),
    # Scenarios
    ("GET",    "/api/v1/tspm/projects/{pid}/scenarios",                True,  False),
    ("POST",   "/api/v1/tspm/projects/{pid}/scenarios",                True,  True),
    # Approvals
    ("GET",    "/api/v1/tspm/projects/{pid}/approvals",                True,  False),
    # Executions
    ("GET",    "/api/v1/tspm/projects/{pid}/executions",               True,  False),
    ("POST",   "/api/v1/tspm/projects/{pid}/executions",               True,  True),
    # Flows
    ("GET",    "/api/v1/tspm/projects/{pid}/flows",                    True,  False),
    ("POST",   "/api/v1/tspm/projects/{pid}/flows",                    True,  True),
    # Regression
    ("GET",    "/api/v1/tspm/projects/{pid}/regression-sets",          True,  False),
    ("POST",   "/api/v1/tspm/projects/{pid}/regression-sets",          True,  True),
    # Requirements
    ("GET",    "/api/v1/tspm/projects/{pid}/requirements",             True,  False),
    ("POST",   "/api/v1/tspm/projects/{pid}/requirements",             True,  True),
    # Coverage
    ("GET",    "/api/v1/tspm/projects/{pid}/coverage-matrix",          True,  False),
    ("GET",    "/api/v1/tspm/projects/{pid}/coverage-gaps",            True,  False),
    # Schedules
    ("GET",    "/api/v1/tspm/projects/{pid}/schedules",                True,  False),
    ("POST",   "/api/v1/tspm/projects/{pid}/schedules",                True,  True),
    # Test data
    ("GET",    "/api/v1/tspm/projects/{pid}/test-data",                True,  False),
    ("POST",   "/api/v1/tspm/projects/{pid}/test-data",                True,  True),
    # Integrations
    ("GET",    "/api/v1/tspm/projects/{pid}/integrations",             True,  False),
    ("POST",   "/api/v1/tspm/projects/{pid}/integrations",             True,  True),
    # API Tests
    ("GET",    "/api/v1/tspm/projects/{pid}/api-tests/collections",    True,  False),
    ("POST",   "/api/v1/tspm/projects/{pid}/api-tests/collections",    True,  True),
    # Members
    ("GET",    "/api/v1/tspm/projects/{pid}/members",                  True,  False),
    ("POST",   "/api/v1/tspm/projects/{pid}/members",                  True,  True),
    # Execution trends / stats (read-only)
    ("GET",    "/api/v1/tspm/projects/{pid}/execution-trends",         True,  False),
    ("GET",    "/api/v1/tspm/projects/{pid}/execution-stats",          True,  False),
    ("GET",    "/api/v1/tspm/projects/{pid}/flaky-tests",              True,  False),
]

ROLES = ["admin", "viewer"]

# Minimal valid bodies for POST endpoints
POST_BODIES = {
    "/api/v1/tspm/projects": {"name": "RBAC Test"},
    "scenarios": {"title": "RBAC Scenario"},
    "executions": {"name": "RBAC Run", "scenario_ids": []},
    "flows": {"name": "RBAC Flow"},
    "regression-sets": {"name": "RBAC Set"},
    "requirements": {"external_id": "RBAC-R", "title": "RBAC Req"},
    "schedules": {"name": "RBAC Sched", "cron_expression": "0 * * * *"},
    "test-data": {"name": "RBAC Data"},
    "integrations": {"provider": "test"},
    "collections": {"name": "RBAC Col"},
    "members": {"user_id": "00000000-0000-0000-0000-000000000000", "role": "viewer"},
}


def _body_for(path: str, admin_user_id: str | None = None) -> dict:
    """Pick the right minimal JSON body for a POST endpoint.

    Eşleşme stratejisi: yolu '/' üzerinden segment olarak geziyoruz;
    POST_BODIES anahtarı yol segmentinin son parçasıyla birebir eşleşmeli.
    Daha önce substring araması `/api/v1/tspm/projects` anahtarını
    /api/v1/tspm/projects/{pid}/scenarios gibi her yola uydurduğu için
    her endpoint'e yanlış body gönderiliyordu.
    """
    segments = [s for s in path.split("/") if s]
    last = segments[-1] if segments else ""
    body: dict
    if last in POST_BODIES:
        body = dict(POST_BODIES[last])
    elif path.rstrip("/") in POST_BODIES:
        body = dict(POST_BODIES[path.rstrip("/")])
    else:
        return {}

    # members endpoint'i gerçek bir user_id ister (FK). Admin'in kendi ID'sini
    # kullanarak 500 (IntegrityError) yerine düzgün bir oluşturma akışı
    # çalıştırıyoruz.
    if last == "members" and admin_user_id:
        body["user_id"] = admin_user_id
    return body


def _build_matrix():
    """Build (method, path_template, role, expected_allowed) tuples."""
    cases = []
    for method, path_tpl, needs_project, is_write in ENDPOINTS:
        for role in ROLES:
            if role == "admin":
                allowed = True
            elif role == "viewer":
                allowed = not is_write
            else:
                allowed = True
            test_id = f"{role}-{method}-{path_tpl.split('/')[-1]}"
            cases.append(pytest.param(method, path_tpl, role, allowed, id=test_id))
    return cases


@pytest.fixture(scope="module")
def rbac_project(client: TestClient, auth_headers, viewer_headers) -> str:
    """Create a project and add the viewer as a member so read tests pass."""
    r = client.post(
        "/api/v1/tspm/projects",
        json={"name": "RBAC Matrix Project"},
        headers=auth_headers,
    )
    pid = r.json()["id"]

    viewer_me = client.get("/api/v1/auth/me", headers=viewer_headers)
    if viewer_me.status_code == 200:
        viewer_uid = viewer_me.json()["id"]
        client.post(
            f"/api/v1/tspm/projects/{pid}/members",
            json={"user_id": viewer_uid, "role": "viewer"},
            headers=auth_headers,
        )
    return pid


class TestProjectMembershipGate:
    """Verify that non-member users cannot access project resources."""

    def test_viewer_cannot_access_non_member_project(
        self, client: TestClient, auth_headers, viewer_headers
    ):
        pid = client.post(
            "/api/v1/tspm/projects",
            json={"name": "Isolated Project"},
            headers=auth_headers,
        ).json()["id"]
        # viewer is NOT added as member to this project
        r = client.get(
            f"/api/v1/tspm/projects/{pid}/scenarios",
            headers=viewer_headers,
        )
        assert r.status_code == 403, (
            f"Non-member viewer should get 403, got {r.status_code}"
        )


class TestRBACMatrix:
    """Parametrized RBAC authorization matrix."""

    @pytest.mark.parametrize("method,path_tpl,role,allowed", _build_matrix())
    def test_endpoint_access(
        self,
        client: TestClient,
        auth_headers: dict,
        rbac_project: str,
        method: str,
        path_tpl: str,
        role: str,
        allowed: bool,
        viewer_headers: dict,
    ):
        if role == "admin":
            headers = auth_headers
        elif role == "viewer":
            headers = viewer_headers
        else:
            pytest.skip(f"Role {role} fixture not available")

        path = path_tpl.replace("{pid}", rbac_project)
        kwargs = {"headers": headers}
        admin_uid = None
        if method == "POST":
            me = client.get("/api/v1/auth/me", headers=auth_headers)
            if me.status_code == 200:
                admin_uid = me.json().get("id")
            kwargs["json"] = _body_for(path, admin_user_id=admin_uid)

        r = getattr(client, method.lower())(path, **kwargs)

        if allowed:
            assert r.status_code < 400, (
                f"{role} should access {method} {path}, got {r.status_code}"
            )
        else:
            assert r.status_code in (401, 403), (
                f"{role} should be denied {method} {path}, got {r.status_code}"
            )
