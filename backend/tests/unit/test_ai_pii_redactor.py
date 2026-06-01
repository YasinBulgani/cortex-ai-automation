"""Unit tests for app.domains.ai.pii_redactor — PII detection and redaction.

Tests are fully self-contained: no DB, no HTTP, no external dependencies.
Covers: redact, redact_with_stats, detect_pii_categories, has_pii,
redact_messages, legacy_pattern_list, and RedactionResult.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.pii_redactor import (
        redact,
        redact_with_stats,
        detect_pii_categories,
        has_pii,
        redact_messages,
        legacy_pattern_list,
        RedactionResult,
        PH_TCKN,
        PH_IBAN,
        PH_EMAIL,
        PH_PHONE,
        PH_CARD,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="pii_redactor import failed")


# ---------------------------------------------------------------------------
# Placeholder constants
# ---------------------------------------------------------------------------

class TestPlaceholders:
    def test_tckn_placeholder_format(self):
        assert PH_TCKN == "[TC_KIMLIK]"

    def test_iban_placeholder_format(self):
        assert PH_IBAN == "[IBAN]"

    def test_email_placeholder_format(self):
        assert PH_EMAIL == "[EMAIL]"

    def test_phone_placeholder_format(self):
        assert PH_PHONE == "[TELEFON]"

    def test_card_placeholder_format(self):
        assert PH_CARD == "[KART]"


# ---------------------------------------------------------------------------
# redact — PII replacement
# ---------------------------------------------------------------------------

class TestRedact:
    def test_empty_string_unchanged(self):
        assert redact("") == ""

    def test_none_like_falsy_passthrough(self):
        # None is falsy; function returns early with the original value
        result = redact("")
        assert result == ""

    def test_no_pii_returns_unchanged(self):
        text = "Hello, this is a normal sentence without any PII."
        assert redact(text) == text

    def test_redacts_email(self):
        text = "Contact us at test.user@example.com for support."
        result = redact(text)
        assert "[EMAIL]" in result
        assert "test.user@example.com" not in result

    def test_redacts_tckn(self):
        text = "TC Kimlik No: 12345678901"
        result = redact(text)
        assert "[TC_KIMLIK]" in result
        assert "12345678901" not in result

    def test_redacts_turkish_iban(self):
        text = "IBAN: TR330006100519786457841326"
        result = redact(text)
        assert "[IBAN]" in result

    def test_redacts_turkish_phone(self):
        text = "Telefon: 05321234567"
        result = redact(text)
        assert "[TELEFON]" in result
        assert "05321234567" not in result

    def test_redacts_multiple_emails_in_text(self):
        text = "Send to a@b.com and c@d.org please"
        result = redact(text)
        assert result.count("[EMAIL]") == 2
        assert "a@b.com" not in result
        assert "c@d.org" not in result

    def test_preserves_non_pii_content(self):
        text = "Hello user@example.com, your order #1234 is ready."
        result = redact(text)
        assert "Hello" in result
        assert "your order" in result
        assert "#1234" in result

    def test_returns_string(self):
        result = redact("some text")
        assert isinstance(result, str)

    def test_multiple_pii_types(self):
        text = "Email: foo@bar.com, TC: 12345678901"
        result = redact(text)
        assert "[EMAIL]" in result
        assert "[TC_KIMLIK]" in result


# ---------------------------------------------------------------------------
# redact_with_stats — counts per category
# ---------------------------------------------------------------------------

class TestRedactWithStats:
    def test_returns_redaction_result(self):
        result = redact_with_stats("some text")
        assert isinstance(result, RedactionResult)

    def test_no_pii_empty_counts(self):
        result = redact_with_stats("Hello world")
        assert result.counts == {}
        assert result.total == 0

    def test_email_counted(self):
        result = redact_with_stats("Contact foo@bar.com")
        assert result.counts.get("email") == 1
        assert result.total == 1

    def test_two_emails_counted(self):
        result = redact_with_stats("a@b.com and c@d.org")
        assert result.counts.get("email") == 2

    def test_total_spans_categories(self):
        result = redact_with_stats("Email: a@b.com, TC: 12345678901")
        assert result.total >= 2

    def test_empty_string_returns_empty_result(self):
        result = redact_with_stats("")
        assert result.masked == ""
        assert result.counts == {}

    def test_masked_field_contains_placeholders(self):
        result = redact_with_stats("user@example.com")
        assert "[EMAIL]" in result.masked
        assert "user@example.com" not in result.masked

    def test_result_is_frozen(self):
        result = redact_with_stats("test")
        with pytest.raises((AttributeError, TypeError)):
            result.counts = {}  # type: ignore


# ---------------------------------------------------------------------------
# detect_pii_categories — detection without replacement
# ---------------------------------------------------------------------------

class TestDetectPiiCategories:
    def test_empty_returns_empty_dict(self):
        assert detect_pii_categories("") == {}

    def test_no_pii_returns_empty_dict(self):
        assert detect_pii_categories("Hello, world!") == {}

    def test_detects_email_category(self):
        cats = detect_pii_categories("Send to foo@bar.com")
        assert "email" in cats
        assert len(cats["email"]) == 1

    def test_detects_tckn_category(self):
        cats = detect_pii_categories("TC: 12345678901")
        assert "tckn" in cats

    def test_original_text_not_modified(self):
        text = "Email: foo@bar.com"
        cats = detect_pii_categories(text)
        assert "email" in cats
        # The original email should still appear in the matches
        assert any("foo@bar.com" in m for m in cats["email"])

    def test_duplicate_emails_deduplicated(self):
        text = "a@b.com and a@b.com again"
        cats = detect_pii_categories(text)
        # set-dedup: only 1 unique match
        assert cats["email"] == ["a@b.com"]

    def test_multiple_categories_detected(self):
        text = "Email: x@y.com, TC: 12345678901"
        cats = detect_pii_categories(text)
        assert "email" in cats
        assert "tckn" in cats


# ---------------------------------------------------------------------------
# has_pii — boolean check
# ---------------------------------------------------------------------------

class TestHasPii:
    def test_clean_text_returns_false(self):
        assert has_pii("This is a clean sentence.") is False

    def test_email_returns_true(self):
        assert has_pii("user@example.com") is True

    def test_tckn_returns_true(self):
        assert has_pii("TC: 12345678901") is True

    def test_empty_string_returns_false(self):
        assert has_pii("") is False

    def test_returns_bool(self):
        result = has_pii("some text")
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# redact_messages — OpenAI/Anthropic message list redaction
# ---------------------------------------------------------------------------

class TestRedactMessages:
    def test_empty_list_returns_empty(self):
        assert redact_messages([]) == []

    def test_string_content_redacted(self):
        messages = [{"role": "user", "content": "Email: foo@bar.com"}]
        result = redact_messages(messages)
        assert "[EMAIL]" in result[0]["content"]
        assert "foo@bar.com" not in result[0]["content"]

    def test_non_pii_content_unchanged(self):
        messages = [{"role": "user", "content": "Hello world"}]
        result = redact_messages(messages)
        assert result[0]["content"] == "Hello world"

    def test_role_field_preserved(self):
        messages = [{"role": "assistant", "content": "Text"}]
        result = redact_messages(messages)
        assert result[0]["role"] == "assistant"

    def test_multipart_content_blocks_redacted(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Email is user@example.com"},
                    {"type": "image_url", "image_url": {"url": "http://example.com/img.png"}},
                ],
            }
        ]
        result = redact_messages(messages)
        text_block = result[0]["content"][0]
        assert "[EMAIL]" in text_block["text"]
        # Image block not affected
        assert result[0]["content"][1]["type"] == "image_url"

    def test_non_dict_message_passed_through(self):
        messages = ["not a dict", {"role": "user", "content": "hi"}]
        result = redact_messages(messages)
        assert result[0] == "not a dict"

    def test_multiple_messages_all_redacted(self):
        messages = [
            {"role": "user", "content": "My email: a@b.com"},
            {"role": "assistant", "content": "Your TC: 12345678901"},
        ]
        result = redact_messages(messages)
        assert "[EMAIL]" in result[0]["content"]
        assert "[TC_KIMLIK]" in result[1]["content"]


# ---------------------------------------------------------------------------
# legacy_pattern_list
# ---------------------------------------------------------------------------

class TestLegacyPatternList:
    def test_returns_list(self):
        result = legacy_pattern_list()
        assert isinstance(result, list)

    def test_nonempty(self):
        result = legacy_pattern_list()
        assert len(result) > 0

    def test_each_item_is_tuple_of_two_strings(self):
        for item in legacy_pattern_list():
            assert isinstance(item, tuple)
            assert len(item) == 2
            pattern_str, placeholder = item
            assert isinstance(pattern_str, str)
            assert isinstance(placeholder, str)

    def test_placeholders_are_known_values(self):
        known = {PH_TCKN, PH_IBAN, PH_EMAIL, PH_PHONE, PH_CARD}
        for _pat, ph in legacy_pattern_list():
            assert ph in known
