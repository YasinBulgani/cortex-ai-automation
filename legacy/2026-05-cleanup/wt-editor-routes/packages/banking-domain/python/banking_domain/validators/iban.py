"""
IBAN (TR) — ISO 13616 Mod-97.

TR IBAN formatı (26 karakter):
  TR kk BBBBB R AAAAAAAAAAAAAAAA
  │  │  │     │ │
  │  │  │     │ └─ Hesap no (16 dijit)
  │  │  │     └─── Reserve (1 dijit, genelde 0)
  │  │  └───────── Banka kodu (5 dijit, TCMB)
  │  └──────────── Check dijits (Mod-97)
  └─────────────── Ülke kodu "TR"
"""
from __future__ import annotations

import random
from typing import Optional

TR_IBAN_LENGTH = 26
TR_COUNTRY = "TR"


def normalize_iban(iban: str) -> str:
    """Boşluk kaldır + büyük harfe çevir."""
    return "".join(iban.split()).upper()


def format_iban(iban: str) -> str:
    """4'erli gruplara ayır: TR33 0006 1005 1978 6457 8413 26"""
    n = normalize_iban(iban)
    return " ".join(n[i : i + 4] for i in range(0, len(n), 4))


def _iban_to_numeric(iban: str) -> str:
    """IBAN Mod-97 için sayısal forma çevir: harfler A=10..Z=35."""
    rearranged = iban[4:] + iban[:4]
    out: list[str] = []
    for ch in rearranged:
        if ch.isdigit():
            out.append(ch)
        elif ch.isalpha():
            out.append(str(ord(ch) - 55))  # A=10, B=11, ..., Z=35
        else:
            # Geçersiz karakter
            return ""
    return "".join(out)


def validate_iban_mod97(iban: str) -> bool:
    """ISO 13616 Mod-97 check."""
    numeric = _iban_to_numeric(iban)
    if not numeric:
        return False
    try:
        return int(numeric) % 97 == 1
    except ValueError:
        return False


def validate_iban_tr(iban: str | None) -> bool:
    """TR IBAN tam validasyon: uzunluk + TR prefix + dijit + Mod-97."""
    if not iban or not isinstance(iban, str):
        return False
    n = normalize_iban(iban)
    if len(n) != TR_IBAN_LENGTH:
        return False
    if not n.startswith(TR_COUNTRY):
        return False
    # TR'den sonra 24 dijit olmalı
    if not n[2:].isdigit():
        return False
    return validate_iban_mod97(n)


def _compute_check_digits(country: str, bban: str) -> str:
    """IBAN check digits üret (BBAN = banka kodu + reserve + hesap)."""
    # Check'ler "00" olarak konur, Mod-97 hesaplanır
    tmp = f"{country}00{bban}"
    numeric = _iban_to_numeric(tmp)
    if not numeric:
        raise ValueError("Geçersiz karakter")
    check = 98 - (int(numeric) % 97)
    return f"{check:02d}"


def generate_iban_tr(
    bank_code: str | None = None,
    account_no: str | None = None,
) -> str:
    """
    Geçerli TR IBAN üret.

    Args:
        bank_code: 5-dijit banka kodu (default: rastgele bilinen bankadan).
        account_no: 16-dijit hesap no (default: rastgele).

    Returns:
        "TR\\d{24}" formatında geçerli IBAN.
    """
    if bank_code is None:
        # Bilinen TR bankalarından rastgele seç
        bank_code = random.choice([
            "00046",  # Akbank
            "00062",  # Garanti BBVA
            "00064",  # İş Bankası
            "00067",  # Yapı Kredi
            "00012",  # Halk Bankası
            "00010",  # Ziraat
            "00015",  # Ziraat (alt kod)
            "00111",  # QNB Finansbank
            "00143",  # TEB
            "00203",  # Albaraka Türk
            "00205",  # Kuveyt Türk
        ])
    if not (len(bank_code) == 5 and bank_code.isdigit()):
        raise ValueError(f"Geçersiz banka kodu: {bank_code}")

    if account_no is None:
        account_no = "".join(random.choices("0123456789", k=16))
    if not (len(account_no) == 16 and account_no.isdigit()):
        raise ValueError(f"Geçersiz hesap no: {account_no}")

    reserve = "0"  # TR reserve hanesi
    bban = f"{bank_code}{reserve}{account_no}"  # 5+1+16 = 22
    check = _compute_check_digits("TR", bban)
    iban = f"TR{check}{bban}"
    assert len(iban) == TR_IBAN_LENGTH
    assert validate_iban_tr(iban), f"Üretilen IBAN doğrulanamadı: {iban}"
    return iban


def get_bank_code_from_iban(iban: str) -> Optional[str]:
    """IBAN'dan banka kodunu çıkar (5 dijit)."""
    if not validate_iban_tr(iban):
        return None
    n = normalize_iban(iban)
    return n[4:9]
