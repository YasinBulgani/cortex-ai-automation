"""BIC, VKN, telefon validator tests."""

from __future__ import annotations

import pytest

from banking_domain import (
    validate_bic, bic_country_code, bic_bank_code,
    validate_vkn, generate_vkn,
    validate_phone_tr, generate_phone_tr, normalize_phone_tr,
    format_phone_tr, get_operator, mask_phone_tr,
)


# ═══════════════════════════════════════════════════════════════════════════
# BIC (ISO 9362)
# ═══════════════════════════════════════════════════════════════════════════


class TestBic:
    @pytest.mark.parametrize("bic", [
        "AKBKTRIS",         # Akbank (8)
        "AKBKTRISXXX",      # Akbank primary branch (11)
        "TGBATRIS",         # Garanti
        "ISBKTRIS",         # İş Bankası
        "DEUTDEFF",         # Deutsche Bank
        "DEUTDEFF500",      # Deutsche Bank branch
    ])
    def test_valid_bics(self, bic):
        assert validate_bic(bic)

    @pytest.mark.parametrize("bic", [
        None, "",
        "akbktris",    # Küçük harf de valid — upper'a çevirir
        "TGBATRI",     # 7 hane
        "TGBATRISXX",  # 10 hane
        "TGB4TRIS",    # İlk 4 harfli değil (dijit var)
        "TGBA1RIS",    # Country kodu dijitli
    ])
    def test_invalid_bics(self, bic):
        if bic and bic.upper() == "AKBKTRIS":
            # Küçük harf büyük harfe çevrilip geçerli olmalı
            assert validate_bic(bic)
        else:
            assert not validate_bic(bic), f"Should be invalid: {bic!r}"

    def test_country_code(self):
        assert bic_country_code("AKBKTRIS") == "TR"
        assert bic_country_code("DEUTDEFF") == "DE"

    def test_bank_code(self):
        assert bic_bank_code("AKBKTRIS") == "AKBK"
        assert bic_bank_code("TGBATRIS") == "TGBA"


# ═══════════════════════════════════════════════════════════════════════════
# VKN
# ═══════════════════════════════════════════════════════════════════════════


class TestVkn:
    def test_generate_is_valid(self):
        for _ in range(50):
            vkn = generate_vkn()
            assert validate_vkn(vkn)
            assert len(vkn) == 10
            assert vkn.isdigit()

    def test_invalid_length(self):
        assert not validate_vkn("123456789")    # 9 hane
        assert not validate_vkn("12345678901")  # 11 hane

    def test_non_digit(self):
        assert not validate_vkn("123456789A")

    def test_none(self):
        assert not validate_vkn(None)
        assert not validate_vkn("")


# ═══════════════════════════════════════════════════════════════════════════
# Telefon
# ═══════════════════════════════════════════════════════════════════════════


class TestPhoneTr:
    @pytest.mark.parametrize("phone", [
        "+90 530 123 45 67",
        "+905301234567",
        "0530 123 45 67",
        "05301234567",
        "5301234567",
        "+90-530-123-45-67",
    ])
    def test_normalize_variations(self, phone):
        normalized = normalize_phone_tr(phone)
        assert normalized == "+905301234567"

    def test_normalize_invalid(self):
        assert normalize_phone_tr(None) is None
        assert normalize_phone_tr("") is None
        assert normalize_phone_tr("abc") is None
        assert normalize_phone_tr("123") is None

    def test_validate_mobile(self):
        assert validate_phone_tr("+905301234567")  # Turkcell
        assert validate_phone_tr("+905401234567")  # Vodafone
        assert validate_phone_tr("+905551234567")  # Türk Telekom
        assert not validate_phone_tr("+902121234567")  # Sabit hat (mobile_only=True)

    def test_validate_non_mobile_allowed(self):
        # mobile_only=False ise sabit hatta da OK
        assert validate_phone_tr("+902121234567", mobile_only=False)

    def test_generate_operator(self):
        for _ in range(10):
            tc = generate_phone_tr("turkcell")
            assert get_operator(tc) == "turkcell"

            vf = generate_phone_tr("vodafone")
            assert get_operator(vf) == "vodafone"

            tt = generate_phone_tr("turktelekom")
            assert get_operator(tt) == "turktelekom"

    def test_generate_default(self):
        for _ in range(20):
            phone = generate_phone_tr()
            assert validate_phone_tr(phone)

    def test_format_international(self):
        result = format_phone_tr("+905301234567", style="international")
        assert result == "+90 530 123 45 67"

    def test_format_national(self):
        result = format_phone_tr("+905301234567", style="national")
        assert result == "0530 123 45 67"

    def test_format_plain(self):
        result = format_phone_tr("+905301234567", style="plain")
        assert result == "5301234567"

    def test_mask(self):
        masked = mask_phone_tr("+905301234567")
        assert "530" in masked
        assert "67" in masked
        assert "*" in masked
        # Ortadaki kısım gizli olmalı
        assert "123" not in masked
