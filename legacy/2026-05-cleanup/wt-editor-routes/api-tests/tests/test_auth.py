"""Authentication endpoint tests — FastAPI JWT auth."""

import pytest

from clients.fastapi_client import FastAPIClient
from config.constants import FastAPIPaths
from config.settings import settings
from helpers.data_factory import random_email, long_string


@pytest.mark.auth
@pytest.mark.critical
class TestLogin:

    def test_login_valid_credentials(self):
        client = FastAPIClient()
        result = client.login(settings.TEST_USER_EMAIL, settings.TEST_USER_PASSWORD)
        assert result["status_code"] == 200
        assert "access_token" in result["data"]
        assert result["data"]["token_type"] == "bearer"

    def test_login_wrong_password(self):
        client = FastAPIClient()
        resp = client.post(
            FastAPIPaths.AUTH_LOGIN,
            json={"email": settings.TEST_USER_EMAIL, "password": "wrong_password_123"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_email(self):
        client = FastAPIClient()
        resp = client.post(
            FastAPIPaths.AUTH_LOGIN,
            json={"email": "nonexistent@nowhere.com", "password": "anything"},
        )
        assert resp.status_code == 401

    @pytest.mark.negative
    def test_login_empty_password(self):
        client = FastAPIClient()
        resp = client.post(
            FastAPIPaths.AUTH_LOGIN,
            json={"email": "user@test.com", "password": ""},
        )
        assert resp.status_code == 422

    @pytest.mark.negative
    def test_login_invalid_email_format(self):
        client = FastAPIClient()
        resp = client.post(
            FastAPIPaths.AUTH_LOGIN,
            json={"email": "not-an-email", "password": "pass"},
        )
        assert resp.status_code == 422

    @pytest.mark.negative
    def test_login_empty_body(self):
        client = FastAPIClient()
        resp = client.post(FastAPIPaths.AUTH_LOGIN, json={})
        assert resp.status_code == 422

    @pytest.mark.negative
    def test_login_no_body(self):
        client = FastAPIClient()
        resp = client.post(FastAPIPaths.AUTH_LOGIN)
        assert resp.status_code == 422

    @pytest.mark.boundary
    def test_login_very_long_email(self):
        client = FastAPIClient()
        long_email = "a" * 300 + "@test.com"
        resp = client.post(
            FastAPIPaths.AUTH_LOGIN,
            json={"email": long_email, "password": "x"},
        )
        assert resp.status_code in (401, 422)

    @pytest.mark.boundary
    def test_login_very_long_password(self):
        client = FastAPIClient()
        resp = client.post(
            FastAPIPaths.AUTH_LOGIN,
            json={"email": "user@test.com", "password": long_string(10000)},
        )
        assert resp.status_code in (401, 422)

    @pytest.mark.security
    def test_login_sql_injection(self):
        client = FastAPIClient()
        resp = client.post(
            FastAPIPaths.AUTH_LOGIN,
            json={"email": "' OR 1=1--", "password": "x"},
        )
        assert resp.status_code in (401, 422)


@pytest.mark.auth
class TestMe:

    def test_me_with_valid_token(self, api):
        resp = api.get(FastAPIPaths.AUTH_ME)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "email" in data
        assert "roles" in data

    @pytest.mark.negative
    def test_me_without_token(self, api_noauth):
        resp = api_noauth.get(FastAPIPaths.AUTH_ME)
        assert resp.status_code in (401, 403)

    @pytest.mark.negative
    def test_me_with_invalid_token(self):
        client = FastAPIClient()
        client.set_token("invalid.jwt.token")
        resp = client.get(FastAPIPaths.AUTH_ME)
        assert resp.status_code in (401, 403)

    @pytest.mark.negative
    def test_me_with_expired_token(self):
        # Manually crafted expired JWT — will fail decode
        client = FastAPIClient()
        client.set_token(
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxMDAwMDAwMDAwfQ."
            "fakesig"
        )
        resp = client.get(FastAPIPaths.AUTH_ME)
        assert resp.status_code in (401, 403)
