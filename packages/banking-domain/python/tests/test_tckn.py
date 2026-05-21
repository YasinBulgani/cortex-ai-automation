"""TCKN validator + generator tests — MERNIS algoritması."""

from __future__ import annotations

import pytest

from banking_domain import validate_tckn, generate_tckn, mask_tckn


# ═══════════════════════════════════════════════════════════════════════════
# MERNIS golden vectors — algoritma doğrulaması için kesin doğru TCKN'ler
# ═══════════════════════════════════════════════════════════════════════════

VALID_TCKNS = [
    "10000000146",   # Nüfus Müdürlüğü test TCKN
    "11111111110",   # Test
    "22222222220",
    "33333333330",
    "44444444440",
    "55555555550",
    "66666666660",
    "77777777770",
    "88888888880",
    "99999999990",
]


INVALID_TCKNS = [
    None,
    "",
    "00000000000",    # İlk hane 0
    "1234567890",     # 10 hane
    "123456789012",   # 12 hane
    "12345678901",    # Geçersiz checksum
    "ABCDEFGHIJK",    # Harfli
    "0000000000A",    # Sonuna harf
    "12345 78901",    # Boşluk
]


class TestTcknValidation:
    @pytest.mark.parametrize("tckn", VALID_TCKNS)
    def test_valid_tckns(self, tckn):
        assert validate_tckn(tckn), f"Should be valid: {tckn}"

    @pytest.mark.parametrize("tckn", INVALID_TCKNS)
    def test_invalid_tckns(self, tckn):
        assert not validate_tckn(tckn), f"Should be invalid: {tckn!r}"

    def test_first_digit_zero(self):
        # 0 ile başlar → geçersiz
        assert not validate_tckn("01234567890")

    def test_non_digit_chars(self):
        assert not validate_tckn("1234567A901")

    def test_correct_length_wrong_checksum(self):
        # 11 hane ama 10. ve 11. hane doğru değil
        assert not validate_tckn("12345678911")


class TestTcknGeneration:
    def test_generate_is_valid(self):
        for _ in range(100):
            tckn = generate_tckn()
            assert validate_tckn(tckn), f"Generated invalid: {tckn}"

    def test_generate_first_digit_non_zero(self):
        for _ in range(50):
            tckn = generate_tckn()
            assert tckn[0] != "0"

    def test_generate_all_digits(self):
        for _ in range(50):
            tckn = generate_tckn()
            assert tckn.isdigit()
            assert len(tckn) == 11


class TestTcknMask:
    def test_default_mask(self):
        assert mask_tckn("12345678901") == "123******01"

    def test_custom_visible(self):
        assert mask_tckn("12345678901", visible_start=2, visible_end=3) == "12******901"

    def test_mask_returns_empty_for_invalid(self):
        # Yanlış uzunluk — olduğu gibi (veya boş) döner
        result = mask_tckn("123")
        assert result == "123"
