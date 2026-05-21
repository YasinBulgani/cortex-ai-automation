"""
KVKK (6698 sayılı Kişisel Verilerin Korunması Kanunu) — veri sınıflandırma + maskeleme.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Any


class DataClass(str, Enum):
    """KVKK veri kategorileri."""

    PUBLIC = "public"                     # Kurumsal veri (ticari unvan vb)
    PERSONAL = "personal"                 # Ad, soyad, tel, e-posta
    SENSITIVE = "sensitive"               # Özel nitelikli (sağlık, din, siyasi görüş)
    FINANCIAL = "financial"               # IBAN, kart, gelir, bakiye
    IDENTITY = "identity"                 # TCKN, pasaport no, MERSİS
    BIOMETRIC = "biometric"               # Parmak izi, yüz, ses
    LOCATION = "location"                 # GPS, IP, adres


FIELD_CLASSIFICATION: dict[str, DataClass] = {
    # Identity
    "tckn": DataClass.IDENTITY,
    "tc_kimlik_no": DataClass.IDENTITY,
    "passport_no": DataClass.IDENTITY,
    "mersis": DataClass.IDENTITY,
    "vkn": DataClass.IDENTITY,

    # Personal
    "first_name": DataClass.PERSONAL,
    "last_name": DataClass.PERSONAL,
    "full_name": DataClass.PERSONAL,
    "ad": DataClass.PERSONAL,
    "soyad": DataClass.PERSONAL,
    "phone": DataClass.PERSONAL,
    "telefon": DataClass.PERSONAL,
    "email": DataClass.PERSONAL,
    "eposta": DataClass.PERSONAL,
    "birth_date": DataClass.PERSONAL,
    "dogum_tarihi": DataClass.PERSONAL,

    # Financial
    "iban": DataClass.FINANCIAL,
    "account_no": DataClass.FINANCIAL,
    "hesap_no": DataClass.FINANCIAL,
    "card_number": DataClass.FINANCIAL,
    "kart_no": DataClass.FINANCIAL,
    "cvv": DataClass.FINANCIAL,
    "expiry": DataClass.FINANCIAL,
    "income": DataClass.FINANCIAL,
    "gelir": DataClass.FINANCIAL,
    "balance": DataClass.FINANCIAL,
    "bakiye": DataClass.FINANCIAL,
    "salary": DataClass.FINANCIAL,
    "maas": DataClass.FINANCIAL,

    # Sensitive
    "health_condition": DataClass.SENSITIVE,
    "saglik_durumu": DataClass.SENSITIVE,
    "religion": DataClass.SENSITIVE,
    "din": DataClass.SENSITIVE,
    "political_view": DataClass.SENSITIVE,
    "siyasi_gorus": DataClass.SENSITIVE,
    "sexual_orientation": DataClass.SENSITIVE,
    "ethnic_origin": DataClass.SENSITIVE,

    # Biometric
    "fingerprint": DataClass.BIOMETRIC,
    "face_id": DataClass.BIOMETRIC,
    "voice_print": DataClass.BIOMETRIC,

    # Location
    "address": DataClass.LOCATION,
    "adres": DataClass.LOCATION,
    "gps_lat": DataClass.LOCATION,
    "gps_lon": DataClass.LOCATION,
    "ip_address": DataClass.LOCATION,
}


def classify_field(field_name: str) -> DataClass:
    """Field adından veri sınıfını bul."""
    key = field_name.lower().strip()
    return FIELD_CLASSIFICATION.get(key, DataClass.PUBLIC)


# ═══════════════════════════════════════════════════════════════════════════
# Redaction helpers
# ═══════════════════════════════════════════════════════════════════════════


def redact_value(value: Any, data_class: DataClass) -> Any:
    """
    Veri sınıfına göre değeri maskele.

    - PUBLIC  → aynen bırak
    - PERSONAL → kısmi maskele (ad: A*** Y***)
    - IDENTITY → TCKN gibi → 3*** + 2
    - FINANCIAL → IBAN/kart no özel
    - SENSITIVE/BIOMETRIC → [REDACTED]
    """
    if value is None:
        return None
    if data_class == DataClass.PUBLIC:
        return value
    if data_class in (DataClass.SENSITIVE, DataClass.BIOMETRIC):
        return "[REDACTED]"

    s = str(value)

    if data_class == DataClass.IDENTITY:
        # TCKN/VKN/MERSIS — 3 ilk + *** + 2 son
        if s.isdigit() and len(s) >= 10:
            if len(s) == 11:  # TCKN
                return s[:3] + "*" * 6 + s[-2:]
            if len(s) == 10:  # VKN
                return s[:3] + "*" * 5 + s[-2:]
        return s[:2] + "***" if len(s) > 4 else "***"

    if data_class == DataClass.FINANCIAL:
        # IBAN: TR33... → TR33 **** **** **** **** **** 26
        clean = "".join(s.split()).upper()
        if clean.startswith("TR") and len(clean) == 26:
            return clean[:4] + " **** **** **** **** **** " + clean[-2:]
        # Kart no
        if s.replace(" ", "").isdigit() and 13 <= len(s.replace(" ", "")) <= 19:
            digits = s.replace(" ", "")
            return digits[:6] + "*" * (len(digits) - 10) + digits[-4:]
        # Gelir/bakiye → gizle (numeric)
        try:
            float(s)
            return "[HIDDEN]"
        except ValueError:
            return "***"

    if data_class == DataClass.PERSONAL:
        # Telefon: +90 530 *** ** 67
        if s.startswith("+90") or s.startswith("0"):
            clean = "".join(c for c in s if c.isdigit())
            if len(clean) >= 10:
                # Son 10 hane
                local = clean[-10:]
                return f"+90 {local[:3]} *** ** {local[8:]}"
        # Email: a***@gmail.com
        if "@" in s:
            local, domain = s.split("@", 1)
            if len(local) > 1:
                return local[0] + "*" * (len(local) - 1) + "@" + domain
        # Ad/soyad
        parts = s.split()
        masked_parts = []
        for p in parts:
            if len(p) > 1:
                masked_parts.append(p[0] + "*" * (len(p) - 1))
            else:
                masked_parts.append(p)
        return " ".join(masked_parts)

    if data_class == DataClass.LOCATION:
        # Adresin sadece şehrini bırak
        if "," in s:
            parts = s.split(",")
            return "***, " + parts[-1].strip()
        return "[LOCATION_REDACTED]"

    return "***"


def redact_dict(
    data: dict[str, Any],
    *,
    classification: dict[str, DataClass] | None = None,
    skip_classes: set[DataClass] | None = None,
) -> dict[str, Any]:
    """
    Dict içindeki tüm field'ları KVKK sınıflarına göre maskele.

    Args:
        data: Gelen dict
        classification: Custom field classification (default: FIELD_CLASSIFICATION)
        skip_classes: Maskelenmemesi istenen sınıflar (default: {PUBLIC})
    """
    cls_map = classification or FIELD_CLASSIFICATION
    skip = skip_classes if skip_classes is not None else {DataClass.PUBLIC}

    out: dict[str, Any] = {}
    for key, value in data.items():
        field_class = cls_map.get(key.lower(), DataClass.PUBLIC)
        # Dict ve list değerleri key tipi ne olursa olsun RECURSE etmeli
        if isinstance(value, dict):
            out[key] = redact_dict(
                value, classification=classification, skip_classes=skip,
            )
        elif isinstance(value, list):
            out[key] = [
                redact_dict(v, classification=classification, skip_classes=skip)
                if isinstance(v, dict) else (
                    v if field_class in skip else redact_value(v, field_class)
                )
                for v in value
            ]
        else:
            if field_class in skip:
                out[key] = value
            else:
                out[key] = redact_value(value, field_class)
    return out


# ═══════════════════════════════════════════════════════════════════════════
# PII Detection (metin içinde PII ara)
# ═══════════════════════════════════════════════════════════════════════════


_PII_PATTERNS: dict[str, re.Pattern] = {
    "tckn": re.compile(r"\b[1-9][0-9]{10}\b"),
    "iban_tr": re.compile(r"\bTR\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b"),
    "card_number": re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    "phone_tr": re.compile(r"\b(?:\+90|0)?\s?5\d{2}\s?\d{3}\s?\d{2}\s?\d{2}\b"),
    "email": re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
}


def detect_pii(text: str) -> dict[str, list[str]]:
    """
    Metinde PII bulunan tüm eşleşmeleri döndür.
    Dict: kategori → [eşleşen metinler]
    """
    if not text:
        return {}
    found: dict[str, list[str]] = {}
    for category, pattern in _PII_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            found[category] = list(set(matches))
    return found


def redact_pii_in_text(text: str) -> str:
    """Metindeki tüm PII'ları `[REDACTED_XXX]` ile değiştir."""
    if not text:
        return text
    result = text
    for category, pattern in _PII_PATTERNS.items():
        result = pattern.sub(f"[REDACTED_{category.upper()}]", result)
    return result
