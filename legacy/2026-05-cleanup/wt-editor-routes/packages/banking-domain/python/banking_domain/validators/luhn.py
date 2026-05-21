"""
Luhn Algoritması — ISO/IEC 7812-1.

Kredi/banka kartı numaralarının sağlamasını kontrol eder.
"""
from __future__ import annotations

import random


def validate_luhn(card_number: str | None) -> bool:
    """
    Luhn check.

    Çift konumdaki (sağdan 2., 4., ...) her dijit 2'yle çarpılır; sonuç 9'u aşarsa
    9 çıkarılır. Tüm dijitlerin toplamı 10'a bölünebiliyorsa geçerli.
    """
    if not card_number:
        return False
    digits = [int(c) for c in str(card_number) if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def luhn_check_digit(body: str) -> int:
    """
    Verilen kart no gövdesinden (check hariç) Luhn check dijitini hesaplar.
    """
    digits = [int(c) for c in body if c.isdigit()]
    # "Tam" kart no için çift konumlar sağdan 2., 4. — ama bizde sondaki dijit ekleneceği
    # için gövdeyi 1 kaydırılmış gibi düşünmemiz lazım.
    checksum = 0
    # Şu an body'nin son dijiti "sağdan 2." konumunda olacak (check eklenince)
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 0:  # Check dijit olmadan sağdan 2. → şu ankinin 1.
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return (10 - (checksum % 10)) % 10


def generate_card_number(bin_prefix: str, length: int = 16) -> str:
    """
    Verilen BIN prefix ile Luhn-valid kart no üret.

    Args:
        bin_prefix: Genellikle 6 dijit banka/network kodu.
        length: Toplam kart no uzunluğu (13-19 arası; VISA 16, AMEX 15).

    Returns:
        Luhn check dijiti dahil, geçerli kart numarası.
    """
    if not (13 <= length <= 19):
        raise ValueError(f"Kart no uzunluğu 13-19 arası olmalı: {length}")
    if not bin_prefix.isdigit():
        raise ValueError(f"BIN dijitlerden oluşmalı: {bin_prefix}")
    if len(bin_prefix) >= length:
        raise ValueError(f"BIN length ({len(bin_prefix)}) >= total length ({length})")

    body_length = length - 1  # check dijit için 1 dijit ayır
    filler = "".join(random.choices("0123456789", k=body_length - len(bin_prefix)))
    body = bin_prefix + filler
    check = luhn_check_digit(body)
    card = f"{body}{check}"
    assert validate_luhn(card), f"Luhn check failed: {card}"
    return card


def mask_card_number(card: str, visible_first: int = 6, visible_last: int = 4) -> str:
    """
    PCI-DSS uyumlu maskele: "1234567812345678" → "123456******5678"
    """
    if not card:
        return ""
    clean = "".join(c for c in card if c.isdigit())
    if len(clean) < visible_first + visible_last:
        return clean
    hidden = "*" * (len(clean) - visible_first - visible_last)
    return clean[:visible_first] + hidden + clean[-visible_last:]


# Popüler test BIN'leri (public test numaraları için)
BIN_TEST_CARDS: dict[str, str] = {
    "VISA": "454360",
    "MASTERCARD": "550000",
    "AMEX": "378282",
    "TROY": "979200",   # TR Troy
    "DISCOVER": "601100",
}


def generate_test_card(network: str = "VISA") -> str:
    """Test kart no üret (network bazlı)."""
    network = network.upper()
    if network not in BIN_TEST_CARDS:
        raise ValueError(f"Bilinmeyen network: {network}")
    bin_prefix = BIN_TEST_CARDS[network]
    length = 15 if network == "AMEX" else 16
    return generate_card_number(bin_prefix, length)
