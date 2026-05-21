"""Security tests — authentication bypass attempts."""

import pytest

from clients.fastapi_client import FastAPIClient
from config.constants import FastAPIPaths


@pytest.mark.security
class TestAuthBypass:
    """Verify that protected endpoints reject unauthenticated requests."""

    PROTECTED_GET_ENDPOINTS = [
        FastAPIPaths.DATASETS,
        FastAPIPaths.JOBS,
        FastAPIPaths.TSPM_PROJECTS,
        FastAPIPaths.AUTH_ME,
    ]

    @pytest.mark.parametrize("endpoint", PROTECTED_GET_ENDPOINTS)
    def test_get_endpoints_require_auth(self, endpoint):
        client = FastAPIClient()
        resp = client.get(endpoint)
        assert resp.status_code in (401, 403), (
            f"{endpoint} returned {resp.status_code} without auth"
        )

    def test_create_project_requires_auth(self):
        client = FastAPIClient()
        resp = client.post(FastAPIPaths.TSPM_PROJECTS, json={"name": "hacker"})
        assert resp.status_code in (401, 403)

    def test_create_dataset_requires_auth(self):
        client = FastAPIClient()
        resp = client.post(FastAPIPaths.DATASETS, json={"name": "hacker"})
        assert resp.status_code in (401, 403)

    def test_manipulated_jwt_rejected(self):
        client = FastAPIClient()
        client.set_token(
            "eyJhbGciOiJIUzI1NiJ9."
            "eyJzdWIiOiJhZG1pbiIsImV4cCI6OTk5OTk5OTk5OX0."
            "tampered_signature"
        )
        resp = client.get(FastAPIPaths.AUTH_ME)
        assert resp.status_code in (401, 403)
