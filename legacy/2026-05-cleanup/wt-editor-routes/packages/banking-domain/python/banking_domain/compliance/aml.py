"""
AML (Anti-Money Laundering) — MASAK 2006/55 sayılı Tebliğ.

Şüpheli işlem bildirim eşikleri ve AML bayrak kontrolleri.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
# MASAK eşikleri (2026 güncel)
# ═══════════════════════════════════════════════════════════════════════════

SUSPICIOUS_TRANSACTION_THRESHOLD_TRY: float = 20_000.0
"""Tek işlem için MASAK bildirim eşiği (TRY)."""

CUMULATIVE_DAILY_THRESHOLD_TRY: float = 50_000.0
"""Aynı hesaptan günlük toplam eşik (TRY)."""

INTERNATIONAL_WIRE_THRESHOLD_USD: float = 10_000.0
"""Uluslararası havale raporlama eşiği (USD)."""

CASH_TRANSACTION_THRESHOLD_TRY: float = 75_000.0
"""Nakit işlem raporlama eşiği (TRY)."""


# ═══════════════════════════════════════════════════════════════════════════
# AML Flag'leri
# ═══════════════════════════════════════════════════════════════════════════


class AmlFlag(str, Enum):
    """AML denetiminde tetiklenebilecek bayraklar."""

    LARGE_TRANSACTION = "large_transaction"         # Eşik üstü tek işlem
    CUMULATIVE_LIMIT = "cumulative_limit"           # Günlük toplam eşik
    STRUCTURING_SUSPECT = "structuring_suspect"     # Yapılandırma (parçalı transfer)
    RAPID_MOVEMENT = "rapid_movement"               # Hızlı para hareketi
    CROSS_BORDER = "cross_border"                   # Sınır ötesi
    HIGH_RISK_MCC = "high_risk_mcc"                 # Yüksek risk sektör (kumar, döviz)
    SANCTIONS_MATCH = "sanctions_match"             # Yaptırım listesi
    PEP_MATCH = "pep_match"                         # Politically Exposed Person
    UNUSUAL_PATTERN = "unusual_pattern"             # Müşteri profiline aykırı
    ROUND_DOLLAR = "round_dollar"                   # Tam yuvarlak tutar (100K, 500K)


@dataclass
class TransactionForAml:
    """AML kontrolü için minimum transaction data."""

    amount: float
    currency: str = "TRY"
    type: str = "transfer"  # transfer | cash | wire | pos | ...
    is_cross_border: bool = False
    counterparty_country: str | None = None
    mcc: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# Reporting decision
# ═══════════════════════════════════════════════════════════════════════════


def is_reportable_transaction(tx: TransactionForAml | dict) -> bool:
    """
    Tek bir işlem MASAK'a rapor edilmeli mi?
    """
    if isinstance(tx, dict):
        amount = float(tx.get("amount", 0))
        currency = tx.get("currency", "TRY")
        tx_type = tx.get("type", "transfer")
        is_cross_border = bool(tx.get("is_cross_border", False))
    else:
        amount = tx.amount
        currency = tx.currency
        tx_type = tx.type
        is_cross_border = tx.is_cross_border

    # TRY işlemler için 20K eşik
    if currency == "TRY" and amount >= SUSPICIOUS_TRANSACTION_THRESHOLD_TRY:
        return True

    # Nakit için 75K
    if tx_type == "cash" and currency == "TRY" and amount >= CASH_TRANSACTION_THRESHOLD_TRY:
        return True

    # Uluslararası wire için 10K USD
    if is_cross_border or tx_type == "wire":
        # USD eşiğini TL'ye çevir (~35:1 2026 kur)
        usd_equivalent = amount / 35.0 if currency == "TRY" else amount
        if currency == "USD":
            usd_equivalent = amount
        if usd_equivalent >= INTERNATIONAL_WIRE_THRESHOLD_USD:
            return True

    return False


# ═══════════════════════════════════════════════════════════════════════════
# AML Flag check
# ═══════════════════════════════════════════════════════════════════════════


def check_aml_flags(
    tx: TransactionForAml | dict,
    *,
    daily_total: float = 0.0,
    customer_avg_amount: float = 0.0,
    sanctions_list: list[str] | None = None,
    pep_list: list[str] | None = None,
    counterparty_id: str | None = None,
    high_risk_mccs: set[str] | None = None,
) -> list[AmlFlag]:
    """
    İşlem için tüm AML bayraklarını döndür.

    Args:
        tx: TransactionForAml veya dict
        daily_total: Bugünkü toplam işlem hacmi (TL)
        customer_avg_amount: Müşterinin ortalama işlem tutarı
        sanctions_list: Yaptırım altındaki kişi/firma ID'leri
        pep_list: PEP (politik önemli kişi) listesi
        counterparty_id: Karşı taraf ID'si
        high_risk_mccs: Yüksek risk MCC set'i
    """
    if isinstance(tx, dict):
        amount = float(tx.get("amount", 0))
        currency = tx.get("currency", "TRY")
        tx_type = tx.get("type", "transfer")
        is_cross_border = bool(tx.get("is_cross_border", False))
        mcc = tx.get("mcc")
    else:
        amount = tx.amount
        currency = tx.currency
        tx_type = tx.type
        is_cross_border = tx.is_cross_border
        mcc = tx.mcc

    flags: list[AmlFlag] = []

    # Large single transaction
    if currency == "TRY" and amount >= SUSPICIOUS_TRANSACTION_THRESHOLD_TRY:
        flags.append(AmlFlag.LARGE_TRANSACTION)

    # Cumulative daily
    if daily_total + amount >= CUMULATIVE_DAILY_THRESHOLD_TRY and currency == "TRY":
        flags.append(AmlFlag.CUMULATIVE_LIMIT)

    # Cross-border
    if is_cross_border:
        flags.append(AmlFlag.CROSS_BORDER)

    # High risk MCC
    if mcc and high_risk_mccs and mcc in high_risk_mccs:
        flags.append(AmlFlag.HIGH_RISK_MCC)

    # Round dollar (500, 1K, 5K, 10K, 50K, 100K gibi tam miktarlar)
    if amount > 0 and amount % 10_000 == 0 and amount >= 50_000:
        flags.append(AmlFlag.ROUND_DOLLAR)

    # Unusual pattern (müşteri ortalamasının 10 katından fazla)
    if customer_avg_amount > 0 and amount > customer_avg_amount * 10:
        flags.append(AmlFlag.UNUSUAL_PATTERN)

    # Structuring suspect (reporting threshold'un hemen altı)
    if currency == "TRY" and 0.85 * SUSPICIOUS_TRANSACTION_THRESHOLD_TRY <= amount < SUSPICIOUS_TRANSACTION_THRESHOLD_TRY:
        flags.append(AmlFlag.STRUCTURING_SUSPECT)

    # Sanctions / PEP
    if counterparty_id and sanctions_list and counterparty_id in sanctions_list:
        flags.append(AmlFlag.SANCTIONS_MATCH)
    if counterparty_id and pep_list and counterparty_id in pep_list:
        flags.append(AmlFlag.PEP_MATCH)

    return flags
