"""Smoke tests for Jenkins outbound integration (cicd/jenkins_*)."""

from __future__ import annotations

import os

import pytest

from app.domains.cicd import jenkins_client, jenkins_service


# ── Encryption round-trip ─────────────────────────────────────────────────────

def test_token_roundtrip_with_jwt_derived_key():
    cipher = jenkins_service.encrypt_token("super-secret-token")
    assert cipher != "super-secret-token"
    plain = jenkins_service.decrypt_token(cipher)
    assert plain == "super-secret-token"


def test_token_decrypt_rejects_garbage():
    with pytest.raises(ValueError):
        jenkins_service.decrypt_token("not-a-real-fernet-blob")


# ── Jenkins client behaviour (mocked transport) ───────────────────────────────

class _Resp:
    def __init__(self, status_code=200, json_data=None, headers=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = headers or {}
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


class _AsyncClientMock:
    def __init__(self, response):
        self._response = response
        self.last_url = None
        self.last_auth = None
        self.last_data = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, auth=None):
        self.last_url = url
        self.last_auth = auth
        return self._response

    async def post(self, url, auth=None, data=None):
        self.last_url = url
        self.last_auth = auth
        self.last_data = data
        return self._response


@pytest.mark.asyncio
async def test_ping_success(monkeypatch):
    resp = _Resp(
        status_code=200,
        json_data={"nodeName": "master", "mode": "NORMAL"},
        headers={"X-Jenkins": "2.452.1"},
    )
    monkeypatch.setattr(
        jenkins_client.httpx, "AsyncClient", lambda timeout=None: _AsyncClientMock(resp)
    )
    client = jenkins_client.JenkinsClient("https://j.example.com/", "alice", "tok")
    info = await client.ping()
    assert info["version"] == "2.452.1"
    assert info["node_name"] == "master"


@pytest.mark.asyncio
async def test_ping_unauthorized(monkeypatch):
    resp = _Resp(status_code=401, text="nope")
    monkeypatch.setattr(
        jenkins_client.httpx, "AsyncClient", lambda timeout=None: _AsyncClientMock(resp)
    )
    client = jenkins_client.JenkinsClient("https://j.example.com", "alice", "tok")
    with pytest.raises(jenkins_client.JenkinsClientError) as exc:
        await client.ping()
    assert "401" in str(exc.value)


@pytest.mark.asyncio
async def test_trigger_build_no_params(monkeypatch):
    mock = _AsyncClientMock(
        _Resp(status_code=201, headers={"Location": "https://j.example.com/queue/item/42/"})
    )
    monkeypatch.setattr(jenkins_client.httpx, "AsyncClient", lambda timeout=None: mock)
    client = jenkins_client.JenkinsClient("https://j.example.com", "alice", "tok")
    out = await client.trigger_build("my-job")
    assert out["queue_url"].endswith("/queue/item/42/")
    assert mock.last_url.endswith("/job/my-job/build")
    assert mock.last_data is None


@pytest.mark.asyncio
async def test_trigger_build_with_params(monkeypatch):
    mock = _AsyncClientMock(_Resp(status_code=201, headers={"Location": "queue/url"}))
    monkeypatch.setattr(jenkins_client.httpx, "AsyncClient", lambda timeout=None: mock)
    client = jenkins_client.JenkinsClient("https://j.example.com", "alice", "tok")
    await client.trigger_build("my-job", {"BRANCH": "main"})
    assert mock.last_url.endswith("/job/my-job/buildWithParameters")
    assert mock.last_data == {"BRANCH": "main"}


@pytest.mark.asyncio
async def test_last_build_404(monkeypatch):
    monkeypatch.setattr(
        jenkins_client.httpx,
        "AsyncClient",
        lambda timeout=None: _AsyncClientMock(_Resp(status_code=404)),
    )
    client = jenkins_client.JenkinsClient("https://j.example.com", "alice", "tok")
    out = await client.last_build("missing-job")
    assert out == {"exists": False, "job": "missing-job"}


@pytest.mark.asyncio
async def test_last_build_success(monkeypatch):
    resp = _Resp(
        status_code=200,
        json_data={
            "number": 7,
            "result": "SUCCESS",
            "building": False,
            "duration": 12345,
            "timestamp": 1700000000000,
            "url": "https://j.example.com/job/my-job/7/",
        },
    )
    monkeypatch.setattr(
        jenkins_client.httpx, "AsyncClient", lambda timeout=None: _AsyncClientMock(resp)
    )
    client = jenkins_client.JenkinsClient("https://j.example.com", "alice", "tok")
    out = await client.last_build("my-job")
    assert out["exists"] is True
    assert out["number"] == 7
    assert out["result"] == "SUCCESS"
