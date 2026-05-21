"""
Bankacilik Domain Dagilim Fonksiyonlari.

Turk bankacilik sektorune ozgu istatistiksel dagilimlari kullanarak
gercekci sentetik veri ureten fonksiyonlar:
- Bakiye: lognormal (segment bazli)
- Islem tutari: lognormal-pareto karişimi
- Islem sikligi: Poisson
- Kredi skoru: Beta (yeniden olceklenmis)
- TCKN: algoritmik checksum
- IBAN: mod-97 kontrol haneli
"""
from __future__ import annotations

import random
import string
from datetime import date, timedelta

import numpy as np

# ── Turk Bankasi BIN Kodlari ─────────────────────────────────────────────────
TURKISH_BANK_CODES = [
    "0001", "0004", "0006", "0010", "0012", "0015", "0032",
    "0046", "0062", "0064", "0067", "0099", "0103", "0111", "0134",
]

# ── Segment Bazli Bakiye Parametreleri (lognormal mu, sigma) ──────────────────
SEGMENT_BALANCE_PARAMS: dict[str, dict[str, float]] = {
    "Bireysel":  {"mu": 9.0,  "sigma": 1.8, "min": 0,   "max": 500_000},
    "Premium":   {"mu": 12.0, "sigma": 1.5, "min": 1000, "max": 10_000_000},
    "Kurumsal":  {"mu": 13.5, "sigma": 2.0, "min": 5000, "max": 100_000_000},
    "VIP":       {"mu": 13.0, "sigma": 1.2, "min": 50000, "max": 50_000_000},
    "KOBİ":     {"mu": 11.0, "sigma": 1.8, "min": 0,   "max": 5_000_000},
}

# ── Islem Tipi Bazli Tutar Parametreleri ──────────────────────────────────────
TRANSACTION_AMOUNT_PARAMS: dict[str, dict[str, float]] = {
    "EFT":       {"mu": 8.5, "sigma": 1.5, "min": 1,    "max": 5_000_000},
    "Havale":    {"mu": 7.5, "sigma": 1.2, "min": 1,    "max": 1_000_000},
    "ATM":       {"mu": 6.0, "sigma": 0.8, "min": 10,   "max": 10_000},
    "POS":       {"mu": 5.5, "sigma": 1.0, "min": 1,    "max": 50_000},
    "Virman":    {"mu": 8.0, "sigma": 1.5, "min": 1,    "max": 10_000_000},
    "Fatura":    {"mu": 5.0, "sigma": 0.8, "min": 10,   "max": 5_000},
    "Maas":      {"mu": 9.5, "sigma": 0.5, "min": 8000, "max": 200_000},
}


def generate_balance(segment: str = "Bireysel", n: int = 1) -> np.ndarray:
    """Segment bazli lognormal bakiye uret."""
    params = SEGMENT_BALANCE_PARAMS.get(segment, SEGMENT_BALANCE_PARAMS["Bireysel"])
    values = np.random.lognormal(mean=params["mu"], sigma=params["sigma"], size=n)
    return np.clip(values, params["min"], params["max"]).round(2)


def generate_transaction_amount(tx_type: str = "EFT", n: int = 1) -> np.ndarray:
    """Islem tipine gore lognormal tutar uret."""
    params = TRANSACTION_AMOUNT_PARAMS.get(tx_type, TRANSACTION_AMOUNT_PARAMS["EFT"])
    values = np.random.lognormal(mean=params["mu"], sigma=params["sigma"], size=n)
    return np.clip(values, params["min"], params["max"]).round(2)


def generate_transaction_frequency(segment: str = "Bireysel", n: int = 1) -> np.ndarray:
    """Aylik islem sikligi — Poisson dagilimi."""
    lambdas = {
        "Bireysel": 15, "Premium": 30, "Kurumsal": 80,
        "VIP": 25, "KOBİ": 45,
    }
    lam = lambdas.get(segment, 15)
    return np.random.poisson(lam=lam, size=n)


def generate_credit_score(n: int = 1) -> np.ndarray:
    """Kredi skoru — Beta(5,2) dagilimi, 300-1900 arasina olceklenmis."""
    raw = np.random.beta(a=5, b=2, size=n)
    return (raw * 1600 + 300).round(0).astype(int)


def generate_age(n: int = 1) -> np.ndarray:
    """Musteri yasi — truncated normal, 18-85 arasi."""
    ages = np.random.normal(loc=42, scale=14, size=n)
    return np.clip(ages, 18, 85).round(0).astype(int)


# ── TCKN Uretimi (algoritmik checksum) ───────────────────────────────────────

def generate_tckn(n: int = 1) -> list[str]:
    """Algoritmik olarak gecerli 11 haneli TC Kimlik Numarasi uret."""
    results = []
    for _ in range(n):
        digits = [random.randint(1, 9)]  # ilk hane 0 olamaz
        digits += [random.randint(0, 9) for _ in range(8)]

        odd_sum = sum(digits[i] for i in range(0, 9, 2))
        even_sum = sum(digits[i] for i in range(1, 9, 2))
        d10 = (odd_sum * 7 - even_sum) % 10
        digits.append(d10)

        d11 = sum(digits[:10]) % 10
        digits.append(d11)

        results.append("".join(str(d) for d in digits))
    return results


# ── IBAN Uretimi (mod-97 kontrol haneli) ──────────────────────────────────────

def generate_iban(n: int = 1) -> list[str]:
    """ISO 13616 uyumlu Turk IBAN'i uret (TR + 2 kontrol + 22 hane)."""
    results = []
    for _ in range(n):
        bank_code = random.choice(TURKISH_BANK_CODES)
        reserved = "0"
        account = "".join(random.choices(string.digits, k=17))
        bban = bank_code + reserved + account

        numeric_iban = bban + "2929" + "00"  # TR = 29 29
        remainder = int(numeric_iban) % 97
        check_digits = f"{98 - remainder:02d}"

        results.append(f"TR{check_digits}{bban}")
    return results


def generate_phone(n: int = 1) -> list[str]:
    """+90 5XX XXX XX XX formatinda telefon numarasi uret."""
    prefixes = ["530", "531", "532", "533", "534", "535", "536", "537", "538", "539",
                "540", "541", "542", "543", "544", "545", "546", "547", "548", "549",
                "550", "551", "552", "553", "554", "555", "556", "557", "558", "559"]
    results = []
    for _ in range(n):
        prefix = random.choice(prefixes)
        rest = "".join(random.choices(string.digits, k=7))
        results.append(f"+90 {prefix} {rest[:3]} {rest[3:5]} {rest[5:]}")
    return results


def generate_transaction_dates(
    n: int = 1,
    start: date | None = None,
    end: date | None = None,
) -> list[str]:
    """Son 1 yil icinde islem tarihleri uret — hafta ici yogunluklu."""
    if end is None:
        end = date.today()
    if start is None:
        start = end - timedelta(days=365)

    days_range = (end - start).days
    results = []
    attempts = 0
    while len(results) < n and attempts < n * 5:
        attempts += 1
        day = start + timedelta(days=random.randint(0, days_range))
        weekday = day.weekday()
        if weekday < 5 or random.random() < 0.15:
            results.append(day.isoformat())

    while len(results) < n:
        results.append((start + timedelta(days=random.randint(0, days_range))).isoformat())

    random.shuffle(results)
    return results[:n]
