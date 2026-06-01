"""Unit tests for infra.git_client pure helper functions and dataclasses.

All tests are self-contained: no git subprocess calls, no HTTP.
Covers:
  - _bool: string → boolean coercion
  - _branch_name: slug → safe git branch name
  - _commit_env: GitConfig → git author environment dict
  - CommitResult: frozen dataclass structure
  - GitConfig: default values and construction
"""
from __future__ import annotations

from pathlib import Path

import pytest

try:
    from app.infra.git_client import (
        _bool,
        _branch_name,
        _commit_env,
        CommitResult,
        GitConfig,
        GitClientError,
    )
    _GC_OK = True
except ImportError:
    _GC_OK = False


# ---------------------------------------------------------------------------
# _bool
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GC_OK, reason="git_client import failed")
class TestBool:
    def test_true_string(self):
        assert _bool("true") is True

    def test_True_string(self):
        assert _bool("True") is True

    def test_TRUE_uppercase(self):
        assert _bool("TRUE") is True

    def test_one_string(self):
        assert _bool("1") is True

    def test_yes_string(self):
        assert _bool("yes") is True

    def test_YES_uppercase(self):
        assert _bool("YES") is True

    def test_on_string(self):
        assert _bool("on") is True

    def test_ON_uppercase(self):
        assert _bool("ON") is True

    def test_false_string(self):
        assert _bool("false") is False

    def test_zero_string(self):
        assert _bool("0") is False

    def test_no_string(self):
        assert _bool("no") is False

    def test_empty_string(self):
        assert _bool("") is False

    def test_none(self):
        assert _bool(None) is False

    def test_arbitrary_string(self):
        assert _bool("maybe") is False

    def test_whitespace_trimmed(self):
        assert _bool("  true  ") is True

    def test_returns_bool(self):
        assert isinstance(_bool("1"), bool)


# ---------------------------------------------------------------------------
# _branch_name
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GC_OK, reason="git_client import failed")
class TestBranchName:
    def _cfg(self, prefix="dsl/edit-"):
        return GitConfig(branch_prefix=prefix)

    def test_simple_slug(self):
        result = _branch_name(self._cfg(), "hello-world")
        assert result == "dsl/edit-hello-world"

    def test_spaces_become_hyphens(self):
        result = _branch_name(self._cfg(), "hello world")
        assert "hello-world" in result

    def test_special_chars_replaced(self):
        result = _branch_name(self._cfg(), "special!@#chars")
        assert "!" not in result
        assert "@" not in result
        assert "#" not in result

    def test_leading_hyphens_stripped(self):
        result = _branch_name(self._cfg(), "---leading")
        assert not result.split("/", 1)[-1].startswith("-")

    def test_trailing_hyphens_stripped(self):
        result = _branch_name(self._cfg(), "trailing---")
        assert not result.split("/", 1)[-1].endswith("-")

    def test_max_64_chars_in_slug(self):
        long_slug = "a" * 100
        result = _branch_name(self._cfg(), long_slug)
        # Slug part (after prefix) should be ≤ 64 chars
        slug_part = result[len("dsl/edit-"):]
        assert len(slug_part) <= 64

    def test_empty_slug_uses_edit_default(self):
        result = _branch_name(self._cfg(), "")
        assert result.endswith("edit")

    def test_custom_prefix(self):
        result = _branch_name(self._cfg(prefix="feature/"), "my-change")
        assert result.startswith("feature/")

    def test_returns_string(self):
        assert isinstance(_branch_name(self._cfg(), "test"), str)

    def test_dots_preserved(self):
        result = _branch_name(self._cfg(), "v1.2.3")
        assert "1.2.3" in result or "1-2-3" in result  # dots allowed or hyphenated


