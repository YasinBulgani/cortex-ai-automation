"""
TR Telefon numarası — mobil operatör prefix kontrolü + normalizasyon.

Kabul edilen formatlar:
  +90 530 123 45 67
  0530 123 45 67
  5301234567
  +905301234567

Normalize formatı: "+90XXXXXXXXXX" (13 karakter).
"""
from __future__ import annotations

import random
import re

# TR mobil operatör prefixleri (2026 itibariyle BTK ayırmalı)
_TURKCELL_PREFIXES = ["530", "531", "532", "533", "534", "535", "536", "537", "538", "539"]
_VODAFONE_PREFIXES = ["540", "541", "542", "543", "544", "545", "546", "547", "548", "549"]
_TURKTELEKOM_PREFIXES = ["550", "551", "552", "553", "554", "555", "556", "557", "558", "559"]

# İlave: Bimcell, Pttcell vb. (MVNO prefixlerini de ekle)
_ALL_MOBILE_PREFIXES = set(
    _TURKCELL_PREFIXES + _VODAFONE_PREFIXES + _TURKTELEKOM_PREFIXES
)

_PHONE_CLEAN_RE = re.compile(r"[\s\-\(\)\.]")


def normalize_phone_tr(phone: str | None) -> str | None:
    """
    Girilen formatı "+90XXXXXXXXXX" biçimine çevir.

    None döner eğer:
      - Boş/None input
      - Format tanınmıyor
      - Dijit sayısı yanlış
    """
    if not phone:
        return None
    # Temizle
    clean = _PHONE_CLEAN_RE.sub("", phone)
    if not clean:
        return None

    # +90 prefix'i
    if clean.startswith("+90"):
        clean = clean[3:]
    elif clean.startswith("0090"):
        clean = clean[4:]
    elif clean.startswith("90") and len(clean) == 12:
        clean = clean[2:]
    elif clean.startswith("0") and len(clean) == 11:
        clean = clean[1:]

    if len(clean) != 10 or not clean.isdigit():
        return None

    return f"+90{clean}"


def validate_phone_tr(phone: str | None, mobile_only: bool = True) -> bool:
    """
    TR telefon validasyon. mobile_only=True ise operatör prefix kontrolü yapar.
    """
    normalized = normalize_phone_tr(phone)
    if not normalized:
        return False
    # "+90" + 10 dijit
    local = normalized[3:]
    if not (len(local) == 10 and local.isdigit()):
        return False
    if mobile_only:
        prefix = local[:3]
        return prefix in _ALL_MOBILE_PREFIXES
    return True


def generate_phone_tr(operator: str | None = None) -> str:
    """
    Rastgele TR mobil numara üret.

    operator: "turkcell" | "vodafone" | "turktelekom" | None (rastgele)
    """
    if operator == "turkcell":
        prefix = random.choice(_TURKCELL_PREFIXES)
    elif operator == "vodafone":
        prefix = random.choice(_VODAFONE_PREFIXES)
    elif operator == "turktelekom":
        prefix = random.choice(_TURKTELEKOM_PREFIXES)
    else:
        prefix = random.choice(list(_ALL_MOBILE_PREFIXES))
    rest = "".join(random.choices("0123456789", k=7))
    return f"+90{prefix}{rest}"


def format_phone_tr(phone: str, style: str = "international") -> str:
    """
    "+905301234567" → çeşitli stiller:
      international: "+90 530 123 45 67"
      national:      "0530 123 45 67"
      plain:         "5301234567"
    """
    normalized = normalize_phone_tr(phone)
    if not normalized:
        return phone or ""
    local = normalized[3:]
    groups = f"{local[:3]} {local[3:6]} {local[6:8]} {local[8:]}"
    if style == "international":
        return f"+90 {groups}"
    if style == "national":
        return f"0{local[0]}{local[1:3]} {local[3:6]} {local[6:8]} {local[8:]}"
    return local


def get_operator(phone: str) -> str | None:
    """Numarayı operatöre eşle ('turkcell' / 'vodafone' / 'turktelekom')."""
    normalized = normalize_phone_tr(phone)
    if not normalized:
        return None
    prefix = normalized[3:6]
    if prefix in _TURKCELL_PREFIXES:
        return "turkcell"
    if prefix in _VODAFONE_PREFIXES:
        return "vodafone"
    if prefix in _TURKTELEKOM_PREFIXES:
        return "turktelekom"
    return None


def mask_phone_tr(phone: str) -> str:
    """Maskele: "+90 530 *** ** 67" """
    normalized = normalize_phone_tr(phone)
    if not normalized:
        return phone or ""
    local = normalized[3:]
    return f"+90 {local[:3]} *** ** {local[8:]}"
