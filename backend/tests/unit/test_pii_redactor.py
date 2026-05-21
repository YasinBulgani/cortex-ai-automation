"""PII Redactor — LLM-boundary redaksiyon testleri (Dalga 0)."""
from __future__ import annotations

import pytest

from app.domains.ai.pii_redactor import (
    PH_CARD,
    PH_EMAIL,
    PH_IBAN,
    PH_PHONE,
    PH_TCKN,
    detect_pii_categories,
    has_pii,
    redact,
    redact_messages,
    redact_with_stats,
)


class TestBasicRedaction:
    def test_tckn(self):
        assert redact("TC no: 12345678901") == "TC no: [TC_KIMLIK]"

    def test_iban_with_spaces(self):
        text = "IBAN: TR33 0006 1005 1978 6457 8413 26 dir"
        assert "[IBAN]" in redact(text)
        assert "TR33" not in redact(text)

    def test_iban_lowercase_tr(self):
        assert "[IBAN]" in redact("tr330006100519786457841326")

    def test_email(self):
        assert redact("Mail: ali@example.com") == "Mail: [EMAIL]"

    def test_phone_tr(self):
        for phone in ["0532 123 45 67", "05321234567", "+90 532 123 45 67"]:
            masked = redact(f"Tel: {phone}")
            assert PH_PHONE in masked, f"{phone} redakte edilmedi: {masked}"

    def test_card(self):
        # Kredi kartı: 16 rakam, boşluk veya tire ile
        text = "Kart: 4532 1234 5678 9012"
        assert PH_CARD in redact(text)

    def test_no_pii_returns_untouched(self):
        text = "Bu tamamen temiz bir metin."
        assert redact(text) == text

    def test_empty_input(self):
        assert redact("") == ""
        assert redact(None) is None  # type: ignore


class TestMultiPII:
    def test_multiple_categories_in_one_text(self):
        text = (
            "Ali TC 12345678901 numaralı müşteri, IBAN TR330006100519786457841326 "
            "hesabından 0532 111 22 33 telefonuyla ali@bank.com adresine iletişim."
        )
        masked = redact(text)
        assert "[TC_KIMLIK]" in masked
        assert "[IBAN]" in masked
        assert "[TELEFON]" in masked
        assert "[EMAIL]" in masked
        assert "12345678901" not in masked
        assert "TR33" not in masked
        assert "0532" not in masked
        assert "ali@" not in masked


class TestStats:
    def test_counts_per_category(self):
        text = "tckn1: 12345678901 tckn2: 98765432109 email: a@b.co"
        result = redact_with_stats(text)
        assert result.counts.get("tckn", 0) == 2
        assert result.counts.get("email", 0) == 1
        assert result.total == 3
        assert "[TC_KIMLIK]" in result.masked

    def test_empty_stats(self):
        result = redact_with_stats("no pii here")
        assert result.counts == {}
        assert result.total == 0


class TestDetect:
    def test_detect_categories(self):
        found = detect_pii_categories("TC: 12345678901, mail: a@b.co")
        assert "tckn" in found
        assert "email" in found
        assert "12345678901" in found["tckn"]

    def test_has_pii_true(self):
        assert has_pii("TC: 12345678901") is True

    def test_has_pii_false(self):
        assert has_pii("lorem ipsum") is False


class TestMessages:
    def test_redact_messages_str_content(self):
        msgs = [
            {"role": "system", "content": "sen bir asistansın"},
            {"role": "user", "content": "TC 12345678901 ile giriş yap"},
        ]
        out = redact_messages(msgs)
        assert out[0]["content"] == "sen bir asistansın"
        assert "[TC_KIMLIK]" in out[1]["content"]
        assert "12345678901" not in out[1]["content"]

    def test_redact_messages_multipart(self):
        msgs = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "TCKN: 12345678901"},
                    {"type": "image_url", "image_url": {"url": "https://x"}},
                ],
            }
        ]
        out = redact_messages(msgs)
        assert out[0]["content"][0]["text"] == "TCKN: [TC_KIMLIK]"
        # image block değişmeden kalmalı
        assert out[0]["content"][1]["type"] == "image_url"

    def test_redact_messages_preserves_non_content_fields(self):
        msgs = [{"role": "user", "content": "TC 12345678901", "name": "ali"}]
        out = redact_messages(msgs)
        assert out[0]["role"] == "user"
        assert out[0]["name"] == "ali"
        assert out[0]["content"] == "TC [TC_KIMLIK]"


class TestPlaceholdersStable:
    """Placeholder format LOCK'lu — engine ve diğer testler bu değerlere güveniyor."""

    def test_placeholders_are_expected(self):
        assert PH_TCKN == "[TC_KIMLIK]"
        assert PH_IBAN == "[IBAN]"
        assert PH_EMAIL == "[EMAIL]"
        assert PH_PHONE == "[TELEFON]"
        assert PH_CARD == "[KART]"
