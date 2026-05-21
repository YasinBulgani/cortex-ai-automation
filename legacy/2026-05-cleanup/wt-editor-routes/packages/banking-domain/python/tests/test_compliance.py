"""Compliance tests — KVKK, AML, BDDK."""

from __future__ import annotations

import pytest

from banking_domain import (
    DataClass, classify_field, redact_value, redact_dict,
    SUSPICIOUS_TRANSACTION_THRESHOLD_TRY,
    is_reportable_transaction, AmlFlag, check_aml_flags,
    calculate_credit_limit, DTI_LIMITS,
    check_capital_adequacy_ratio, CAR_MINIMUM,
)
from banking_domain.compliance.kvkk import detect_pii, redact_pii_in_text


# ═══════════════════════════════════════════════════════════════════════════
# KVKK
# ═══════════════════════════════════════════════════════════════════════════


class TestKvkkClassification:
    def test_identity_fields(self):
        assert classify_field("tckn") == DataClass.IDENTITY
        assert classify_field("vkn") == DataClass.IDENTITY
        assert classify_field("mersis") == DataClass.IDENTITY

    def test_personal_fields(self):
        assert classify_field("phone") == DataClass.PERSONAL
        assert classify_field("email") == DataClass.PERSONAL
        assert classify_field("first_name") == DataClass.PERSONAL

    def test_financial_fields(self):
        assert classify_field("iban") == DataClass.FINANCIAL
        assert classify_field("card_number") == DataClass.FINANCIAL
        assert classify_field("income") == DataClass.FINANCIAL

    def test_sensitive_fields(self):
        assert classify_field("religion") == DataClass.SENSITIVE
        assert classify_field("health_condition") == DataClass.SENSITIVE

    def test_unknown_field_is_public(self):
        assert classify_field("some_random_field") == DataClass.PUBLIC


class TestKvkkRedaction:
    def test_tckn_redaction(self):
        result = redact_value("12345678901", DataClass.IDENTITY)
        assert result.startswith("123")
        assert result.endswith("01")
        assert "*" in result

    def test_iban_redaction(self):
        iban = "TR330006100519786457841326"
        result = redact_value(iban, DataClass.FINANCIAL)
        assert result.startswith("TR33")
        assert result.endswith("26")
        assert "*" in result

    def test_card_redaction(self):
        card = "4242424242424242"
        result = redact_value(card, DataClass.FINANCIAL)
        assert result.startswith("424242")
        assert result.endswith("4242")
        assert "*" in result

    def test_phone_redaction(self):
        result = redact_value("+905301234567", DataClass.PERSONAL)
        assert "530" in result
        assert "67" in result
        assert "*" in result

    def test_email_redaction(self):
        result = redact_value("john.doe@example.com", DataClass.PERSONAL)
        assert "@example.com" in result
        assert "*" in result

    def test_sensitive_fully_redacted(self):
        assert redact_value("Herhangi bir değer", DataClass.SENSITIVE) == "[REDACTED]"

    def test_public_unchanged(self):
        assert redact_value("ABC A.Ş.", DataClass.PUBLIC) == "ABC A.Ş."


class TestKvkkRedactDict:
    def test_nested_redaction(self):
        data = {
            "tckn": "12345678901",
            "first_name": "Ahmet",
            "iban": "TR330006100519786457841326",
            "company_name": "ABC Ltd",  # PUBLIC
        }
        result = redact_dict(data)
        assert "*" in result["tckn"]
        assert "*" in result["first_name"] or result["first_name"] == "Ahmet" and False
        assert "*" in result["iban"]
        assert result["company_name"] == "ABC Ltd"

    def test_nested_dict(self):
        data = {
            "customer": {
                "tckn": "12345678901",
                "company_name": "ABC",  # public (classification'da yok)
            }
        }
        result = redact_dict(data)
        assert "*" in result["customer"]["tckn"]
        # company_name PUBLIC sınıfında, değişmemeli
        assert result["customer"]["company_name"] == "ABC"


class TestPiiDetection:
    def test_detect_tckn_in_text(self):
        text = "Müşteri TCKN: 12345678901 ile işlem yapıldı."
        found = detect_pii(text)
        assert "tckn" in found

    def test_detect_iban_in_text(self):
        text = "Hesap: TR33 0006 1005 1978 6457 8413 26"
        found = detect_pii(text)
        assert "iban_tr" in found

    def test_detect_email(self):
        text = "İletişim: test@example.com"
        found = detect_pii(text)
        assert "email" in found

    def test_redact_text(self):
        text = "TCKN 12345678901 ve +90 530 123 45 67"
        redacted = redact_pii_in_text(text)
        assert "12345678901" not in redacted
        assert "[REDACTED_TCKN]" in redacted

    def test_no_pii(self):
        text = "Sadece sıradan bir metin."
        assert detect_pii(text) == {}


