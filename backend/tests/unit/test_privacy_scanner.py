"""Privacy scanner unit testleri — TCKN/IBAN checksum + k-anon + l-div."""
from __future__ import annotations

import pytest

from app.domains.ai_synthetic_data.privacy_scanner import (
    ScanConfig,
    compute_k_anonymity,
    compute_l_diversity,
    is_valid_iban,
    is_valid_tckn,
    scan_dataset,
)


# ── TCKN checksum ────────────────────────────────────────────────────────


class TestTCKN:
    def test_known_valid_tckn(self) -> None:
        # Math'e uygun bir sentetik: 10000000146 (0 ile başladığı için invalid olmalı)
        # Bilinen valid bir test TCKN üretmek için elle hesap:
        # d1..d9 = 1,2,3,4,5,6,7,8,9
        # odd = 1+3+5+7+9 = 25 ; even = 2+4+6+8 = 20
        # d10 = (25*7 - 20) mod 10 = (175-20) mod 10 = 155 mod 10 = 5
        # d11 = (1+2+3+4+5+6+7+8+9+5) mod 10 = 50 mod 10 = 0
        assert is_valid_tckn("12345678950")

    def test_leading_zero_invalid(self) -> None:
        assert is_valid_tckn("01234567895") is False

    def test_wrong_length(self) -> None:
        assert is_valid_tckn("123") is False
        assert is_valid_tckn("123456789012") is False

    def test_non_digit(self) -> None:
        assert is_valid_tckn("1234567890A") is False

    def test_fails_checksum_10(self) -> None:
        # d10 bilerek yanlış: 12345678940 (doğru 50)
        assert is_valid_tckn("12345678940") is False

    def test_fails_checksum_11(self) -> None:
        # d11 bilerek yanlış: 12345678957 (doğru 50)
        assert is_valid_tckn("12345678957") is False

    def test_random_inputs_mostly_invalid(self) -> None:
        # 1000 rastgele 11-digit içinden 1'den azı gerçek valid olabilir
        import random

        random.seed(0)
        valid_count = 0
        for _ in range(1000):
            s = str(random.randint(10_000_000_000, 99_999_999_999))
            if is_valid_tckn(s):
                valid_count += 1
        # İstatistiksel beklenti ~10 (100'de 1), 20'den az olmalı
        assert valid_count < 20


# ── IBAN mod-97 ──────────────────────────────────────────────────────────


class TestIBAN:
    def test_known_valid_de_iban(self) -> None:
        # DE89370400440532013000 — Wikipedia örnek valid IBAN
        assert is_valid_iban("DE89 3704 0044 0532 0130 00") is True

    def test_known_valid_gb_iban(self) -> None:
        # GB82WEST12345698765432
        assert is_valid_iban("GB82 WEST 1234 5698 7654 32") is True

    def test_invalid_checksum(self) -> None:
        # Son digit'i bozarsak
        assert is_valid_iban("DE89 3704 0044 0532 0130 01") is False

    def test_too_short(self) -> None:
        assert is_valid_iban("DE89") is False

    def test_too_long(self) -> None:
        assert is_valid_iban("DE" + "0" * 50) is False

    def test_lowercase_normalized(self) -> None:
        assert is_valid_iban("de89 3704 0044 0532 0130 00") is True

    def test_non_alnum_rejected(self) -> None:
        assert is_valid_iban("DE89-3704-0044-0532-0130-00") is False


# ── k-anonymity ──────────────────────────────────────────────────────────


class TestKAnonymity:
    def test_empty(self) -> None:
        assert compute_k_anonymity([], quasi_identifiers=["a"]) == 0

    def test_homogeneous_dataset(self) -> None:
        rows = [{"a": 1, "b": 2}] * 5
        assert compute_k_anonymity(rows, quasi_identifiers=["a", "b"]) == 5

    def test_mixed_groups(self) -> None:
        rows = [
            {"age": 30, "city": "Ankara"},
            {"age": 30, "city": "Ankara"},
            {"age": 25, "city": "İzmir"},
        ]
        assert compute_k_anonymity(rows, quasi_identifiers=["age", "city"]) == 1

    def test_larger_minimum(self) -> None:
        rows = [
            {"age": 30, "city": "Ankara"},
            {"age": 30, "city": "Ankara"},
            {"age": 30, "city": "Ankara"},
            {"age": 25, "city": "İzmir"},
            {"age": 25, "city": "İzmir"},
        ]
        # Gruplar: (30,Ankara)=3, (25,İzmir)=2 → k=2
        assert compute_k_anonymity(rows, quasi_identifiers=["age", "city"]) == 2