# ---------------------------------------------------------------------------
# _commit_env
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GC_OK, reason="git_client import failed")
class TestCommitEnv:
    def test_has_author_name(self):
        cfg = GitConfig(author_name="Test Bot")
        env = _commit_env(cfg)
        assert "GIT_AUTHOR_NAME" in env
        assert env["GIT_AUTHOR_NAME"] == "Test Bot"

    def test_has_author_email(self):
        cfg = GitConfig(author_email="bot@example.com")
        env = _commit_env(cfg)
        assert "GIT_AUTHOR_EMAIL" in env
        assert env["GIT_AUTHOR_EMAIL"] == "bot@example.com"

    def test_has_committer_name(self):
        cfg = GitConfig(author_name="Commit Bot")
        env = _commit_env(cfg)
        assert "GIT_COMMITTER_NAME" in env
        assert env["GIT_COMMITTER_NAME"] == "Commit Bot"

    def test_has_committer_email(self):
        cfg = GitConfig(author_email="commit@example.com")
        env = _commit_env(cfg)
        assert "GIT_COMMITTER_EMAIL" in env
        assert env["GIT_COMMITTER_EMAIL"] == "commit@example.com"

    def test_author_and_committer_same(self):
        cfg = GitConfig(author_name="Unified Bot", author_email="unified@example.com")
        env = _commit_env(cfg)
        assert env["GIT_AUTHOR_NAME"] == env["GIT_COMMITTER_NAME"]
        assert env["GIT_AUTHOR_EMAIL"] == env["GIT_COMMITTER_EMAIL"]

    def test_returns_dict(self):
        assert isinstance(_commit_env(GitConfig()), dict)

    def test_has_4_keys(self):
        env = _commit_env(GitConfig())
        assert len(env) == 4

    def test_default_author_name(self):
        env = _commit_env(GitConfig())
        assert env["GIT_AUTHOR_NAME"] == "DSL Bot"

    def test_default_author_email(self):
        env = _commit_env(GitConfig())
        assert len(env["GIT_AUTHOR_EMAIL"]) > 0


# ---------------------------------------------------------------------------
# CommitResult
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GC_OK, reason="git_client import failed")
class TestCommitResult:
    def test_required_fields(self):
        result = CommitResult(sha="abc123", branch="main", pushed=True)
        assert result.sha == "abc123"
        assert result.branch == "main"
        assert result.pushed is True

    def test_pr_url_defaults_to_none(self):
        result = CommitResult(sha="abc", branch="main", pushed=False)
        assert result.pr_url is None

    def test_pr_url_can_be_set(self):
        result = CommitResult(sha="abc", branch="main", pushed=True, pr_url="https://github.com/pr/1")
        assert result.pr_url == "https://github.com/pr/1"

    def test_is_frozen(self):
        result = CommitResult(sha="abc", branch="main", pushed=False)
        with pytest.raises((AttributeError, TypeError)):
            result.sha = "different"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# GitConfig
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GC_OK, reason="git_client import failed")
class TestGitConfig:
    def test_default_enabled_false(self):
        cfg = GitConfig()
        assert cfg.enabled is False

    def test_default_mode_direct_commit(self):
        cfg = GitConfig()
        assert cfg.mode == "direct_commit"

    def test_default_base_branch_main(self):
        cfg = GitConfig()
        assert cfg.base_branch == "main"

    def test_default_push_false(self):
        cfg = GitConfig()
        assert cfg.push is False

    def test_default_strict_clean_true(self):
        cfg = GitConfig()
        assert cfg.strict_clean is True

    def test_custom_author_name(self):
        cfg = GitConfig(author_name="My Bot")
        assert cfg.author_name == "My Bot"

    def test_branch_prefix_in_defaults(self):
        cfg = GitConfig()
        assert "dsl" in cfg.branch_prefix or "edit" in cfg.branch_prefix

    def test_github_token_default_empty(self):
        cfg = GitConfig()
        assert cfg.github_token == ""

# ---------------------------------------------------------------------------
# GitClientError
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GC_OK, reason="git_client import failed")
class TestGitClientError:
    def test_is_runtime_error(self):
        assert issubclass(GitClientError, RuntimeError)

    def test_can_be_raised(self):
        with pytest.raises(GitClientError):
            raise GitClientError("test error")

    def test_message_preserved(self):
        try:
            raise GitClientError("specific message")
        except GitClientError as e:
            assert "specific message" in str(e)
