"""
Maaş günü patternları — TR bankacılık/işletme normları.

Patternlar:
- CIVIL_SERVANT: Ayın 15'i (devlet memuru maaşı)
- PRIVATE_MONTHLY: Ayın son iş günü (özel sektör aylık)
- PENSION: Hesap sonuna göre ayın 1-12'si arası dağılım (emeklilik)
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date
from enum import Enum

from .holidays_tr import next_business_day, previous_business_day, is_business_day


class SalaryPattern(str, Enum):
    CIVIL_SERVANT = "civil_servant"       # 15'i
    PRIVATE_MONTHLY = "private_monthly"   # Ayın son iş günü
    PRIVATE_BIMONTHLY = "private_bimonthly"  # 15 + ayın sonu
    PENSION = "pension"                   # 1-12 arası (hesap no son hanesine göre)
    CUSTOM = "custom"


def salary_day_for_month(
    year: int,
    month: int,
    pattern: SalaryPattern = SalaryPattern.CIVIL_SERVANT,
    *,
    pension_bucket: int = 0,  # 0-11 arası bucket
) -> date:
    """
    Verilen ay için tahmin edilen maaş ödeme günü.

    Tatile denk gelirse önceki iş gününe kaydırılır (bankacılık pratiği).
    """
    if pattern == SalaryPattern.CIVIL_SERVANT:
        target = date(year, month, 15)
    elif pattern == SalaryPattern.PRIVATE_MONTHLY:
        last_day = monthrange(year, month)[1]
        target = date(year, month, last_day)
    elif pattern == SalaryPattern.PENSION:
        # TR'de emeklilik maaşları TC son hanesine göre 1-12'si arasında dağıtılıyor
        bucket = max(0, min(11, pension_bucket))
        target = date(year, month, bucket + 1)
    elif pattern == SalaryPattern.PRIVATE_BIMONTHLY:
        # İlk ödeme 15'i, 2. ödeme ayın sonu — burada 15'i döndür
        target = date(year, month, 15)
    else:
        target = date(year, month, 1)

    if is_business_day(target):
        return target
    # Tatilse önceki iş gününe kaydır
    return previous_business_day(target)


def is_salary_day(
    d: date,
    pattern: SalaryPattern = SalaryPattern.CIVIL_SERVANT,
    *,
    pension_bucket: int = 0,
) -> bool:
    """Verilen tarih, pattern'a göre bir maaş günü mü?"""
    salary_d = salary_day_for_month(
        d.year, d.month, pattern, pension_bucket=pension_bucket
    )
    return d == salary_d


def get_pension_bucket(tckn: str) -> int:
    """
    TCKN son hanesine göre emekli maaşı ödeme bucket'ı.
    SGK 2007+ uygulaması: son hane 0-9; 0 ise 1. günü, 9 ise 10. günü.
    (Basitleştirilmiş model — gerçek dağıtım daha kompleks.)
    """
    if not tckn or len(tckn) < 11:
        return 0
    last = int(tckn[-1])
    return last  # 0-9 arası
