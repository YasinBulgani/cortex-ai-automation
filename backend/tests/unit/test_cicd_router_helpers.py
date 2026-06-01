"""Unit tests for CiCD router pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/cicd/router.py:
    _summarize, _normalize_ref, _extract_commit_sha, _extract_branch,
    _extract_author, _serialize_json, _keywords_from_path, _tenant_of
"""

from __future__ import annotations

import json
import types
from datetime import datetime, timezone

import pytest

from app.domains.cicd.router import (
    _extract_author,
    _extract_branch,
    _extract_commit_sha,
    _keywords_from_path,
    _normalize_ref,
    _serialize_json,
    _summarize,
    _tenant_of,
)


# ── _summarize ────────────────────────────────────────────────────────────────


class TestSummarize:
    def test_extracts_known_keys(self) -> None:
        payload = {"ref": "refs/heads/main", "repository": "repo", "extra": "ignored"}
        result = _summarize(payload)
        assert result["ref"] == "refs/heads/main"
        assert result["repository"] == "repo"
        assert "extra" not in result

    def test_ignores_absent_keys(self) -> None:
        payload = {"ref": "main"}
        result = _summarize(payload)
        assert "action" not in result
        assert "status" not in result

    def test_empty_payload_returns_empty_dict(self) -> None:
        assert _summarize({}) == {}

    def test_returns_dict(self) -> None:
        assert isinstance(_summarize({"ref": "x"}), dict)

    def test_all_known_keys_extracted(self) -> None:
        payload = {
            "ref": "r", "repository": "rep", "action": "a",
            "status": "s", "conclusion": "c", "pipeline": "p",
            "build_url": "u", "commit": "abc", "branch": "b",
            "tag": "v1.0", "object_kind": "push", "state": "success",
        }
        result = _summarize(payload)
        assert len(result) == 12

    def test_extra_keys_not_included(self) -> None:
        payload = {"ref": "x", "unknown_key": "value", "another": 123}
        result = _summarize(payload)
        assert set(result.keys()) == {"ref"}


# ── _normalize_ref ────────────────────────────────────────────────────────────


class TestNormalizeRef:
    def test_strips_refs_heads_prefix(self) -> None:
        assert _normalize_ref("refs/heads/main") == "main"

    def test_strips_refs_tags_prefix(self) -> None:
        assert _normalize_ref("refs/tags/v1.2.3") == "v1.2.3"

    def test_plain_branch_unchanged(self) -> None:
        assert _normalize_ref("feature/my-feature") == "feature/my-feature"

    def test_empty_string_returns_empty(self) -> None:
        assert _normalize_ref("") == ""

    def test_returns_string(self) -> None:
        assert isinstance(_normalize_ref("refs/heads/dev"), str)

    def test_nested_branch_name(self) -> None:
        result = _normalize_ref("refs/heads/feat/some/nested")
        assert result == "feat/some/nested"

    def test_tag_with_dots(self) -> None:
        result = _normalize_ref("refs/tags/v2.0.0-rc1")
        assert result == "v2.0.0-rc1"


# ── _extract_commit_sha ───────────────────────────────────────────────────────


class TestExtractCommitSha:
    def test_extracts_from_after(self) -> None:
        payload = {"after": "abc123"}
        assert _extract_commit_sha(payload) == "abc123"

    def test_extracts_from_checkout_sha(self) -> None:
        payload = {"checkout_sha": "def456"}
        assert _extract_commit_sha(payload) == "def456"

    def test_extracts_from_sha(self) -> None:
        payload = {"sha": "ghi789"}
        assert _extract_commit_sha(payload) == "ghi789"

    def test_extracts_from_commit(self) -> None:
        payload = {"commit": "jkl012"}
        assert _extract_commit_sha(payload) == "jkl012"

    def test_extracts_from_workflow_run(self) -> None:
        payload = {"workflow_run": {"head_sha": "mno345"}}
        assert _extract_commit_sha(payload) == "mno345"

    def test_empty_payload_returns_empty(self) -> None:
        assert _extract_commit_sha({}) == ""

    def test_truncates_at_64_chars(self) -> None:
        sha = "a" * 80
        result = _extract_commit_sha({"after": sha})
        assert len(result) == 64

    def test_prefers_after_over_sha(self) -> None:
        payload = {"after": "preferred", "sha": "secondary"}
        assert _extract_commit_sha(payload) == "preferred"

    def test_returns_string(self) -> None:
        assert isinstance(_extract_commit_sha({}), str)


# ── _extract_branch ───────────────────────────────────────────────────────────


