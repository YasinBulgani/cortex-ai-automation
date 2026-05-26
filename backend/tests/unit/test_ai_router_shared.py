"""Unit tests for app.domains.ai.router_shared — pure helpers.

Tests are fully self-contained: no DB, no HTTP.
Covers: _estimate_tokens, raise_structured_internal_error.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.router_shared import (
        _estimate_tokens,
        raise_structured_internal_error,
    )
    from fastapi import HTTPException
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="router_shared import failed")


# ---------------------------------------------------------------------------
# _estimate_tokens
# ---------------------------------------------------------------------------

class TestEstimateTokens:
    def test_empty_returns_zero(self):
        assert _estimate_tokens() == 0

    def test_single_part(self):
        # "abc" = 3 chars / 3 = 1 token
        assert _estimate_tokens("abc") == 1

    def test_multiple_parts_concatenated(self):
        # "abc" + "def" = 6 chars / 3 = 2 tokens
        assert _estimate_tokens("abc", "def") == 2

    def test_falsy_parts_skipped(self):
        # None and "" are falsy → skipped
        assert _estimate_tokens("abc", None, "", "def") == 2

    def test_none_only_returns_zero(self):
        assert _estimate_tokens(None) == 0

    def test_zero_only_returns_zero(self):
        # 0 is falsy → skipped
        assert _estimate_tokens(0) == 0

    def test_integer_parts_converted(self):
        # str(100) = "100" = 3 chars → 1 token
        assert _estimate_tokens(100) == 1

    def test_minimum_zero(self):
        # Short text may give 0 (floor division)
        assert _estimate_tokens("ab") == 0

    def test_returns_int(self):
        assert isinstance(_estimate_tokens("hello world"), int)

    def test_long_text_proportional(self):
        # 30 chars / 3 = 10 tokens
        assert _estimate_tokens("a" * 30) == 10

    def test_non_negative(self):
        assert _estimate_tokens("x") >= 0


# ---------------------------------------------------------------------------
# raise_structured_internal_error
# ---------------------------------------------------------------------------

class TestRaiseStructuredInternalError:
    def test_raises_http_exception(self):
        with pytest.raises(HTTPException):
            raise_structured_internal_error("ERR_CODE", "Something failed", ValueError("boom"))

    def test_status_code_500(self):
        with pytest.raises(HTTPException) as exc_info:
            raise_structured_internal_error("ERR_CODE", "msg", RuntimeError("x"))
        assert exc_info.value.status_code == 500

    def test_detail_has_code(self):
        with pytest.raises(HTTPException) as exc_info:
            raise_structured_internal_error("MY_CODE", "message", ValueError("error"))
        detail = exc_info.value.detail
        assert detail["code"] == "MY_CODE"

    def test_detail_has_message(self):
        with pytest.raises(HTTPException) as exc_info:
            raise_structured_internal_error("C", "my message", ValueError("e"))
        assert exc_info.value.detail["message"] == "my message"

    def test_detail_has_error_type(self):
        with pytest.raises(HTTPException) as exc_info:
            raise_structured_internal_error("C", "m", ValueError("e"))
        assert exc_info.value.detail["error_type"] == "ValueError"

    def test_detail_has_details_truncated_to_300(self):
        long_msg = "x" * 400
        with pytest.raises(HTTPException) as exc_info:
            raise_structured_internal_error("C", "m", RuntimeError(long_msg))
        details = exc_info.value.detail["details"]
        assert len(details) <= 300

    def test_empty_exception_message_falls_back_to_class_name(self):
        with pytest.raises(HTTPException) as exc_info:
            raise_structured_internal_error("C", "m", ValueError(""))
        details = exc_info.value.detail["details"]
        assert "ValueError" in details

    def test_detail_is_dict(self):
        with pytest.raises(HTTPException) as exc_info:
            raise_structured_internal_error("C", "m", Exception("e"))
        assert isinstance(exc_info.value.detail, dict)