# ── l-diversity ──────────────────────────────────────────────────────────


class TestLDiversity:
    def test_single_group_all_same_sensitive(self) -> None:
        rows = [{"age": 30, "disease": "X"}] * 5
        assert compute_l_diversity(
            rows, quasi_identifiers=["age"], sensitive_attr="disease"
        ) == 1

    def test_single_group_two_sensitive_values(self) -> None:
        rows = [
            {"age": 30, "disease": "X"},
            {"age": 30, "disease": "Y"},
        ]
        assert compute_l_diversity(
            rows, quasi_identifiers=["age"], sensitive_attr="disease"
        ) == 2

    def test_multiple_groups_min_wins(self) -> None:
        rows = [
            {"age": 30, "disease": "X"},
            {"age": 30, "disease": "Y"},
            {"age": 30, "disease": "Z"},  # (30) → 3 farklı
            {"age": 40, "disease": "X"},  # (40) → 1
        ]
        assert compute_l_diversity(
            rows, quasi_identifiers=["age"], sensitive_attr="disease"
        ) == 1


# ── scan_dataset ─────────────────────────────────────────────────────────


def test_scan_synthetic_banking_passes() -> None:
    # Sentetik: TCKN'ler rastgele 11-digit (valid oranı <%5), IBAN'lar rastgele
    rows = [
        {"tckn": str(10_000_000_000 + i), "age": 30, "city": "Ankara", "disease": "X" if i % 2 == 0 else "Y"}
        for i in range(10)
    ]
    config = ScanConfig(
        tckn_columns=["tckn"],
        quasi_identifiers=["age", "city"],
        sensitive_attrs=["disease"],
        k_min=5,
        l_min=2,
    )
    report = scan_dataset(dataset_id="ds-1", rows=rows, config=config)
    # TCKN'ler çoğunlukla invalid — passed; k=10, l=2 → passed
    tckn_check = next(c for c in report.checks if c.name == "tckn.tckn")
    assert tckn_check.status == "passed"
    k_check = next(c for c in report.checks if c.name == "k_anonymity")
    assert k_check.status == "passed"
    l_check = next(c for c in report.checks if c.name == "l_diversity.disease")
    assert l_check.status == "passed"
    assert report.overall_passed is True


def test_scan_detects_real_tckn_leak() -> None:
    # Hepsi gerçek valid TCKN → leak şüphesi, FAIL
    rows = [{"tckn": "12345678950"}] * 20  # valid checksum
    config = ScanConfig(tckn_columns=["tckn"])
    report = scan_dataset(dataset_id="ds-leak", rows=rows, config=config)
    tckn_check = next(c for c in report.checks if c.name == "tckn.tckn")
    assert tckn_check.status == "failed"
    assert tckn_check.metric_value == 1.0
    assert report.overall_passed is False


def test_scan_detects_real_iban_leak() -> None:
    rows = [{"iban": "DE89 3704 0044 0532 0130 00"}] * 10
    config = ScanConfig(iban_columns=["iban"])
    report = scan_dataset(dataset_id="ds-iban", rows=rows, config=config)
    iban = next(c for c in report.checks if c.name == "iban.iban")
    assert iban.status == "failed"
    assert iban.metric_value == 1.0


def test_scan_low_k_anonymity_fails() -> None:
    # Her quasi-identifier tek satır → k=1 < k_min=5 → fail
    rows = [
        {"age": i, "city": f"C{i}"}
        for i in range(10)
    ]
    config = ScanConfig(
        quasi_identifiers=["age", "city"], sensitive_attrs=[], k_min=5
    )
    report = scan_dataset(dataset_id="ds-k1", rows=rows, config=config)
    k = next(c for c in report.checks if c.name == "k_anonymity")
    assert k.status == "failed"
    assert k.metric_value == 1.0


def test_scan_empty_column_skipped() -> None:
    rows = [{"tckn": None} for _ in range(5)]
    config = ScanConfig(tckn_columns=["tckn"])
    report = scan_dataset(dataset_id="ds-empty", rows=rows, config=config)
    tckn = next(c for c in report.checks if c.name == "tckn.tckn")
    assert tckn.status == "skipped"
