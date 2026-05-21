"""
BDDK (Bankacılık Düzenleme ve Denetleme Kurumu) — kredi limit ve sermaye kuralları.

Bu modül basitleştirilmiş temsil sağlar; gerçek BDDK kuralları çok daha karmaşıktır.
"""
from __future__ import annotations

from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════
# Sermaye Yeterliliği (CAR — Capital Adequacy Ratio)
# ═══════════════════════════════════════════════════════════════════════════

CAR_MINIMUM: float = 0.12
"""
BDDK Sermaye Yeterliliği Tebliği — minimum %12.
(Basel III + TR ek tampon).
"""

CAR_COMMON_EQUITY_TIER1_MIN: float = 0.08
"""CET1 minimum %8."""


def check_capital_adequacy_ratio(
    tier1_capital: float,
    tier2_capital: float,
    risk_weighted_assets: float,
) -> tuple[float, bool]:
    """
    CAR hesapla + BDDK minimum ile karşılaştır.

    Returns: (ratio, is_compliant)
    """
    if risk_weighted_assets <= 0:
        return 0.0, False
    ratio = (tier1_capital + tier2_capital) / risk_weighted_assets
    return ratio, ratio >= CAR_MINIMUM


# ═══════════════════════════════════════════════════════════════════════════
# Kredi/Borç Oranı (DTI — Debt-to-Income) Limitleri
# ═══════════════════════════════════════════════════════════════════════════
# BDDK'nın segmentlere göre DTI limitleri — 2026 yaklaşımı

DTI_LIMITS: dict[str, float] = {
    "retail": 0.50,       # Bireysel: aylık gelirin %50'sini aşmayan borç
    "mass": 0.55,
    "affluent": 0.60,
    "private": 0.70,
    "sme": 0.70,
    "corporate": 0.80,
}


def calculate_credit_limit(
    monthly_income: float,
    segment: str,
    other_debts: float = 0.0,
    *,
    months: int = 12,
) -> float:
    """
    Segmente göre maksimum kredi kartı limit hesapla.

    Args:
        monthly_income: Aylık net gelir (TRY)
        segment: retail | mass | affluent | private | sme | corporate
        other_debts: Müşterinin mevcut diğer borçları toplamı
        months: Gelir × ay çarpanı (default: 12 ay yıllık)

    Returns:
        Max kart/kredi limiti (TRY), en az 0
    """
    if monthly_income <= 0:
        return 0.0

    dti = DTI_LIMITS.get(segment.lower(), 0.50)
    max_total_debt = monthly_income * dti * months
    available = max_total_debt - other_debts
    return round(max(0.0, available), 0)


# ═══════════════════════════════════════════════════════════════════════════
# Karta/Kredi Başvuru Reddi Kontrolleri
# ═══════════════════════════════════════════════════════════════════════════


class RejectionReason(str, Enum):
    INSUFFICIENT_INCOME = "insufficient_income"
    HIGH_DTI = "high_dti"
    LOW_CREDIT_SCORE = "low_credit_score"
    BLACKLIST = "blacklist"
    AGE_LIMIT = "age_limit"
    MISSING_KYC = "missing_kyc"


def assess_credit_application(
    *,
    monthly_income: float,
    age: int,
    segment: str,
    existing_debts: float,
    requested_amount: float,
    credit_score: int | None = None,
    kyc_verified: bool = True,
    is_blacklisted: bool = False,
) -> tuple[bool, list[RejectionReason]]:
    """
    Kredi başvurusu değerlendirme.

    Returns: (approved, reasons) — approved=False ise reasons doludur
    """
    reasons: list[RejectionReason] = []

    if age < 18 or age > 75:
        reasons.append(RejectionReason.AGE_LIMIT)
    if not kyc_verified:
        reasons.append(RejectionReason.MISSING_KYC)
    if is_blacklisted:
        reasons.append(RejectionReason.BLACKLIST)
    if monthly_income < 10_000:  # 2026 asgari ücretin altı
        reasons.append(RejectionReason.INSUFFICIENT_INCOME)
    if credit_score is not None and credit_score < 1100:
        # KKB skoru 1100 altı = düşük
        reasons.append(RejectionReason.LOW_CREDIT_SCORE)

    max_limit = calculate_credit_limit(monthly_income, segment, existing_debts)
    if requested_amount > max_limit:
        reasons.append(RejectionReason.HIGH_DTI)

    return (len(reasons) == 0, reasons)
