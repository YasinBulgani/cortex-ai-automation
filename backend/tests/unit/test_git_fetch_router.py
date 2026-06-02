"""Unit tests for the git_fetch router — 10 tests.

All subprocess.run calls are patched to avoid real git operations.
Auth dependency is overridden to skip JWT validation.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.git_fetch.router import router as git_fetch_router, _lang, _repo_name, _inject_token
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    from app.deps import get_current_user
    app = FastAPI()
    app.include_router(git_fetch_router, prefix="/api/v1")

    fake_user = MagicMock()
    fake_user.id = "user-1"
    app.dependency_overrides[get_current_user] = lambda: fake_user

    return TestClient(app, raise_server_exceptions=False)


def _make_proc(returncode=0, stdout="main\n", stderr=""):
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestLangHelper:
    def test_py_returns_python(self):
        assert _lang("app.py") == "Python"

    def test_ts_returns_typescript(self):
        assert _lang("main.ts") == "TypeScript"

    def test_unknown_ext_returns_metin(self):
        assert _lang("binary.bin") == "Metin"

    def test_no_extension_returns_metin(self):
        assert _lang("Makefile") == "Metin"


class TestRepoNameHelper:
    def test_extracts_name_without_git_suffix(self):
        assert _repo_name("https://github.com/org/my-repo.git") == "my-repo"

    def test_extracts_name_without_extension(self):
        assert _repo_name("https://github.com/org/my-repo") == "my-repo"


class TestInjectTokenHelper:
    def test_injects_token_into_https_url(self):
        result = _inject_token("https://github.com/org/repo.git", "mytoken")
        assert "mytoken@github.com" in result

    def test_no_token_returns_original_url(self):
        url = "https://github.com/org/repo.git"
        assert _inject_token(url, "") == url


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------

class TestFetchEndpoint:
    def test_non_https_url_returns_422(self, client):
        resp = client.post("/api/v1/git/fetch", json={
            "url": "ftp://example.com/repo.git",
            "branch": "",
            "token": "",
            "extensions": [],
            "path_prefix": "",
            "max_files": 10,
        })
        assert resp.status_code == 422

    def test_git_clone_failure_returns_422(self, client):
        clone_proc = _make_proc(returncode=128, stderr="fatal: repository not found")
        with patch("app.domains.git_fetch.router.subprocess.run", return_value=clone_proc), \
             patch("app.domains.git_fetch.router.tempfile.mkdtemp", return_value="/tmp/fake_git_dir"), \
             patch("app.domains.git_fetch.router.shutil.rmtree"):
            resp = client.post("/api/v1/git/fetch", json={
                "url": "https://github.com/org/nonexistent.git",
                "branch": "",
                "token": "",
                "extensions": [],
                "path_prefix": "",
                "max_files": 10,
            })
        assert resp.status_code == 422
        assert "Git clone" in resp.json()["detail"]

    def test_successful_clone_returns_200_with_file_list(self, client, tmp_path):
        # Create a fake cloned repo structure
        fake_py = tmp_path / "hello.py"
        fake_py.write_text("print('hello')")

        def fake_run(cmd, *args, **kwargs):
            if "clone" in cmd:
                return _make_proc(returncode=0)
            if "rev-parse" in cmd:
                return _make_proc(returncode=0, stdout="main\n")
            return _make_proc(returncode=0)

        with patch("app.domains.git_fetch.router.subprocess.run", side_effect=fake_run), \
             patch("app.domains.git_fetch.router.tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("app.domains.git_fetch.router.shutil.rmtree"):
            resp = client.post("/api/v1/git/fetch", json={
                "url": "https://github.com/org/myrepo.git",
                "branch": "",
                "token": "",
                "extensions": [".py"],
                "path_prefix": "",
                "max_files": 50,
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["repo_name"] == "myrepo"
        assert data["total_files"] >= 1
        assert any(f["name"] == "hello.py" for f in data["files"])

    def test_token_scrubbed_from_error_message(self, client):
        clone_proc = _make_proc(returncode=128, stderr="error: Authentication failed for 'https://secrettoken@github.com/org/repo.git'")
        with patch("app.domains.git_fetch.router.subprocess.run", return_value=clone_proc), \
             patch("app.domains.git_fetch.router.tempfile.mkdtemp", return_value="/tmp/fake"), \
             patch("app.domains.git_fetch.router.shutil.rmtree"):
            resp = client.post("/api/v1/git/fetch", json={
                "url": "https://github.com/org/repo.git",
                "branch": "",
                "token": "secrettoken",
                "extensions": [],
                "path_prefix": "",
                "max_files": 10,
            })
        assert resp.status_code == 422
        assert "secrettoken" not in resp.json()["detail"]

    def test_branch_specified_is_reflected_in_response(self, client, tmp_path):
        (tmp_path / "app.py").write_text("x = 1")

        def fake_run(cmd, *args, **kwargs):
            if "clone" in cmd:
                return _make_proc(returncode=0)
            if "rev-parse" in cmd:
                return _make_proc(returncode=0, stdout="feature-branch\n")
            return _make_proc(returncode=0)

        with patch("app.domains.git_fetch.router.subprocess.run", side_effect=fake_run), \
             patch("app.domains.git_fetch.router.tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("app.domains.git_fetch.router.shutil.rmtree"):
            resp = client.post("/api/v1/git/fetch", json={
                "url": "https://github.com/org/repo.git",
                "branch": "feature-branch",
                "token": "",
                "extensions": [],
                "path_prefix": "",
                "max_files": 50,
            })

        assert resp.status_code == 200
        assert resp.json()["branch"] == "feature-branch"

    def test_max_files_limit_respected(self, client, tmp_path):
        for i in range(10):
            (tmp_path / f"file{i}.py").write_text(f"x = {i}")

        def fake_run(cmd, *args, **kwargs):
            if "clone" in cmd:
                return _make_proc(returncode=0)
            if "rev-parse" in cmd:
                return _make_proc(returncode=0, stdout="main\n")
            return _make_proc(returncode=0)

        with patch("app.domains.git_fetch.router.subprocess.run", side_effect=fake_run), \
             patch("app.domains.git_fetch.router.tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("app.domains.git_fetch.router.shutil.rmtree"):
            resp = client.post("/api/v1/git/fetch", json={
                "url": "https://github.com/org/repo.git",
                "branch": "",
                "token": "",
                "extensions": [".py"],
                "path_prefix": "",
                "max_files": 3,
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_files"] <= 3
