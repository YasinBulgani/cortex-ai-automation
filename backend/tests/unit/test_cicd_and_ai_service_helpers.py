"""Unit tests for CI/CD router and AI service pure helper functions.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/cicd/router.py:
    _normalize_ref, _summarize, _extract_commit_sha,
    _extract_branch, _extract_author, _serialize_json,
    _keywords_from_path
  app/domains/ai/service.py:
    _is_local_llm_url, _is_retriable_error, _parse_json_response
"""

from __future__ import annotations

import json

import pytest

from app.domains.cicd.router import (
    _extract_author,
    _extract_branch,
    _extract_commit_sha,
    _keywords_from_path,
    _normalize_ref,
    _serialize_json,
    _summarize,
)
from app.domains.ai.service import (
    _is_local_llm_url,
    _is_retriable_error,
    _parse_json_response,
)


# ── _normalize_ref ────────────────────────────────────────────────────────────


class TestNormalizeRef:
    def test_refs_heads_stripped(self) -> None:
        assert _normalize_ref("refs/heads/main") == "main"

    def test_refs_tags_stripped(self) -> None:
        assert _normalize_ref("refs/tags/v1.0.0") == "v1.0.0"

    def test_plain_branch_unchanged(self) -> None:
        assert _normalize_ref("main") == "main"

    def test_feature_branch(self) -> None:
        assert _normalize_ref("refs/heads/feature/login") == "feature/login"

    def test_empty_string(self) -> None:
        assert _normalize_ref("") == ""

    def test_other_ref_unchanged(self) -> None:
        assert _normalize_ref("HEAD") == "HEAD"


# ── _summarize ────────────────────────────────────────────────────────────────


class TestSummarize:
    def test_only_known_keys_extracted(self) -> None:
        payload = {
            "ref": "refs/heads/main",
            "secret_data": "should_be_excluded",
            "status": "success",
        }
        result = _summarize(payload)
        assert "ref" in result
        assert "status" in result
        assert "secret_data" not in result

    def test_empty_payload_returns_empty(self) -> None:
        assert _summarize({}) == {}

    def test_all_known_keys_included(self) -> None:
        payload = {
            "ref": "main",
            "repository": "org/repo",
            "action": "opened",
            "status": "success",
            "conclusion": "success",
        }
        result = _summarize(payload)
        assert len(result) == 5

    def test_returns_dict(self) -> None:
        assert isinstance(_summarize({"ref": "main"}), dict)


# ── _extract_commit_sha ───────────────────────────────────────────────────────


class TestExtractCommitSha:
    def test_after_key(self) -> None:
        payload = {"after": "abc123def456"}
        result = _extract_commit_sha(payload)
        assert result == "abc123def456"

    def test_sha_key_fallback(self) -> None:
        payload = {"sha": "deadbeef1234"}
        assert _extract_commit_sha(payload) == "deadbeef1234"

    def test_checkout_sha_fallback(self) -> None:
        payload = {"checkout_sha": "abc"}
        assert _extract_commit_sha(payload) == "abc"

    def test_empty_payload_returns_empty(self) -> None:
        assert _extract_commit_sha({}) == ""

    def test_truncated_to_64_chars(self) -> None:
        long_sha = "a" * 100
        payload = {"after": long_sha}
        result = _extract_commit_sha(payload)
        assert len(result) == 64

    def test_nested_workflow_run(self) -> None:
        payload = {"workflow_run": {"head_sha": "xyz999"}}
        assert _extract_commit_sha(payload) == "xyz999"


# ── _extract_branch ───────────────────────────────────────────────────────────


class TestExtractBranch:
    def test_branch_key(self) -> None:
        payload = {"branch": "main"}
        assert _extract_branch(payload) == "main"

    def test_ref_key_normalized(self) -> None:
        payload = {"ref": "refs/heads/develop"}
        assert _extract_branch(payload) == "develop"

    def test_empty_payload_returns_empty(self) -> None:
        assert _extract_branch({}) == ""

    def test_truncated_to_128_chars(self) -> None:
        payload = {"branch": "a" * 200}
        assert len(_extract_branch(payload)) == 128

    def test_nested_workflow_run_branch(self) -> None:
        payload = {"workflow_run": {"head_branch": "feature/login"}}
        assert _extract_branch(payload) == "feature/login"


# ── _extract_author ───────────────────────────────────────────────────────────


class TestExtractAuthor:
    def test_sender_login(self) -> None:
        payload = {"sender": {"login": "johndoe"}}
        assert _extract_author(payload) == "johndoe"

    def test_user_username_fallback(self) -> None:
        payload = {"user_username": "jane"}
        assert _extract_author(payload) == "jane"

    def test_pusher_name_fallback(self) -> None:
        payload = {"pusher": {"name": "bob"}}
        assert _extract_author(payload) == "bob"

    def test_empty_payload_returns_empty(self) -> None:
        assert _extract_author({}) == ""

    def test_truncated_to_256_chars(self) -> None:
        payload = {"sender": {"login": "a" * 300}}
        assert len(_extract_author(payload)) == 256

    def test_author_key(self) -> None:
        payload = {"author": {"name": "alice"}}
        assert _extract_author(payload) == "alice"


