"""Luhn algorithm + card number generator tests."""

from __future__ import annotations

import pytest

from banking_domain import (
    validate_luhn,
    luhn_check_digit,
    generate_card_number,
    generate_test_card,
    mask_card_number,
    BIN_TEST_CARDS,
)


# Bilinen Luhn-valid test kart no'ları (kamuya açık test numaraları)
VALID_CARDS = [
    "4242424242424242",  # Stripe test VISA
    "4012888888881881",  # Visa test
    "5555555555554444",  # Mastercard test
    "5105105105105100",  # Mastercard test
    "378282246310005",   # AMEX test (15 hane)
    "371449635398431",   # AMEX test
    "6011111111111117",  # Discover test
    "9792000000000000003",  # Troy test (19 hane)
]


INVALID_CARDS = [
    "",
    None,
    "1234567890123456",  # Rastgele dijit
    "4242424242424241",  # Son dijit yanlış (+1)
    "ABCD",
    "123",                # Çok kısa
    "42424242424242424242",  # Çok uzun (20 hane)
]


class TestLuhnValidation:
    @pytest.mark.parametrize("card", VALID_CARDS)
    def test_valid_cards(self, card):
        assert validate_luhn(card), f"Should be valid: {card}"

    @pytest.mark.parametrize("card", INVALID_CARDS)
    def test_invalid_cards(self, card):
        assert not validate_luhn(card), f"Should be invalid: {card!r}"

    def test_with_spaces(self):
        # Boşluklu da OK (dijitleri extract eder)
        assert validate_luhn("4242 4242 4242 4242")

    def test_with_dashes(self):
        assert validate_luhn("4242-4242-4242-4242")


class TestCheckDigit:
    def test_known_check_digits(self):
        # 4242424242424242 → body 424242424242424, check 2
        assert luhn_check_digit("424242424242424") == 2

    def test_mastercard(self):
        # 5555555555554444 → body 555555555555444, check 4
        assert luhn_check_digit("555555555555444") == 4


class TestCardGeneration:
    def test_generate_default_length(self):
        for _ in range(20):
            card = generate_card_number("454360", length=16)
            assert len(card) == 16
            assert validate_luhn(card)
            assert card.startswith("454360")

    def test_generate_amex(self):
        for _ in range(10):
            card = generate_card_number("378282", length=15)
            assert len(card) == 15
            assert validate_luhn(card)

    def test_generate_test_card_visa(self):
        for _ in range(10):
            card = generate_test_card("VISA")
            assert len(card) == 16
            assert validate_luhn(card)
            assert card.startswith("454360")

    def test_generate_test_card_amex(self):
        card = generate_test_card("AMEX")
        assert len(card) == 15
        assert validate_luhn(card)

    def test_generate_test_card_troy(self):
        card = generate_test_card("TROY")
        assert validate_luhn(card)
        assert card.startswith("979200")

    def test_reject_unknown_network(self):
        with pytest.raises(ValueError):
            generate_test_card("UNKNOWN")

    def test_reject_invalid_length(self):
        with pytest.raises(ValueError):
            generate_card_number("454360", length=10)
        with pytest.raises(ValueError):
            generate_card_number("454360", length=25)

    def test_reject_non_digit_bin(self):
        with pytest.raises(ValueError):
            generate_card_number("ABC123", length=16)


class TestCardMasking:
    def test_default_mask(self):
        # 1234567812345678 → 123456******5678
        assert mask_card_number("1234567812345678") == "123456******5678"

    def test_mask_with_spaces(self):
        # Boşluk temizle + maskele
        assert mask_card_number("1234 5678 1234 5678") == "123456******5678"

    def test_mask_custom_visible(self):
        result = mask_card_number("1234567812345678", visible_first=4, visible_last=4)
        assert result == "1234********5678"

    def test_mask_amex(self):
        # 15 hane
        assert mask_card_number("378282246310005") == "378282*****0005"

    def test_mask_empty(self):
        assert mask_card_number("") == ""


class TestBinTable:
    def test_all_networks_have_bins(self):
        assert "VISA" in BIN_TEST_CARDS
        assert "MASTERCARD" in BIN_TEST_CARDS
        assert "TROY" in BIN_TEST_CARDS
        assert "AMEX" in BIN_TEST_CARDS

    def test_bins_are_digits(self):
        for bin_ in BIN_TEST_CARDS.values():
            assert bin_.isdigit()
