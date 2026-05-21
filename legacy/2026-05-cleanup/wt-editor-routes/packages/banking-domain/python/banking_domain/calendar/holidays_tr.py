"""
TR Resmi Tatilleri + Dini Bayramlar 2026-2027.

Resmi kaynak: Kültür ve Turizm Bakanlığı + Diyanet (hicri → miladi).
"""
from __future__ import annotations

from datetime import date, timedelta


# ═══════════════════════════════════════════════════════════════════════════
# Sabit (miladi) resmi tatiller
# ═══════════════════════════════════════════════════════════════════════════


def _generate_fixed_holidays(year: int) -> dict[date, str]:
    """Yılda değişmeyen miladi tatiller."""
    return {
        date(year, 1, 1): "Yılbaşı",
        date(year, 4, 23): "Ulusal Egemenlik ve Çocuk Bayramı",
        date(year, 5, 1): "Emek ve Dayanışma Günü",
        date(year, 5, 19): "Atatürk'ü Anma, Gençlik ve Spor Bayramı",
        date(year, 7, 15): "Demokrasi ve Milli Birlik Günü",
        date(year, 8, 30): "Zafer Bayramı",
        date(year, 10, 29): "Cumhuriyet Bayramı",
    }


# Pre-calculated 2025-2028 resmi tatil + arefe tanımları
RESMI_TATILLER: dict[date, str] = {}
for _year in (2025, 2026, 2027, 2028):
    RESMI_TATILLER.update(_generate_fixed_holidays(_year))


# ═══════════════════════════════════════════════════════════════════════════
# Dini Bayramlar (Diyanet kaynaklı, miladi takvime çevrilmiş)
# ═══════════════════════════════════════════════════════════════════════════
# Her bayram için (başlangıç, bitiş) tuple + "Ramazan Bayramı 1. Günü" gibi etiketler

DINI_BAYRAMLAR: dict[date, str] = {}


def _add_bayram(start: date, days: int, name: str) -> None:
    for i in range(days):
        DINI_BAYRAMLAR[start + timedelta(days=i)] = f"{name} {i + 1}. Günü"


# 2025 Ramazan Bayramı: 30 Mart - 1 Nisan (3 gün)
_add_bayram(date(2025, 3, 30), 3, "Ramazan Bayramı")
# 2025 Kurban Bayramı: 6-9 Haziran (4 gün)
_add_bayram(date(2025, 6, 6), 4, "Kurban Bayramı")

# 2026 Ramazan Bayramı: 20-22 Mart (3 gün)
_add_bayram(date(2026, 3, 20), 3, "Ramazan Bayramı")
# 2026 Kurban Bayramı: 26-29 Mayıs (4 gün)
_add_bayram(date(2026, 5, 26), 4, "Kurban Bayramı")

# 2027 Ramazan Bayramı: 10-12 Mart (3 gün)
_add_bayram(date(2027, 3, 10), 3, "Ramazan Bayramı")
# 2027 Kurban Bayramı: 16-19 Mayıs (4 gün)
_add_bayram(date(2027, 5, 16), 4, "Kurban Bayramı")

# 2028 Ramazan Bayramı: 27 Şubat-1 Mart (3 gün)
_add_bayram(date(2028, 2, 27), 3, "Ramazan Bayramı")
# 2028 Kurban Bayramı: 5-8 Mayıs (4 gün)
_add_bayram(date(2028, 5, 5), 4, "Kurban Bayramı")


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════


def is_holiday(d: date) -> bool:
    """Resmi tatil veya dini bayram mı?"""
    return d in RESMI_TATILLER or d in DINI_BAYRAMLAR


def is_weekend(d: date) -> bool:
    """Cumartesi (5) veya Pazar (6) mı?"""
    return d.weekday() >= 5


def is_business_day(d: date) -> bool:
    """Hafta içi ve tatil değil mi?"""
    return not is_weekend(d) and not is_holiday(d)


def next_business_day(d: date) -> date:
    """Verilen günden sonraki ilk iş günü."""
    candidate = d + timedelta(days=1)
    while not is_business_day(candidate):
        candidate += timedelta(days=1)
    return candidate


def previous_business_day(d: date) -> date:
    """Verilen günden önceki son iş günü."""
    candidate = d - timedelta(days=1)
    while not is_business_day(candidate):
        candidate -= timedelta(days=1)
    return candidate


def business_days_between(start: date, end: date) -> int:
    """start (dahil) ile end (hariç) arası iş günü sayısı."""
    if start > end:
        start, end = end, start
    count = 0
    current = start
    while current < end:
        if is_business_day(current):
            count += 1
        current += timedelta(days=1)
    return count


def add_business_days(d: date, days: int) -> date:
    """Verilen güne N iş günü ekle (veya çıkar negatifse)."""
    current = d
    step = 1 if days >= 0 else -1
    remaining = abs(days)
    while remaining > 0:
        current += timedelta(days=step)
        if is_business_day(current):
            remaining -= 1
    return current


def holidays_in_year(year: int) -> list[tuple[date, str]]:
    """Yıl içindeki tüm tatilleri (resmi + dini) sıralı liste olarak döndür."""
    all_holidays: list[tuple[date, str]] = []
    for d, name in RESMI_TATILLER.items():
        if d.year == year:
            all_holidays.append((d, name))
    for d, name in DINI_BAYRAMLAR.items():
        if d.year == year:
            all_holidays.append((d, name))
    all_holidays.sort(key=lambda x: x[0])
    return all_holidays