class TestExtractBranch:
    def test_extracts_from_branch(self) -> None:
        payload = {"branch": "main"}
        assert _extract_branch(payload) == "main"

    def test_strips_refs_heads_from_ref(self) -> None:
        payload = {"ref": "refs/heads/feature/test"}
        assert _extract_branch(payload) == "feature/test"

    def test_empty_payload_returns_empty(self) -> None:
        assert _extract_branch({}) == ""

    def test_extracts_from_workflow_run(self) -> None:
        payload = {"workflow_run": {"head_branch": "staging"}}
        assert _extract_branch(payload) == "staging"

    def test_truncates_at_128_chars(self) -> None:
        branch = "b" * 200
        result = _extract_branch({"branch": branch})
        assert len(result) == 128

    def test_returns_string(self) -> None:
        assert isinstance(_extract_branch({}), str)


# ── _extract_author ───────────────────────────────────────────────────────────


class TestExtractAuthor:
    def test_extracts_sender_login(self) -> None:
        payload = {"sender": {"login": "octocat"}}
        assert _extract_author(payload) == "octocat"

    def test_extracts_user_username(self) -> None:
        payload = {"user_username": "gitlabuser"}
        assert _extract_author(payload) == "gitlabuser"

    def test_extracts_pusher_name(self) -> None:
        payload = {"pusher": {"name": "dev-user"}}
        assert _extract_author(payload) == "dev-user"

    def test_extracts_author_name(self) -> None:
        payload = {"author": {"name": "John Doe"}}
        assert _extract_author(payload) == "John Doe"

    def test_empty_payload_returns_empty(self) -> None:
        assert _extract_author({}) == ""

    def test_truncates_at_256_chars(self) -> None:
        name = "n" * 300
        result = _extract_author({"user_username": name})
        assert len(result) == 256

    def test_returns_string(self) -> None:
        assert isinstance(_extract_author({}), str)


# ── _serialize_json ───────────────────────────────────────────────────────────


class TestSerializeJson:
    def test_serializes_dict(self) -> None:
        result = _serialize_json({"key": "value"})
        assert json.loads(result) == {"key": "value"}

    def test_serializes_list(self) -> None:
        result = _serialize_json([1, 2, 3])
        assert json.loads(result) == [1, 2, 3]

    def test_datetime_serialized_as_string(self) -> None:
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = _serialize_json({"dt": dt})
        parsed = json.loads(result)
        assert isinstance(parsed["dt"], str)

    def test_returns_string(self) -> None:
        assert isinstance(_serialize_json({}), str)

    def test_empty_dict(self) -> None:
        assert _serialize_json({}) == "{}"


# ── _keywords_from_path ───────────────────────────────────────────────────────


class TestKeywordsFromPath:
    def test_extracts_meaningful_parts(self) -> None:
        result = _keywords_from_path("src/auth/login.py")
        assert "auth" in result
        assert "login" in result

    def test_skips_src(self) -> None:
        result = _keywords_from_path("src/auth/login.py")
        assert "src" not in result

    def test_skips_test_dir(self) -> None:
        # "tests" and "test" are in the skip set; "unit" is kept (not a skip word)
        result = _keywords_from_path("tests/unit/auth_test.py")
        assert "tests" not in result
        assert "test" not in result

    def test_skips_file_extensions(self) -> None:
        result = _keywords_from_path("auth/login.py")
        assert "py" not in result

    def test_skips_short_parts(self) -> None:
        # Parts of length <= 2 should be excluded
        result = _keywords_from_path("a/b/authentication.py")
        assert "a" not in result
        assert "b" not in result

    def test_empty_path_returns_list(self) -> None:
        result = _keywords_from_path("")
        assert isinstance(result, list)

    def test_returns_list(self) -> None:
        assert isinstance(_keywords_from_path("auth/login.py"), list)

    def test_lowercase_output(self) -> None:
        result = _keywords_from_path("Auth/Login.py")
        for kw in result:
            assert kw == kw.lower()

    def test_handles_backslash_separator(self) -> None:
        result = _keywords_from_path("src\\auth\\login.py")
        assert "auth" in result or "login" in result

    def test_skips_index_and_main(self) -> None:
        result = _keywords_from_path("src/index.ts")
        assert "index" not in result
        assert "src" not in result


# ── _tenant_of ────────────────────────────────────────────────────────────────


class TestTenantOf:
    def test_returns_tenant_id_from_attribute(self) -> None:
        user = types.SimpleNamespace(tenant_id="tenant-abc")
        assert _tenant_of(user) == "tenant-abc"

    def test_falls_back_when_no_tenant_id(self) -> None:
        user = types.SimpleNamespace()
        result = _tenant_of(user)
        # Default fallback UUID
        assert result == "00000000-0000-0000-0000-000000000001"

    def test_falls_back_when_tenant_id_empty(self) -> None:
        user = types.SimpleNamespace(tenant_id="")
        result = _tenant_of(user)
        assert result == "00000000-0000-0000-0000-000000000001"

    def test_falls_back_when_tenant_id_none(self) -> None:
        user = types.SimpleNamespace(tenant_id=None)
        result = _tenant_of(user)
        assert result == "00000000-0000-0000-0000-000000000001"

    def test_returns_string(self) -> None:
        user = types.SimpleNamespace(tenant_id="t123")
        assert isinstance(_tenant_of(user), str)