# ═══════════════════════════════════════════════════════════════════════════
# AML (MASAK)
# ═══════════════════════════════════════════════════════════════════════════


class TestAmlReporting:
    def test_above_threshold(self):
        tx = {"amount": 25_000, "currency": "TRY", "type": "transfer"}
        assert is_reportable_transaction(tx)

    def test_below_threshold(self):
        tx = {"amount": 5_000, "currency": "TRY", "type": "transfer"}
        assert not is_reportable_transaction(tx)

    def test_cash_high(self):
        tx = {"amount": 80_000, "currency": "TRY", "type": "cash"}
        assert is_reportable_transaction(tx)

    def test_cross_border_wire(self):
        tx = {
            "amount": 400_000,  # ~$11.4K
            "currency": "TRY",
            "type": "wire",
            "is_cross_border": True,
        }
        assert is_reportable_transaction(tx)


class TestAmlFlags:
    def test_large_transaction_flag(self):
        tx = {"amount": 25_000, "currency": "TRY"}
        flags = check_aml_flags(tx)
        assert AmlFlag.LARGE_TRANSACTION in flags

    def test_round_dollar_flag(self):
        tx = {"amount": 100_000, "currency": "TRY"}
        flags = check_aml_flags(tx)
        assert AmlFlag.ROUND_DOLLAR in flags

    def test_structuring_suspect(self):
        # Eşiğin hemen altı (17K-20K arası)
        tx = {"amount": 18_500, "currency": "TRY"}
        flags = check_aml_flags(tx)
        assert AmlFlag.STRUCTURING_SUSPECT in flags

    def test_cumulative_limit(self):
        tx = {"amount": 30_000, "currency": "TRY"}
        flags = check_aml_flags(tx, daily_total=25_000)
        # 25K + 30K = 55K >= 50K → flag
        assert AmlFlag.CUMULATIVE_LIMIT in flags

    def test_unusual_pattern(self):
        # Müşteri ortalaması 500 iken 25000 işlem
        tx = {"amount": 25_000, "currency": "TRY"}
        flags = check_aml_flags(tx, customer_avg_amount=500)
        assert AmlFlag.UNUSUAL_PATTERN in flags

    def test_sanctions_match(self):
        tx = {"amount": 1000, "currency": "TRY"}
        flags = check_aml_flags(
            tx, counterparty_id="SANCTIONED_1", sanctions_list=["SANCTIONED_1"]
        )
        assert AmlFlag.SANCTIONS_MATCH in flags

    def test_cross_border(self):
        tx = {"amount": 5000, "currency": "TRY", "is_cross_border": True}
        flags = check_aml_flags(tx)
        assert AmlFlag.CROSS_BORDER in flags


# ═══════════════════════════════════════════════════════════════════════════
# BDDK
# ═══════════════════════════════════════════════════════════════════════════


class TestBddkCreditLimit:
    def test_retail_limit(self):
        # 20K aylık gelir, retail, diğer borç yok
        # DTI 0.50, 12 ay → 20K × 0.5 × 12 = 120K
        limit = calculate_credit_limit(20_000, "retail")
        assert limit == 120_000

    def test_affluent_higher_limit(self):
        # 100K gelir, affluent, DTI 0.6
        # 100K × 0.6 × 12 = 720K
        limit = calculate_credit_limit(100_000, "affluent")
        assert limit == 720_000

    def test_with_existing_debts(self):
        # 20K gelir, retail, 50K mevcut borç
        # Max 120K, available 120-50 = 70K
        limit = calculate_credit_limit(20_000, "retail", other_debts=50_000)
        assert limit == 70_000

    def test_zero_income_zero_limit(self):
        assert calculate_credit_limit(0, "retail") == 0.0

    def test_negative_available(self):
        # Borçlar zaten limiti aşıyor → 0
        limit = calculate_credit_limit(10_000, "retail", other_debts=100_000)
        assert limit == 0.0


class TestCapitalAdequacy:
    def test_compliant(self):
        # Tier1 100M + Tier2 50M = 150M / RWA 1000M = %15 >= %12
        ratio, compliant = check_capital_adequacy_ratio(100_000_000, 50_000_000, 1_000_000_000)
        assert compliant
        assert ratio == pytest.approx(0.15)

    def test_non_compliant(self):
        # %10 → fail
        ratio, compliant = check_capital_adequacy_ratio(50_000_000, 50_000_000, 1_000_000_000)
        assert not compliant
        assert ratio == pytest.approx(0.10)

    def test_zero_assets(self):
        ratio, compliant = check_capital_adequacy_ratio(100_000, 0, 0)
        assert ratio == 0.0
        assert not compliant

    def test_minimum_threshold(self):
        assert CAR_MINIMUM == 0.12
