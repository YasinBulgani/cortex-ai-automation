"""
Customer generator — TR lokalli, geçerli TCKN + telefon + segment.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from ..validators.tckn import generate_tckn
from ..validators.phone_tr import generate_phone_tr


class CustomerSegment(str, Enum):
    RETAIL = "retail"            # Bireysel (ana kitle)
    MASS = "mass"                # Kitlesel
    AFFLUENT = "affluent"        # Üst-orta gelir
    PRIVATE = "private"          # Private banking
    SME = "sme"                  # KOBİ
    CORPORATE = "corporate"      # Kurumsal


# Segment dağılımı (gerçekçi TR bankacılık piyasa profili)
_SEGMENT_WEIGHTS: dict[CustomerSegment, float] = {
    CustomerSegment.RETAIL: 0.60,
    CustomerSegment.MASS: 0.25,
    CustomerSegment.AFFLUENT: 0.08,
    CustomerSegment.PRIVATE: 0.02,
    CustomerSegment.SME: 0.04,
    CustomerSegment.CORPORATE: 0.01,
}


# Segment → aylık net gelir aralığı (TRY, 2026 yaklaşımı)
_SEGMENT_INCOME_RANGE: dict[CustomerSegment, tuple[int, int]] = {
    CustomerSegment.RETAIL: (15_000, 40_000),
    CustomerSegment.MASS: (30_000, 80_000),
    CustomerSegment.AFFLUENT: (60_000, 200_000),
    CustomerSegment.PRIVATE: (150_000, 1_000_000),
    CustomerSegment.SME: (20_000, 300_000),  # KOBİ — girişimci geliri
    CustomerSegment.CORPORATE: (500_000, 10_000_000),  # Şirket
}


# TR büyük şehir dağılımı
_CITIES = [
    ("İstanbul", 0.20),
    ("Ankara", 0.08),
    ("İzmir", 0.06),
    ("Bursa", 0.04),
    ("Antalya", 0.04),
    ("Adana", 0.03),
    ("Konya", 0.03),
    ("Gaziantep", 0.03),
    ("Mersin", 0.02),
    ("Kayseri", 0.02),
    ("Eskişehir", 0.02),
    ("Samsun", 0.02),
    ("Diğer", 0.41),
]


_FIRST_NAMES_MALE = [
    "Ahmet", "Mehmet", "Mustafa", "Ali", "Hüseyin", "Hasan", "İbrahim", "Osman",
    "Yusuf", "Ömer", "Emre", "Kerem", "Can", "Burak", "Okan", "Selim", "Furkan",
    "Yiğit", "Deniz", "Berk", "Arda", "Mert", "Caner", "Serkan", "Onur",
]
_FIRST_NAMES_FEMALE = [
    "Ayşe", "Fatma", "Emine", "Hatice", "Zeynep", "Elif", "Merve", "Büşra",
    "Gamze", "Selin", "Ezgi", "İrem", "Ece", "Begüm", "Sude", "Azra", "Defne",
    "Naz", "Derya", "Cansu", "Melisa", "Aylin", "Pınar", "Seda", "Gizem",
]
_LAST_NAMES = [
    "Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Yıldız", "Yıldırım", "Öztürk",
    "Aydın", "Özdemir", "Arslan", "Doğan", "Kılıç", "Aslan", "Çetin", "Kara",
    "Koç", "Kurt", "Özkan", "Şimşek", "Polat", "Erdoğan", "Tekin", "Güneş",
]


@dataclass
class Customer:
    """Banka müşterisi."""

    id: str
    tckn: str
    first_name: str
    last_name: str
    birth_date: date
    gender: str  # "M" | "F"
    phone: str
    email: str
    city: str
    segment: CustomerSegment
    income: float
    risk_score: int  # 0-100
    kyc_verified: bool = True
    created_at: date = field(default_factory=date.today)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self) -> int:
        today = date.today()
        years = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            years -= 1
        return years

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tckn": self.tckn,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "birth_date": self.birth_date.isoformat(),
            "age": self.age,
            "gender": self.gender,
            "phone": self.phone,
            "email": self.email,
            "city": self.city,
            "segment": self.segment.value,
            "income": self.income,
            "risk_score": self.risk_score,
            "kyc_verified": self.kyc_verified,
            "created_at": self.created_at.isoformat(),
        }


def _weighted_choice(choices: list[tuple[Any, float]]):
    items = [c[0] for c in choices]
    weights = [c[1] for c in choices]
    return random.choices(items, weights=weights, k=1)[0]


def _random_birth_date(age_min: int, age_max: int) -> date:
    """Verilen aralıkta geçerli bir yaşa denk gelen birth_date üret."""
    today = date.today()
    # Hedef yaşı randomla
    target_age = random.randint(age_min, age_max)
    # Doğum yılı
    birth_year = today.year - target_age
    # Geçmiş bir tarih olduğundan emin ol: bugünden 1 gün önce maksimum
    # Ay/gün: target_age'in tam tutması için
    # Eğer bugüne kadar olan aralıkta ay/gün seçersek age = target_age
    # Yoksa age = target_age - 1 olur.
    # Basit yaklaşım: 1 Ocak - bugünden 1 gün önce arası
    start = date(birth_year, 1, 1)
    end = date(birth_year, today.month, today.day) if target_age > 0 else today
    if end < start:
        end = start
    days_range = (end - start).days
    offset = random.randint(0, max(0, days_range))
    from datetime import timedelta
    return start + timedelta(days=offset)


def _risk_score(segment: CustomerSegment, age: int, income: float) -> int:
    """Basit risk skor hesabı (0-100, düşük = iyi müşteri)."""
    base = 20
    if segment in (CustomerSegment.PRIVATE, CustomerSegment.CORPORATE):
        base = 10
    elif segment == CustomerSegment.SME:
        base = 30
    # Genç = daha riskli
    if age < 25:
        base += 15
    elif age < 30:
        base += 5
    # Yüksek gelir = daha güvenilir
    if income > 100_000:
        base -= 10
    return max(0, min(100, base + random.randint(-10, 10)))


def _generate_email(first: str, last: str) -> str:
    # TR karakterleri ASCII'ye çevir
    tr_map = {"ş": "s", "ğ": "g", "ü": "u", "ı": "i", "ç": "c", "ö": "o",
              "Ş": "S", "Ğ": "G", "Ü": "U", "İ": "I", "Ç": "C", "Ö": "O"}
    def _ascii(s: str) -> str:
        return "".join(tr_map.get(c, c) for c in s).lower()
    domain = random.choice(["gmail.com", "hotmail.com", "yahoo.com", "outlook.com", "mail.com"])
    return f"{_ascii(first)}.{_ascii(last)}{random.randint(1, 999)}@{domain}"


def generate_customer(
    *,
    segment: CustomerSegment | str | None = None,
    age_range: tuple[int, int] = (18, 75),
    city: str | None = None,
    kyc_verified: bool | None = None,
) -> Customer:
    """
    Rastgele geçerli TR müşterisi üret.

    Args:
        segment: Belirli segment (default: dağılıma göre rastgele)
        age_range: (min, max) yaş aralığı
        city: Şehir (default: dağılıma göre)
        kyc_verified: KYC durumu (default: rastgele, %95 true)
    """
    if segment is None:
        segment_enum = _weighted_choice(list(_SEGMENT_WEIGHTS.items()))
    elif isinstance(segment, str):
        segment_enum = CustomerSegment(segment)
    else:
        segment_enum = segment

    gender = random.choice(["M", "F"])
    if gender == "M":
        first_name = random.choice(_FIRST_NAMES_MALE)
    else:
        first_name = random.choice(_FIRST_NAMES_FEMALE)
    last_name = random.choice(_LAST_NAMES)

    bd = _random_birth_date(*age_range)
    phone = generate_phone_tr()
    email = _generate_email(first_name, last_name)

    if city is None:
        city = _weighted_choice(_CITIES)

    income_range = _SEGMENT_INCOME_RANGE[segment_enum]
    income = round(random.uniform(*income_range), 2)

    today = date.today()
    age = today.year - bd.year

    risk = _risk_score(segment_enum, age, income)

    return Customer(
        id=str(uuid4()),
        tckn=generate_tckn(),
        first_name=first_name,
        last_name=last_name,
        birth_date=bd,
        gender=gender,
        phone=phone,
        email=email,
        city=city,
        segment=segment_enum,
        income=income,
        risk_score=risk,
        kyc_verified=kyc_verified if kyc_verified is not None else random.random() > 0.05,
    )
