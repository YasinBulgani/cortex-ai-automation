"""
BIC (SWIFT Business Identifier Code) — ISO 9362.

Format: AAAA CC LL [BBB]
  AAAA — 4 harf banka kodu
  CC   — 2 harf ülke kodu (ISO 3166-1 alpha-2)
  LL   — 2 alfanümerik lokasyon kodu
  BBB  — 3 alfanümerik branch (opsiyonel)

Toplam: 8 veya 11 karakter.
"""
from __future__ import annotations

import re

_BIC_RE = re.compile(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")


def validate_bic(bic: str | None) -> bool:
    """ISO 9362 BIC formatı kontrolü."""
    if not bic or not isinstance(bic, str):
        return False
    b = bic.strip().upper()
    if len(b) not in (8, 11):
        return False
    return bool(_BIC_RE.match(b))


def bic_country_code(bic: str) -> str | None:
    """BIC'ten 2 harf ülke kodunu al (validasyon varsayılır)."""
    if not validate_bic(bic):
        return None
    return bic.upper()[4:6]


def bic_bank_code(bic: str) -> str | None:
    """BIC'ten 4 harf banka kodunu al."""
    if not validate_bic(bic):
        return None
    return bic.upper()[:4]