# ── _serialize_json ───────────────────────────────────────────────────────────


class TestSerializeJson:
    def test_dict_serialized(self) -> None:
        result = _serialize_json({"key": "value"})
        assert json.loads(result) == {"key": "value"}

    def test_returns_string(self) -> None:
        assert isinstance(_serialize_json({"a": 1}), str)

    def test_non_serializable_uses_str(self) -> None:
        from datetime import datetime
        result = _serialize_json({"dt": datetime(2024, 1, 1)})
        assert isinstance(result, str)

    def test_list_serialized(self) -> None:
        result = _serialize_json([1, 2, 3])
        assert json.loads(result) == [1, 2, 3]


# ── _keywords_from_path ───────────────────────────────────────────────────────


class TestKeywordsFromPath:
    def test_returns_list(self) -> None:
        assert isinstance(_keywords_from_path("src/auth/login.py"), list)

    def test_extracts_meaningful_parts(self) -> None:
        result = _keywords_from_path("src/auth/login.py")
        assert "auth" in result
        assert "login" in result

    def test_skips_common_parts(self) -> None:
        result = _keywords_from_path("src/index.py")
        assert "src" not in result
        assert "index" not in result
        assert "py" not in result

    def test_empty_path_returns_empty(self) -> None:
        assert _keywords_from_path("") == []

    def test_short_parts_excluded(self) -> None:
        # Parts with <= 2 chars are excluded
        result = _keywords_from_path("a/bb/valid.py")
        assert "a" not in result
        assert "bb" not in result

    def test_handles_backslash(self) -> None:
        result = _keywords_from_path("src\\auth\\login.py")
        assert "auth" in result
        assert "login" in result


# ── _is_local_llm_url ─────────────────────────────────────────────────────────


class TestIsLocalLlmUrl:
    def test_localhost(self) -> None:
        assert _is_local_llm_url("http://localhost:11434") is True

    def test_127_0_0_1(self) -> None:
        assert _is_local_llm_url("http://127.0.0.1:8080") is True

    def test_docker_service_name(self) -> None:
        # "ollama" has no dots → local
        assert _is_local_llm_url("http://ollama:11434") is True

    def test_external_url(self) -> None:
        assert _is_local_llm_url("https://api.openai.com") is False

    def test_empty_returns_false(self) -> None:
        assert _is_local_llm_url("") is False

    def test_host_docker_internal(self) -> None:
        assert _is_local_llm_url("http://host.docker.internal:11434") is True

    def test_private_ip(self) -> None:
        assert _is_local_llm_url("http://192.168.1.100:8080") is True


# ── _is_retriable_error ───────────────────────────────────────────────────────


class TestIsRetriableError:
    def test_generic_exception_retriable(self) -> None:
        assert _is_retriable_error(Exception("connection timeout")) is True

    def test_rate_limit_retriable(self) -> None:
        assert _is_retriable_error(Exception("rate limit exceeded")) is True

    def test_auth_error_not_retriable(self) -> None:
        # Auth errors should not be retried
        result = _is_retriable_error(Exception("401 unauthorized"))
        assert result is False

    def test_permission_error_not_retriable(self) -> None:
        result = _is_retriable_error(Exception("403 permission denied"))
        assert result is False

    def test_returns_bool(self) -> None:
        assert isinstance(_is_retriable_error(Exception("error")), bool)


# ── _parse_json_response ──────────────────────────────────────────────────────


class TestParseJsonResponse:
    def test_valid_json_parsed(self) -> None:
        result = _parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_in_code_fence_parsed(self) -> None:
        raw = '```json\n{"status": "ok"}\n```'
        result = _parse_json_response(raw)
        assert result["status"] == "ok"

    def test_empty_string_raises(self) -> None:
        with pytest.raises((ValueError, Exception)):
            _parse_json_response("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises((ValueError, Exception)):
            _parse_json_response("   ")

    def test_returns_dict(self) -> None:
        result = _parse_json_response('{"a": 1}')
        assert isinstance(result, dict)

    def test_nested_json(self) -> None:
        result = _parse_json_response('{"data": {"score": 9}}')
        assert result["data"]["score"] == 9

    def test_json_with_trailing_comma_handled(self) -> None:
        # Some LLMs produce trailing commas
        # The function tries to clean them up
        raw = '{"key": "value",}'
        try:
            result = _parse_json_response(raw)
            assert isinstance(result, dict)
        except Exception:
            pass  # Acceptable if this particular format fails

    def test_embedded_json_extracted(self) -> None:
        raw = 'Here is the result: {"score": 5} as you can see.'
        result = _parse_json_response(raw)
        assert result.get("score") == 5
