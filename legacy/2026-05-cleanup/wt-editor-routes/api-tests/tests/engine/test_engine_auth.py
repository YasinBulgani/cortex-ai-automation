"""Engine (Flask) authentication tests — session-based auth."""

import pytest

from clients.engine_client import EngineClient
from config.constants import EnginePaths
from helpers.data_factory import random_email, random_password


@pytest.mark.auth
@pytest.mark.engine
class TestEngineRegister:

    def test_register_new_user(self):
        client = EngineClient()
        result = client.register(random_email(), random_password())
        assert result["status_code"] == 200
        assert result["data"]["success"] is True

    @pytest.mark.negative
    def test_register_empty_email(self):
        client = EngineClient()
        resp = client.post(EnginePaths.AUTH_REGISTER, json={"email": "", "password": "pass"})
        assert resp.status_code == 400

    @pytest.mark.negative
    def test_register_empty_password(self):
        client = EngineClient()
        resp = client.post(EnginePaths.AUTH_REGISTER, json={"email": "a@b.com", "password": ""})
        assert resp.status_code == 400

    @pytest.mark.negative
    def test_register_missing_fields(self):
        client = EngineClient()
        resp = client.post(EnginePaths.AUTH_REGISTER, json={})
        assert resp.status_code == 400


@pytest.mark.auth
@pytest.mark.engine
class TestEngineLogin:

    def test_login_hardcoded_bypass(self):
        """The engine has a test/test hardcoded bypass — verify it works."""
        client = EngineClient()
        result = client.login("test", "test")
        assert result["status_code"] == 200
        assert result["data"]["success"] is True

    @pytest.mark.negative
    def test_login_wrong_credentials(self):
        client = EngineClient()
        result = client.login("wrong@user.com", "wrongpass")
        assert result["status_code"] == 401

    @pytest.mark.negative
    def test_protected_endpoint_without_session(self):
        client = EngineClient()
        resp = client.get(EnginePaths.FEATURES)
        assert resp.status_code in (401, 302)


@pytest.mark.auth
@pytest.mark.engine
class TestEngineLogout:

    def test_logout(self, engine):
        result = engine.logout()
        assert result["status_code"] == 200
