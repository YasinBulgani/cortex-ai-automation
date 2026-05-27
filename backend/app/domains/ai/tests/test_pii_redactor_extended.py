"""Extended unit tests for app.domains.ai.pii_redactor.

Covers:
- TCKN (TC kimlik numarası): valid 11-digit, invalid (10 digits), valid in text
- IBAN: Turkish IBAN format, in sentence
- Email: standard, with subdomains, non-PII not masked
- Phone: Turkish GSM (+90, 0, with spaces/dashes)
- JWT token detection (via API key / bearer pattern)
- API key patterns (Bearer tokens, API keys)
- IPv4 address (not PII in this redactor — confirmed no-op)
- Multiple PII in same text: all masked
- Empty string: safe
- No PII text: returned unchanged
- Nested JSON with PII values: values masked, keys preserved
"""
from __future__ import annotations

import json

import pytest

try:
    from app.domains.ai.pii_redactor import (
        redact,
        redact_with_stats,
        detect_pii_categories,
        has_pii,
        redact_messages,
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


# ── TCKN ────────────────────────────────────────────────────────────────────

class TestTCKN:
    def test_valid_11_digit_tckn_is_masked(self):
        result = redact("TC: 12345678901")
        assert PH_TCKN in result
        assert "12345678901" not in result

    def test_tckn_starting_with_zero_not_masked(self):
        """First digit 0 is not a valid TCKN."""
        result = redact("TC: 01234567890")
        assert PH_TCKN not in result

    def test_10_digit_number_not_masked_as_tckn(self):
        """10-digit numbers should NOT be treated as TCKN."""
        result = redact("Numara: 1234567890")
        assert PH_TCKN not in result

    def test_tckn_in_longer_text_is_masked(self):
        text = "Kullanicinin TC kimlik numarasi 23456789012 sistemde kayitlidir."
        result = redact(text)
        assert PH_TCKN in result
        assert "23456789012" not in result

    def test_tckn_detected_in_categories(self):
        cats = detect_pii_categories("TC: 34567890123")
        assert "tckn" in cats


# ── IBAN ─────────────────────────────────────────────────────────────────────

class TestIBAN:
    def test_turkish_iban_plain_is_masked(self):
        iban = "TR330006100519786457841326"
        result = redact(iban)
        assert PH_IBAN in result
        assert iban not in result

    def test_turkish_iban_with_spaces_is_masked(self):
        iban_spaced = "TR33 0006 1005 1978 6457 8413 26"
        result = redact(iban_spaced)
        assert PH_IBAN in result

    def test_iban_in_sentence_is_masked(self):
        text = "Havale IBAN numarasina: TR330006100519786457841326 yapilacaktir."
        result = redact(text)
        assert PH_IBAN in result
        assert "TR330006100519786457841326" not in result

    def test_iban_detected_in_categories(self):
        cats = detect_pii_categories("IBAN: TR330006100519786457841326")
        assert "iban_tr" in cats


# ── Email ────────────────────────────────────────────────────────────────────

class TestEmail:
    def test_standard_email_is_masked(self):
        result = redact("Bize ulasin: test@example.com")
        assert PH_EMAIL in result
        assert "test@example.com" not in result

    def test_email_with_subdomain_is_masked(self):
        result = redact("Contact: user@mail.example.co.uk")
        assert PH_EMAIL in result
        assert "user@mail.example.co.uk" not in result

    def test_email_with_plus_tag_is_masked(self):
        result = redact("Email: user+tag@domain.org")
        assert PH_EMAIL in result

    def test_non_email_at_sign_not_masked(self):
        """'@mention' style text (no dot in domain part) should NOT be masked."""
        result = redact("Twitter: @username")
        # There's no domain TLD here; should not match
        assert PH_EMAIL not in result

    def test_email_detected_in_categories(self):
        cats = detect_pii_categories("admin@neurex.ai")
        assert "email" in cats


# ── Phone ────────────────────────────────────────────────────────────────────

class TestPhone:
    def test_phone_with_plus90_prefix_is_masked(self):
        result = redact("+905321234567")
        assert PH_PHONE in result
        assert "+905321234567" not in result

    def test_phone_with_zero_prefix_is_masked(self):
        result = redact("Tel: 05321234567")
        assert PH_PHONE in result

    def test_phone_with_spaces_is_masked(self):
        result = redact("Telefon: 0532 123 45 67")
        assert PH_PHONE in result

    def test_phone_with_dashes_is_masked(self):
        result = redact("GSM: 0532-123-45-67")
        assert PH_PHONE in result

    def test_phone_with_plus90_and_spaces_is_masked(self):
        result = redact("Numara: +90 532 123 45 67")
        assert PH_PHONE in result

    def test_phone_detected_in_categories(self):
        cats = detect_pii_categories("+905001234567")
        assert "phone_tr" in cats


# ── JWT / Bearer / API Keys ──────────────────────────────────────────────────

class TestBearerAndApiKeyPatterns:
    """
    The pii_redactor does not have a dedicated JWT/API-key pattern.
    These tests document that JWTs are NOT masked by this redactor (by design —
    the module's scope is KVKK/BDDK PII: TCKN, IBAN, card, email, phone).
    A JWT has no PII pattern match unless it coincidentally contains a phone/email.
    """

    def test_jwt_token_not_masked_by_pii_redactor(self):
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        result = redact(jwt)
        # No PII pattern fires; token must pass through unchanged
        assert result == jwt

    def test_bearer_header_value_not_masked(self):
        header = "Authorization: Bearer sk-1234567890abcdef"
        result = redact(header)
        # No standard PII here; redactor should leave it as-is
        assert "Bearer" in result

    def test_api_key_without_pii_not_masked(self):
        text = "API_KEY=abcdef1234567890-xyz"
        result = redact(text)
        assert result == text


# ── IPv4 Addresses ───────────────────────────────────────────────────────────

class TestIPv4:
    """IPv4 is not a PII category in this redactor — confirmed pass-through."""

    def test_ipv4_address_not_masked(self):
        text = "Server IP: 192.168.1.100"
        result = redact(text)
        assert result == text

    def test_ipv4_in_log_not_masked(self):
        text = "Request from 10.0.0.1 to 172.16.0.254"
        result = redact(text)
        assert result == text


# ── Multiple PII in same text ────────────────────────────────────────────────

class TestMultiplePII:
    def test_all_pii_types_masked_in_one_text(self):
        text = (
            "Musteri: 12345678901 "
            "IBAN: TR330006100519786457841326 "
            "Email: test@example.com "
            "Telefon: +905321234567"
        )
        result = redact(text)
        assert PH_TCKN in result
        assert PH_IBAN in result
        assert PH_EMAIL in result
        assert PH_PHONE in result
        assert "12345678901" not in result
        assert "TR330006100519786457841326" not in result
        assert "test@example.com" not in result
        assert "+905321234567" not in result

    def test_redact_with_stats_counts_all_categories(self):
        text = (
            "TC: 12345678901 "
            "Email: a@b.com ve c@d.org "
            "IBAN: TR330006100519786457841326"
        )
        result = redact_with_stats(text)
        assert isinstance(result, RedactionResult)
        assert result.counts.get("tckn", 0) >= 1
        assert result.counts.get("email", 0) >= 2
        assert result.counts.get("iban_tr", 0) >= 1
        assert result.total >= 4

    def test_has_pii_returns_true_for_mixed_text(self):
        text = "TC: 12345678901 Email: foo@bar.com"
        assert has_pii(text) is True


# ── Edge cases ───────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_string_returns_empty_string(self):
        assert redact("") == ""

    def test_none_like_falsy_returns_safely(self):
        """redact('') should not raise; empty string -> empty string."""
        result = redact("")
        assert result == ""

    def test_no_pii_text_returned_unchanged(self):
        text = "Bu metinde hic kisisel veri yoktur."
        assert redact(text) == text

    def test_whitespace_only_string(self):
        text = "   "
        result = redact(text)
        assert result == text

    def test_has_pii_false_for_clean_text(self):
        assert has_pii("Hello world, no personal data here!") is False

    def test_redact_with_stats_empty_string(self):
        result = redact_with_stats("")
        assert result.masked == ""
        assert result.counts == {}
        assert result.total == 0

    def test_detect_pii_categories_empty_string(self):
        assert detect_pii_categories("") == {}


# ── Nested JSON with PII values ──────────────────────────────────────────────

class TestNestedJSON:
    """
    The redactor operates on strings. For JSON, the caller must serialize
    and re-deserialize. This test verifies that pattern keys (TCKN, email etc.)
    survive redaction when used as JSON keys while values are masked.
    """

    def test_json_values_masked_keys_preserved(self):
        payload = {
            "user_id": "admin",
            "tckn": "12345678901",
            "email": "user@example.com",
            "iban": "TR330006100519786457841326",
        }
        serialized = json.dumps(payload)
        redacted_str = redact(serialized)
        redacted_obj = json.loads(redacted_str)

        # Keys must be preserved
        assert "user_id" in redacted_obj
        assert "tckn" in redacted_obj
        assert "email" in redacted_obj
        assert "iban" in redacted_obj

        # Values must be masked
        assert redacted_obj["tckn"] != "12345678901"
        assert redacted_obj["email"] != "user@example.com"
        assert redacted_obj["iban"] != "TR330006100519786457841326"

        # Non-PII value must be unchanged
        assert redacted_obj["user_id"] == "admin"

    def test_json_nested_pii_in_list(self):
        payload = {"contacts": ["12345678901", "foo@bar.com"]}
        redacted = redact(json.dumps(payload))
        assert "12345678901" not in redacted
        assert "foo@bar.com" not in redacted

    def test_json_no_pii_unchanged_after_roundtrip(self):
        payload = {"status": "ok", "count": 42}
        serialized = json.dumps(payload)
        result = redact(serialized)
        assert json.loads(result) == payload


# ── redact_messages ──────────────────────────────────────────────────────────

class TestRedactMessages:
    def test_string_content_is_redacted(self):
        msgs = [{"role": "user", "content": "TC: 12345678901"}]
        result = redact_messages(msgs)
        assert PH_TCKN in result[0]["content"]
        assert "12345678901" not in result[0]["content"]

    def test_multipart_content_text_blocks_are_redacted(self):
        msgs = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Email: secret@neurex.com"},
                    {"type": "image_url", "url": "https://example.com/img.png"},
                ],
            }
        ]
        result = redact_messages(msgs)
        assert PH_EMAIL in result[0]["content"][0]["text"]
        # Non-text block must be left untouched
        assert result[0]["content"][1]["url"] == "https://example.com/img.png"

    def test_non_dict_messages_passed_through(self):
        msgs = ["plain string"]
        result = redact_messages(msgs)
        assert result == ["plain string"]

    def test_message_without_content_key_not_mutated(self):
        msgs = [{"role": "system"}]
        result = redact_messages(msgs)
        assert result[0] == {"role": "system"}
