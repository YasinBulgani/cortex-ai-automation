"""Unit tests for app.domains.git_fetch.service facade.

Covers: fetch_repo, get_diff, list_commits
subprocess and filesystem calls are fully mocked.
"""
from __future__ import annotations

import pytest

try:
    from unittest.mock import MagicMock, patch
    import app.domains.git_fetch.service as git_svc  # noqa: F401
except ImportError as _exc:
    pytestmark = pytest.mark.skipif(True, reason=f"git_fetch service not importable: {_exc}")
    git_svc = None  # type: ignore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_proc(returncode=0, stdout="main\n", stderr=""):
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


# ---------------------------------------------------------------------------
# fetch_repo
# ---------------------------------------------------------------------------

class TestFetchRepo:
    def test_fetch_repo_empty_url_raises_value_error(self):
        """Empty URL raises ValueError."""
        with pytest.raises(ValueError, match="boş olamaz"):
            git_svc.fetch_repo("")

    def test_fetch_repo_non_http_url_raises_value_error(self):
        """git:// and ssh:// URLs are rejected."""
        with pytest.raises(ValueError, match="http/https"):
            git_svc.fetch_repo("git@github.com:user/repo.git")

    def test_fetch_repo_clone_failure_raises_value_error(self, monkeypatch):
        """Non-zero git clone returncode raises ValueError with error text."""
        clone_fail = _make_proc(returncode=128, stderr="Repository not found")
        branch_proc = _make_proc(stdout="main\n")

        with patch("app.domains.git_fetch.service.subprocess.run") as mock_run, \
             patch("app.domains.git_fetch.service.tempfile.mkdtemp", return_value="/tmp/fake"), \
             patch("app.domains.git_fetch.service.shutil.rmtree"):
            mock_run.return_value = clone_fail
            with pytest.raises(ValueError, match="Git clone hatası"):
                git_svc.fetch_repo("https://github.com/user/missing-repo")

    def test_fetch_repo_success_returns_required_keys(self, tmp_path):
        """Happy path returns dict with repo_id, repo_name, branch, files, etc."""
        # Create a minimal fake repo directory with one file
        fake_repo = tmp_path / "repo"
        fake_repo.mkdir()
        (fake_repo / "main.py").write_text("print('hello')", encoding="utf-8")

        clone_proc = _make_proc(returncode=0)
        branch_proc = _make_proc(stdout="main\n")

        with patch("app.domains.git_fetch.service.subprocess.run") as mock_run, \
             patch("app.domains.git_fetch.service.tempfile.mkdtemp", return_value=str(fake_repo)), \
             patch("app.domains.git_fetch.service.shutil.rmtree"):
            mock_run.side_effect = [clone_proc, branch_proc]
            result = git_svc.fetch_repo("https://github.com/user/myrepo.git")

        assert "repo_id" in result
        assert "repo_name" in result
        assert "branch" in result
        assert "files" in result
        assert "total_files" in result
        assert "skipped" in result
        assert isinstance(result["files"], list)

    def test_fetch_repo_token_is_redacted_from_error_message(self, monkeypatch, tmp_path):
        """PAT token is replaced with *** in the ValueError message."""
        fake_dir = tmp_path / "clone"
        fake_dir.mkdir()
        fail_proc = _make_proc(returncode=128, stderr="fatal: https://mytoken@github.com/repo.git/")

        with patch("app.domains.git_fetch.service.subprocess.run") as mock_run, \
             patch("app.domains.git_fetch.service.tempfile.mkdtemp", return_value=str(fake_dir)), \
             patch("app.domains.git_fetch.service.shutil.rmtree"):
            mock_run.return_value = fail_proc
            with pytest.raises(ValueError) as exc_info:
                git_svc.fetch_repo(
                    "https://github.com/user/private.git",
                    token="mytoken",
                )
            assert "mytoken" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# get_diff
# ---------------------------------------------------------------------------

class TestGetDiff:
    def _seed_repo(self, repo_id="repo-abc"):
        """Insert a fake entry into the in-process store."""
        git_svc._repos[repo_id] = {
            "repo_id": repo_id,
            "repo_name": "myrepo",
            "branch": "main",
            "files": [],
            "total_files": 0,
            "skipped": 0,
        }
        return repo_id

    def teardown_method(self, method):
        git_svc._repos.clear()

    def test_get_diff_unknown_repo_raises_key_error(self):
        """repo_id not in store raises KeyError."""
        with pytest.raises(KeyError, match="repo-unknown"):
            git_svc.get_diff("repo-unknown")

    def test_get_diff_known_repo_returns_required_keys(self):
        """get_diff returns dict with repo_id, from_ref, to_ref, note."""
        rid = self._seed_repo("repo-diff-1")
        result = git_svc.get_diff(rid, from_ref="HEAD~2", to_ref="HEAD")

        assert result["repo_id"] == rid
        assert result["from_ref"] == "HEAD~2"
        assert result["to_ref"] == "HEAD"
        assert "note" in result


# ---------------------------------------------------------------------------
# list_commits
# ---------------------------------------------------------------------------

class TestListCommits:
    def _seed_repo(self, repo_id="repo-commits"):
        git_svc._repos[repo_id] = {
            "repo_id": repo_id,
            "repo_name": "myrepo",
            "branch": "develop",
            "files": [],
            "total_files": 0,
            "skipped": 0,
        }
        return repo_id

    def teardown_method(self, method):
        git_svc._repos.clear()

    def test_list_commits_unknown_repo_raises_key_error(self):
        """Requesting commits for unknown repo_id raises KeyError."""
        with pytest.raises(KeyError, match="repo-nope"):
            git_svc.list_commits("repo-nope")

    def test_list_commits_returns_list_with_sha_and_branch(self):
        """list_commits returns a list of commit dicts with sha and branch."""
        rid = self._seed_repo("repo-commits")
        result = git_svc.list_commits(rid)

        assert isinstance(result, list)
        assert len(result) >= 1
        commit = result[0]
        assert "sha" in commit
        assert "branch" in commit
        assert commit["branch"] == "develop"
