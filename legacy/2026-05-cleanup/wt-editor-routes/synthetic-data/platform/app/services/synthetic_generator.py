"""
Sentetik Veri Üretim Motoru — SyntheticDataGenerator Modülü.

SchemaAnalyzer, ColumnClassifier, RuleInferenceEngine ve RelationshipInference
sonuçlarını kullanarak gerçekçi Türk bankacılık sentetik verisi üretir.

Yetenekler:
  - Faker tr_TR ile Türkçe kişisel veri üretimi (isim, TCKN, IBAN, telefon, email, adres)
  - Kural bazlı üretim (RANGE, ENUM, REGEX, DISTRIBUTION, NOT_NULL, UNIQUE, LENGTH)
  - İlişkisel üretim (topological sort, FK bütünlüğü, kardinalite)
  - Dağılım koruma (histogram sampling, frekans bazlı seçim)
  - Çoklu export formatı (DataFrame, CSV, JSON, SQL INSERT)
  - Batch/chunk bazlı üretim ve progress tracking
  - Kalite kontrolü (kural uygunluk, FK bütünlük, istatistik karşılaştırma)
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import math
import os
import random
import re
import string
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd
from faker import Faker

from app.config import settings
from app.models.dataset import (
    Cardinality,
    GenerationStatus,
    RuleType,
)
from app.services.column_classifier import SemanticType
from app.services.relationship_inference import (
    RelationshipCandidate,
    RelationshipGraph,
)
from app.services.rule_engine import InferredRuleResult

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Sabitler — Türk Bankacılık Domain Verileri
# ═══════════════════════════════════════════════════════════════════════

# Türk şehirleri ve ilçeleri (ağırlıklı — büyükşehir nüfus oranı)
_TURKISH_CITIES: list[dict[str, Any]] = [
    {"name": "İstanbul", "weight": 0.19, "districts": ["Kadıköy", "Beşiktaş", "Üsküdar", "Şişli", "Bakırköy", "Ataşehir", "Kartal", "Maltepe", "Beyoğlu", "Fatih"]},
    {"name": "Ankara", "weight": 0.07, "districts": ["Çankaya", "Keçiören", "Yenimahalle", "Mamak", "Etimesgut", "Sincan"]},
    {"name": "İzmir", "weight": 0.05, "districts": ["Konak", "Karşıyaka", "Bornova", "Buca", "Bayraklı", "Çiğli"]},
    {"name": "Bursa", "weight": 0.04, "districts": ["Osmangazi", "Nilüfer", "Yıldırım", "Mudanya"]},
    {"name": "Antalya", "weight": 0.03, "districts": ["Muratpaşa", "Konyaaltı", "Kepez", "Lara"]},
    {"name": "Adana", "weight": 0.03, "districts": ["Seyhan", "Çukurova", "Yüreğir", "Sarıçam"]},
    {"name": "Konya", "weight": 0.03, "districts": ["Selçuklu", "Meram", "Karatay"]},
    {"name": "Gaziantep", "weight": 0.025, "districts": ["Şahinbey", "Şehitkâmil", "Oğuzeli"]},
    {"name": "Mersin", "weight": 0.025, "districts": ["Mezitli", "Yenişehir", "Toroslar", "Akdeniz"]},
    {"name": "Kayseri", "weight": 0.02, "districts": ["Melikgazi", "Kocasinan", "Talas"]},
    {"name": "Eskişehir", "weight": 0.01, "districts": ["Odunpazarı", "Tepebaşı"]},
    {"name": "Diyarbakır", "weight": 0.02, "districts": ["Bağlar", "Kayapınar", "Yenişehir"]},
    {"name": "Samsun", "weight": 0.015, "districts": ["Atakum", "İlkadım", "Canik"]},
    {"name": "Trabzon", "weight": 0.01, "districts": ["Ortahisar", "Akçaabat", "Yomra"]},
    {"name": "Denizli", "weight": 0.01, "districts": ["Merkezefendi", "Pamukkale"]},
    {"name": "Kocaeli", "weight": 0.025, "districts": ["İzmit", "Gebze", "Darıca", "Körfez"]},
    {"name": "Sakarya", "weight": 0.01, "districts": ["Adapazarı", "Serdivan", "Erenler"]},
    {"name": "Tekirdağ", "weight": 0.01, "districts": ["Süleymanpaşa", "Çorlu", "Çerkezköy"]},
    {"name": "Malatya", "weight": 0.01, "districts": ["Battalgazi", "Yeşilyurt"]},
    {"name": "Manisa", "weight": 0.015, "districts": ["Yunusemre", "Şehzadeler", "Akhisar"]},
]

# Bankacılık segment ve tip sabitleri
_SEGMENTS: list[dict[str, float]] = [
    {"value": "Bireysel", "weight": 0.45},
    {"value": "KOBİ", "weight": 0.20},
    {"value": "Ticari", "weight": 0.15},
    {"value": "Kurumsal", "weight": 0.10},
    {"value": "Platinum", "weight": 0.05},
    {"value": "VIP", "weight": 0.05},
]

_ACCOUNT_TYPES: list[dict[str, float]] = [
    {"value": "Vadesiz", "weight": 0.35},
    {"value": "Vadeli", "weight": 0.25},
    {"value": "Tasarruf", "weight": 0.15},
    {"value": "Yatırım", "weight": 0.10},
    {"value": "Kredi", "weight": 0.10},
    {"value": "Cari", "weight": 0.05},
]

_ACCOUNT_STATUSES: list[dict[str, float]] = [
    {"value": "Aktif", "weight": 0.75},
    {"value": "Pasif", "weight": 0.10},
    {"value": "Kapalı", "weight": 0.08},
    {"value": "Dondurulmuş", "weight": 0.04},
    {"value": "Blokeli", "weight": 0.03},
]

_TRANSACTION_TYPES: list[dict[str, float]] = [
    {"value": "Havale", "weight": 0.20},
    {"value": "EFT", "weight": 0.20},
    {"value": "Virman", "weight": 0.10},
    {"value": "ATM Çekim", "weight": 0.15},
    {"value": "POS", "weight": 0.15},
    {"value": "Ödeme", "weight": 0.10},
    {"value": "Yatırma", "weight": 0.05},
    {"value": "Faiz", "weight": 0.03},
    {"value": "Komisyon", "weight": 0.02},
]

_CHANNELS: list[dict[str, float]] = [
    {"value": "İnternet Bankacılığı", "weight": 0.30},
    {"value": "Mobil", "weight": 0.35},
    {"value": "Şube", "weight": 0.15},
    {"value": "ATM", "weight": 0.10},
    {"value": "Çağrı Merkezi", "weight": 0.05},
    {"value": "API", "weight": 0.05},
]

_CURRENCIES: list[dict[str, float]] = [
    {"value": "TRY", "weight": 0.80},
    {"value": "USD", "weight": 0.10},
    {"value": "EUR", "weight": 0.07},
    {"value": "GBP", "weight": 0.03},
]

_CUSTOMER_TYPES: list[dict[str, float]] = [
    {"value": "Bireysel", "weight": 0.70},
    {"value": "Tüzel", "weight": 0.30},
]


# ═══════════════════════════════════════════════════════════════════════
# Sonuç Dataclass'ları
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class GenerationProgress:
    """Üretim ilerleme bilgisi."""

    table_name: str                          # Tablo adı
    total_rows: int = 0                      # Hedef satır sayısı
    generated_rows: int = 0                  # Üretilen satır sayısı
    current_chunk: int = 0                   # Mevcut chunk numarası
    total_chunks: int = 0                    # Toplam chunk sayısı
    status: str = "pending"                  # pending, running, completed, failed
    error_message: str = ""                  # Hata mesajı (varsa)
    elapsed_seconds: float = 0.0            # Geçen süre

    @property
    def progress_percent(self) -> float:
        """Yüzde olarak ilerleme."""
        if self.total_rows == 0:
            return 0.0
        return min((self.generated_rows / self.total_rows) * 100.0, 100.0)


@dataclass
class QualityReport:
    """Kalite kontrol raporu."""

    table_name: str
    total_rows: int = 0
    rule_compliance: dict[str, Any] = field(default_factory=dict)    # Kural uygunluk oranları
    fk_integrity: dict[str, Any] = field(default_factory=dict)       # FK bütünlük kontrolü
    statistics_comparison: dict[str, Any] = field(default_factory=dict)  # İstatistik karşılaştırma
    overall_score: float = 0.0               # Genel kalite skoru (0-100)

    def to_dict(self) -> dict[str, Any]:
        """JSON serializable dict'e dönüştürür."""
        return {
            "table_name": self.table_name,
            "total_rows": self.total_rows,
            "rule_compliance": self.rule_compliance,
            "fk_integrity": self.fk_integrity,
            "statistics_comparison": self.statistics_comparison,
            "overall_score": round(self.overall_score, 2),
        }


@dataclass
class GenerationResult:
    """Üretim sonucu — tüm tablolar için birleşik çıktı."""

    tables: dict[str, pd.DataFrame] = field(default_factory=dict)    # Tablo adı → DataFrame
    quality_reports: dict[str, QualityReport] = field(default_factory=dict)
    progress: dict[str, GenerationProgress] = field(default_factory=dict)
    generation_order: list[str] = field(default_factory=list)
    total_rows_generated: int = 0
    elapsed_seconds: float = 0.0

    def to_summary_dict(self) -> dict[str, Any]:
        """Özet bilgi dict'i döndürür."""
        return {
            "generation_order": self.generation_order,
            "total_rows_generated": self.total_rows_generated,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "tables": {
                name: {
                    "rows": len(df),
                    "columns": list(df.columns),
                }
                for name, df in self.tables.items()
            },
            "quality_reports": {
                name: report.to_dict()
                for name, report in self.quality_reports.items()
            },
        }


# ═══════════════════════════════════════════════════════════════════════
# Ana Sınıf — SyntheticDataGenerator
# ═══════════════════════════════════════════════════════════════════════


class SyntheticDataGenerator:
    """
    Sentetik Bankacılık Verisi Üretim Motoru.

    Türkçe bankacılık domain bilgisi, kural tabanlı üretim, ilişkisel
    bütünlük ve istatistiksel dağılım koruma yetenekleriyle donatılmış
    production-ready sentetik veri üreticisi.

    Kullanım:
        generator = SyntheticDataGenerator(seed=42)
        result = generator.generate(
            table_configs={"customers": {...}, "accounts": {...}},
            rules={"customers": [...], "accounts": [...]},
            relationships=[...],
            row_counts={"customers": 10000, "accounts": 30000},
        )
        generator.export_csv(result, output_dir="./output")
    """

    def __init__(
        self,
        seed: Optional[int] = None,
        locale: str = "tr_TR",
        batch_size: int = 1_000,
        max_unique_retries: int = 100,
    ) -> None:
        """
        SyntheticDataGenerator yapıcısı.

        Args:
            seed: Rastgelelik tohumu (tekrarlanabilirlik için)
            locale: Faker locale ayarı (varsayılan: tr_TR)
            batch_size: Chunk bazlı üretimde batch boyutu
            max_unique_retries: UNIQUE kural zorlamasında maksimum deneme
        """
        self.seed = seed
        self.locale = locale
        self.batch_size = batch_size or settings.DEFAULT_BATCH_SIZE
        self.max_unique_retries = max_unique_retries

        # Faker başlat — Türkçe locale
        self.fake = Faker(locale)
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)
            np.random.seed(seed)

        # Üretilen benzersiz değer havuzları — UNIQUE kısıtı için
        self._unique_pools: dict[str, set[Any]] = defaultdict(set)

        # FK referans havuzu — ilişkisel üretimde parent değerler
        self._fk_pools: dict[str, dict[str, list[Any]]] = defaultdict(dict)

        # İlerleme callback'i (opsiyonel)
        self._progress_callback: Optional[Callable[[GenerationProgress], None]] = None

        # Semantik tip → üretim fonksiyonu eşleştirmesi
        self._semantic_generators: dict[SemanticType, Callable[[], Any]] = {
            SemanticType.FIRST_NAME: self._gen_first_name,
            SemanticType.LAST_NAME: self._gen_last_name,
            SemanticType.FULL_NAME: self._gen_full_name,
            SemanticType.PERSON_NAME: self._gen_full_name,
            SemanticType.NATIONAL_ID: self._gen_tckn,
            SemanticType.IBAN: self._gen_iban,
            SemanticType.PHONE: self._gen_phone,
            SemanticType.EMAIL: self._gen_email,
            SemanticType.ADDRESS: self._gen_address,
            SemanticType.CITY: self._gen_city,
            SemanticType.DISTRICT: self._gen_district,
            SemanticType.CUSTOMER_ID: self._gen_customer_id,
            SemanticType.ACCOUNT_ID: self._gen_account_id,
            SemanticType.ACCOUNT_NUMBER: self._gen_account_number,
            SemanticType.CREDIT_CARD: self._gen_credit_card,
            SemanticType.BIRTH_DATE: self._gen_birth_date,
            SemanticType.AGE: self._gen_age,
            SemanticType.SEGMENT: lambda: self._gen_weighted_choice(_SEGMENTS),
            SemanticType.CUSTOMER_TYPE: lambda: self._gen_weighted_choice(_CUSTOMER_TYPES),
            SemanticType.ACCOUNT_TYPE: lambda: self._gen_weighted_choice(_ACCOUNT_TYPES),
            SemanticType.ACCOUNT_STATUS: lambda: self._gen_weighted_choice(_ACCOUNT_STATUSES),
            SemanticType.TRANSACTION_TYPE: lambda: self._gen_weighted_choice(_TRANSACTION_TYPES),
            SemanticType.CHANNEL: lambda: self._gen_weighted_choice(_CHANNELS),
            SemanticType.CURRENCY: lambda: self._gen_weighted_choice(_CURRENCIES),
            SemanticType.BALANCE: self._gen_balance,
            SemanticType.AMOUNT: self._gen_amount,
            SemanticType.CREDIT_SCORE: self._gen_credit_score,
            SemanticType.CARD_LIMIT: self._gen_card_limit,
            SemanticType.INTEREST_RATE: self._gen_interest_rate,
            SemanticType.BRANCH_CODE: self._gen_branch_code,
            SemanticType.TRANSACTION_DATE: self._gen_transaction_date,
            SemanticType.MATURITY_DATE: self._gen_maturity_date,
        }

        logger.info(
            "SyntheticDataGenerator başlatıldı — locale=%s, seed=%s, batch=%d",
            locale, seed, self.batch_size,
        )

    # ═══════════════════════════════════════════════════════════════════
    # 1. Temel Veri Üretimi — Faker tr_TR + Özel Generatorlar
    # ═══════════════════════════════════════════════════════════════════

    def _gen_first_name(self) -> str:
        """Türkçe isim üretir."""
        return self.fake.first_name()

    def _gen_last_name(self) -> str:
        """Türkçe soyisim üretir."""
        return self.fake.last_name()

    def _gen_full_name(self) -> str:
        """Türkçe ad-soyad üretir."""
        return f"{self.fake.first_name()} {self.fake.last_name()}"

    def _gen_tckn(self) -> str:
        """
        Geçerli TCKN (T.C. Kimlik Numarası) üretir.

        Algoritma:
        - 9 rastgele hane üret (ilk hane 0 olamaz)
        - 10. hane: ((d1+d3+d5+d7+d9)*7 - (d2+d4+d6+d8)) % 10
        - 11. hane: (d1+d2+...+d10) % 10
        """
        # İlk 9 hane — ilk hane 1-9 arası, diğerleri 0-9
        digits = [random.randint(1, 9)]
        for _ in range(8):
            digits.append(random.randint(0, 9))

        # 10. hane hesapla
        odd_sum = digits[0] + digits[2] + digits[4] + digits[6] + digits[8]
        even_sum = digits[1] + digits[3] + digits[5] + digits[7]
        d10 = (odd_sum * 7 - even_sum) % 10
        digits.append(d10)

        # 11. hane hesapla
        d11 = sum(digits) % 10
        digits.append(d11)

        return "".join(str(d) for d in digits)

    def _gen_iban(self) -> str:
        """
        Geçerli TR IBAN formatı üretir.

        Format: TR + 2 kontrol hanesi + 5 banka kodu + 1 anahtar + 16 hesap no
        Toplam: 26 karakter
        """
        # Banka kodu (5 hane) — bilinen Türk banka kodları
        bank_codes = ["00010", "00012", "00015", "00032", "00046",
                      "00062", "00064", "00067", "00099", "00103",
                      "00111", "00134", "00146", "00203", "00206"]
        bank_code = random.choice(bank_codes)

        # Hesap no kısmı (17 hane — 1 anahtar + 16 hesap)
        reserve_key = "0"
        account_no = "".join([str(random.randint(0, 9)) for _ in range(16)])
        bban = bank_code + reserve_key + account_no

        # Kontrol hanesi hesaplama (ISO 13616 — mod 97)
        # TR00 + BBAN → sayısal: BBAN + 2900 (T=29, R=27)
        numeric_str = bban + "292700"
        check = 98 - (int(numeric_str) % 97)
        check_digits = f"{check:02d}"

        return f"TR{check_digits}{bban}"

    def _gen_phone(self) -> str:
        """Türk cep telefonu numarası üretir (+90 5XX XXX XX XX)."""
        prefix = random.choice(["530", "531", "532", "533", "534", "535",
                                "536", "537", "538", "539", "540", "541",
                                "542", "543", "544", "545", "546", "547",
                                "548", "549", "550", "551", "552", "553",
                                "554", "555", "556", "557", "558", "559"])
        number = "".join([str(random.randint(0, 9)) for _ in range(7)])
        return f"+90{prefix}{number}"

    def _gen_email(self) -> str:
        """İsim bazlı email üretir (Türkçe karakter normalleştirmeli)."""
        first = self._normalize_turkish(self.fake.first_name().lower())
        last = self._normalize_turkish(self.fake.last_name().lower())
        domain = random.choice(["gmail.com", "hotmail.com", "outlook.com",
                                "yahoo.com", "yandex.com", "icloud.com",
                                "garanti.com.tr", "akbank.com.tr"])
        separator = random.choice([".", "_", ""])
        suffix = random.choice(["", str(random.randint(1, 99))])
        return f"{first}{separator}{last}{suffix}@{domain}"

    def _gen_address(self) -> str:
        """Türk formatında adres üretir."""
        city_data = self._pick_weighted_city()
        district = random.choice(city_data["districts"])
        street_no = random.randint(1, 150)
        apartment_no = random.randint(1, 30)
        mahalle = random.choice(["Cumhuriyet", "Atatürk", "Fatih", "Zafer",
                                 "Barbaros", "İnönü", "Mevlana", "Yunus Emre",
                                 "Gazi", "Şehitler"])
        return (
            f"{mahalle} Mah. {random.randint(1, 500)}. Sok. "
            f"No: {street_no}/{apartment_no} "
            f"{district}/{city_data['name']}"
        )

    def _gen_city(self) -> str:
        """Nüfus ağırlıklı Türk şehir adı üretir."""
        return self._pick_weighted_city()["name"]

    def _gen_district(self) -> str:
        """Ağırlıklı ilçe adı üretir."""
        city_data = self._pick_weighted_city()
        return random.choice(city_data["districts"])

    def _gen_customer_id(self) -> str:
        """Müşteri numarası üretir (MUS + 8 hane)."""
        return f"MUS{random.randint(10000000, 99999999)}"

    def _gen_account_id(self) -> str:
        """Hesap numarası üretir (HSP + 10 hane)."""
        return f"HSP{random.randint(1000000000, 9999999999)}"

    def _gen_account_number(self) -> str:
        """Banka hesap numarası üretir (16 hane)."""
        return "".join([str(random.randint(0, 9)) for _ in range(16)])

    def _gen_credit_card(self) -> str:
        """
        Luhn uyumlu kredi kartı numarası üretir (16 hane).

        Türk banka BIN aralıkları kullanılır.
        """
        # Türk banka BIN'leri (ilk 6 hane)
        bins = ["454360", "454361", "479610", "520048", "520049",
                "540668", "540667", "547287", "549220", "552879",
                "404591", "428220", "457562", "462732", "476713"]
        prefix = random.choice(bins)
        # Kalan haneleri rastgele üret (son hane hariç)
        body = prefix + "".join([str(random.randint(0, 9)) for _ in range(9)])
        # Luhn check digit hesapla
        digits_list = [int(d) for d in body]
        odd_digits = digits_list[-1::-2]
        even_digits = digits_list[-2::-2]
        total = sum(odd_digits)
        for d in even_digits:
            total += sum(divmod(d * 2, 10))
        check = (10 - (total % 10)) % 10
        return body + str(check)

    def _gen_birth_date(self) -> str:
        """Doğum tarihi üretir (18-80 yaş arası, ISO format)."""
        today = date.today()
        min_age, max_age = 18, 80
        start = today - timedelta(days=max_age * 365)
        end = today - timedelta(days=min_age * 365)
        delta = (end - start).days
        random_date = start + timedelta(days=random.randint(0, delta))
        return random_date.isoformat()

    def _gen_age(self) -> int:
        """Gerçekçi yaş dağılımı üretir (18-80, normal dağılım)."""
        age = int(np.random.normal(loc=38, scale=12))
        return max(18, min(80, age))

    def _gen_balance(self) -> float:
        """Hesap bakiyesi üretir (lognormal dağılım, TL)."""
        # Lognormal: çoğunluk düşük bakiye, az sayıda yüksek bakiye
        value = np.random.lognormal(mean=8.5, sigma=2.0)
        return round(max(0.0, min(value, 50_000_000.0)), 2)

    def _gen_amount(self) -> float:
        """İşlem tutarı üretir (lognormal dağılım)."""
        value = np.random.lognormal(mean=5.5, sigma=1.8)
        return round(max(0.01, min(value, 10_000_000.0)), 2)

    def _gen_credit_score(self) -> int:
        """Kredi skoru üretir (Findeks benzeri, 1-1900 arası)."""
        score = int(np.random.normal(loc=1100, scale=300))
        return max(1, min(1900, score))

    def _gen_card_limit(self) -> float:
        """Kart limiti üretir (lognormal)."""
        value = np.random.lognormal(mean=9.0, sigma=1.5)
        # Yuvarla — 500 TL'nin katlarına
        rounded = round(value / 500) * 500
        return float(max(500, min(rounded, 500_000)))

    def _gen_interest_rate(self) -> float:
        """Faiz oranı üretir (%0.5 — %50 arası, yıllık)."""
        rate = np.random.uniform(0.5, 50.0)
        return round(rate, 2)

    def _gen_branch_code(self) -> str:
        """Şube kodu üretir (4 hane)."""
        return f"{random.randint(1, 9999):04d}"

    def _gen_transaction_date(self) -> str:
        """İşlem tarihi üretir (son 2 yıl içinde, ISO format)."""
        today = date.today()
        start = today - timedelta(days=730)
        delta = (today - start).days
        random_date = start + timedelta(days=random.randint(0, delta))
        return random_date.isoformat()

    def _gen_maturity_date(self) -> str:
        """Vade tarihi üretir (bugünden 1-5 yıl sonra, ISO format)."""
        today = date.today()
        days_ahead = random.randint(30, 1825)  # 1 ay — 5 yıl
        return (today + timedelta(days=days_ahead)).isoformat()

    # ═══════════════════════════════════════════════════════════════════
    # Yardımcı Metotlar
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _normalize_turkish(text: str) -> str:
        """Türkçe karakterleri ASCII karşılıklarına dönüştürür."""
        tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
        return text.translate(tr_map)

    @staticmethod
    def _pick_weighted_city() -> dict[str, Any]:
        """Nüfus ağırlığına göre şehir seçer."""
        weights = [c["weight"] for c in _TURKISH_CITIES]
        total = sum(weights)
        normalized = [w / total for w in weights]
        idx = np.random.choice(len(_TURKISH_CITIES), p=normalized)
        return _TURKISH_CITIES[idx]

    @staticmethod
    def _gen_weighted_choice(options: list[dict[str, Any]]) -> str:
        """Ağırlıklı rastgele seçim yapar."""
        values = [o["value"] for o in options]
        weights = [o["weight"] for o in options]
        total = sum(weights)
        normalized = [w / total for w in weights]
        return np.random.choice(values, p=normalized)

    def _gen_value_by_semantic_type(self, semantic_type: Optional[SemanticType]) -> Any:
        """Semantik tipe göre değer üretir."""
        if semantic_type is None or semantic_type == SemanticType.UNKNOWN:
            return self.fake.word()
        gen_func = self._semantic_generators.get(semantic_type)
        if gen_func:
            return gen_func()
        return self.fake.word()

    # ═══════════════════════════════════════════════════════════════════
    # 2. Kurala Dayalı Üretim
    # ═══════════════════════════════════════════════════════════════════

    def _apply_range_rule(self, rule_def: dict[str, Any], data_type: str = "float") -> Any:
        """
        RANGE kuralına uygun değer üretir.

        Desteklenen dağılım türleri: uniform, normal, lognormal.
        Min-max sınırları garanti edilir.
        """
        min_val = rule_def.get("min", 0)
        max_val = rule_def.get("max", 100)
        distribution = rule_def.get("distribution", "uniform")
        mean = rule_def.get("mean")
        std = rule_def.get("std")

        if distribution == "normal" and mean is not None and std is not None:
            value = np.random.normal(loc=mean, scale=std)
        elif distribution == "lognormal" and mean is not None and std is not None:
            value = np.random.lognormal(mean=mean, sigma=std)
        elif distribution == "exponential":
            scale = rule_def.get("scale", 1.0)
            value = np.random.exponential(scale=scale) + min_val
        else:
            # Uniform dağılım
            value = np.random.uniform(min_val, max_val)

        # Sınırları uygula
        value = max(min_val, min(value, max_val))

        if data_type in ("integer", "int"):
            return int(round(value))
        return round(float(value), 2)

    def _apply_enum_rule(self, rule_def: dict[str, Any]) -> Any:
        """
        ENUM kuralına uygun değer üretir.

        Frekans bilgisi varsa ağırlıklı, yoksa eşit olasılıklı seçim yapar.
        """
        values = rule_def.get("values", [])
        frequencies = rule_def.get("frequencies", {})

        if not values:
            return None

        if frequencies:
            # Frekans ağırlıklı seçim
            weights = [frequencies.get(str(v), 1.0) for v in values]
            total = sum(weights)
            if total > 0:
                normalized = [w / total for w in weights]
                return np.random.choice(values, p=normalized)

        return random.choice(values)

    def _apply_regex_rule(self, rule_def: dict[str, Any]) -> str:
        """
        REGEX kuralına uygun string üretir.

        Bilinen bankacılık pattern'ları için özel üretim,
        genel regex için basit karakter sınıfı tabanlı üretim.
        """
        pattern = rule_def.get("pattern", "")

        # Bilinen pattern'lar için özel üretim
        if "tckn" in pattern.lower() or pattern == r"^\d{11}$":
            return self._gen_tckn()
        if "iban" in pattern.lower() or "TR" in pattern:
            return self._gen_iban()
        if "phone" in pattern.lower() or "+90" in pattern:
            return self._gen_phone()
        if "email" in pattern.lower() or "@" in pattern:
            return self._gen_email()

        # Genel regex — basit karakter sınıfı üretimi
        return self._gen_from_simple_regex(pattern)

    def _gen_from_simple_regex(self, pattern: str) -> str:
        """Basit regex pattern'ından string üretir."""
        result = []
        i = 0
        while i < len(pattern):
            ch = pattern[i]
            if ch == '\\' and i + 1 < len(pattern):
                next_ch = pattern[i + 1]
                if next_ch == 'd':
                    result.append(str(random.randint(0, 9)))
                elif next_ch == 'w':
                    result.append(random.choice(string.ascii_lowercase + string.digits))
                elif next_ch == 's':
                    result.append(' ')
                else:
                    result.append(next_ch)
                i += 2
            elif ch == '[':
                # Karakter sınıfı — kapanış bracket'ına kadar oku
                j = pattern.find(']', i)
                if j == -1:
                    result.append(ch)
                    i += 1
                else:
                    char_class = pattern[i + 1:j]
                    # Basit karakter aralığı: a-z, 0-9
                    chars = self._expand_char_class(char_class)
                    if chars:
                        result.append(random.choice(chars))
                    i = j + 1
            elif ch in ('^', '$', '(', ')', '|', '+', '?', '*', '.'):
                # Özel karakterleri atla veya basit işle
                if ch == '.':
                    result.append(random.choice(string.ascii_lowercase + string.digits))
                i += 1
            elif ch == '{':
                # Tekrar sayısı: {n} veya {n,m}
                j = pattern.find('}', i)
                if j != -1:
                    repeat_str = pattern[i + 1:j]
                    parts = repeat_str.split(',')
                    try:
                        if len(parts) == 1:
                            count = int(parts[0]) - 1  # -1: zaten bir tane ürettik
                        else:
                            count = random.randint(int(parts[0]), int(parts[1].strip() or parts[0])) - 1
                        if result:
                            last_char_gen = result[-1]
                            for _ in range(max(0, count)):
                                result.append(last_char_gen)
                    except (ValueError, IndexError):
                        pass
                    i = j + 1
                else:
                    i += 1
            else:
                result.append(ch)
                i += 1

        return "".join(result)

    @staticmethod
    def _expand_char_class(char_class: str) -> list[str]:
        """Regex karakter sınıfını genişletir (ör. a-z → [a,b,c,...,z])."""
        chars: list[str] = []
        i = 0
        while i < len(char_class):
            if i + 2 < len(char_class) and char_class[i + 1] == '-':
                start = ord(char_class[i])
                end = ord(char_class[i + 2])
                for c in range(start, end + 1):
                    chars.append(chr(c))
                i += 3
            else:
                chars.append(char_class[i])
                i += 1
        return chars

    def _apply_distribution_rule(self, rule_def: dict[str, Any]) -> float:
        """
        DISTRIBUTION kuralına uygun sayısal değer üretir.

        Desteklenen dağılımlar: normal, lognormal, uniform, exponential.
        """
        dist_type = rule_def.get("type", "normal")
        params = rule_def.get("params", {})

        if dist_type == "normal":
            mean = params.get("mean", 0.0)
            std = params.get("std", 1.0)
            value = np.random.normal(loc=mean, scale=std)
        elif dist_type == "lognormal":
            mean = params.get("mean", 0.0)
            sigma = params.get("sigma", 1.0)
            value = np.random.lognormal(mean=mean, sigma=sigma)
        elif dist_type == "uniform":
            low = params.get("low", 0.0)
            high = params.get("high", 1.0)
            value = np.random.uniform(low, high)
        elif dist_type == "exponential":
            scale = params.get("scale", 1.0)
            value = np.random.exponential(scale=scale)
        else:
            value = np.random.normal(loc=0, scale=1)

        # Sınır kontrolü
        min_val = rule_def.get("min")
        max_val = rule_def.get("max")
        if min_val is not None:
            value = max(float(min_val), value)
        if max_val is not None:
            value = min(float(max_val), value)

        return round(float(value), 2)

    def _apply_rules_to_value(
        self,
        value: Any,
        column_name: str,
        table_name: str,
        rules: list[InferredRuleResult],
        data_type: str = "string",
        semantic_type: Optional[SemanticType] = None,
    ) -> Any:
        """
        Üretilen değere tüm kuralları sırasıyla uygular.

        Kural önceliği: ENUM > REGEX > RANGE > DISTRIBUTION > LENGTH > NOT_NULL > UNIQUE
        """
        for rule in rules:
            if rule.column_name != column_name or not rule.is_active:
                continue

            rule_type = rule.rule_type.upper()
            defn = rule.definition

            if rule_type == "ENUM":
                value = self._apply_enum_rule(defn)
            elif rule_type == "REGEX":
                value = self._apply_regex_rule(defn)
            elif rule_type == "RANGE":
                value = self._apply_range_rule(defn, data_type)
            elif rule_type == "DISTRIBUTION":
                value = self._apply_distribution_rule(defn)
            elif rule_type == "LENGTH":
                # String uzunluk kısıtı
                min_len = defn.get("min_length", 0)
                max_len = defn.get("max_length", 255)
                if isinstance(value, str):
                    if len(value) < min_len:
                        value = value.ljust(min_len, "x")
                    if len(value) > max_len:
                        value = value[:max_len]
            elif rule_type == "NOT_NULL":
                # None ise semantik tipe göre yeniden üret
                if value is None:
                    value = self._gen_value_by_semantic_type(semantic_type)

        return value

    # ═══════════════════════════════════════════════════════════════════
    # 3. İlişkisel Veri Üretimi
    # ═══════════════════════════════════════════════════════════════════

    def _determine_generation_order(
        self,
        table_names: list[str],
        relationships: list[RelationshipCandidate],
    ) -> list[str]:
        """
        Topological sort ile tablo üretim sırasını belirler.

        Parent tablolar child'lardan önce üretilir.
        Döngü varsa kalan tablolar sona eklenir.

        Args:
            table_names: Tablo adları listesi
            relationships: İlişki adayları

        Returns:
            Sıralı tablo adları listesi
        """
        # Adjacency list ve in-degree hesapla
        adj: dict[str, list[str]] = defaultdict(list)
        in_deg: dict[str, int] = {name: 0 for name in table_names}

        for rel in relationships:
            parent = rel.source_dataset_name
            child = rel.target_dataset_name
            if parent in in_deg and child in in_deg:
                adj[parent].append(child)
                in_deg[child] = in_deg.get(child, 0) + 1

        # Kahn algoritması — BFS topological sort
        from collections import deque
        queue: deque[str] = deque()
        for name in table_names:
            if in_deg.get(name, 0) == 0:
                queue.append(name)

        order: list[str] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in adj.get(node, []):
                in_deg[neighbor] -= 1
                if in_deg[neighbor] == 0:
                    queue.append(neighbor)

        # Döngüdeki tablolar — sona ekle
        remaining = [n for n in table_names if n not in order]
        if remaining:
            logger.warning(
                "Döngüsel bağımlılık tespit edildi — %d tablo sona eklendi: %s",
                len(remaining), remaining,
            )
            order.extend(remaining)

        logger.info("Üretim sırası belirlendi: %s", order)
        return order

    def _resolve_fk_value(
        self,
        table_name: str,
        column_name: str,
        relationships: list[RelationshipCandidate],
    ) -> Optional[Any]:
        """
        FK kolonları için parent tablodan referans değer çeker.

        Args:
            table_name: Mevcut tablo adı (child)
            column_name: FK kolon adı
            relationships: İlişki listesi

        Returns:
            Parent tablodan rastgele bir değer veya None
        """
        for rel in relationships:
            child_name = rel.target_dataset_name
            child_col = rel.target_column

            if child_name == table_name and child_col == column_name:
                parent_name = rel.source_dataset_name
                parent_col = rel.source_column

                pool = self._fk_pools.get(parent_name, {}).get(parent_col, [])
                if pool:
                    return random.choice(pool)
                else:
                    logger.warning(
                        "FK havuzu boş — %s.%s → %s.%s",
                        table_name, column_name, parent_name, parent_col,
                    )
        return None

    def _get_cardinality_count(
        self,
        parent_table: str,
        child_table: str,
        relationships: list[RelationshipCandidate],
    ) -> tuple[int, int]:
        """
        İlişki kardinalitesine göre child sayı aralığını döndürür.

        Returns:
            (min_count, max_count) tuple'ı
        """
        for rel in relationships:
            if (rel.source_dataset_name == parent_table and
                    rel.target_dataset_name == child_table):
                card = rel.cardinality
                if card == Cardinality.ONE_TO_ONE:
                    return (1, 1)
                elif card == Cardinality.ONE_TO_MANY:
                    # Bankacılık domain: müşteri→hesap(1-5), hesap→işlem(0-50)
                    if "transaction" in child_table.lower() or "islem" in child_table.lower():
                        return (0, 50)
                    elif "account" in child_table.lower() or "hesap" in child_table.lower():
                        return (1, 5)
                    elif "card" in child_table.lower() or "kart" in child_table.lower():
                        return (0, 3)
                    return (1, 10)
                elif card == Cardinality.MANY_TO_MANY:
                    return (0, 20)
        return (1, 5)  # Varsayılan

    # ═══════════════════════════════════════════════════════════════════
    # 4. Dağılım Koruma — Histogram Sampling
    # ═══════════════════════════════════════════════════════════════════

    def _sample_from_histogram(
        self,
        histogram: dict[str, Any],
        n: int = 1,
    ) -> list[float]:
        """
        Histogram bazlı örnekleme ile orijinal dağılımı koruyarak değer üretir.

        Args:
            histogram: {"bin_edges": [...], "counts": [...]} formatında histogram
            n: Üretilecek değer sayısı

        Returns:
            Üretilen değerler listesi
        """
        bin_edges = histogram.get("bin_edges", [])
        counts = histogram.get("counts", [])

        if not bin_edges or not counts or len(bin_edges) < 2:
            return [np.random.normal() for _ in range(n)]

        # Olasılık dağılımı hesapla
        total = sum(counts)
        if total == 0:
            return [np.random.uniform(bin_edges[0], bin_edges[-1]) for _ in range(n)]

        probs = [c / total for c in counts]
        values: list[float] = []

        for _ in range(n):
            # Ağırlıklı bin seçimi
            bin_idx = np.random.choice(len(counts), p=probs)
            # Seçilen bin içinde uniform örnekleme
            low = bin_edges[bin_idx]
            high = bin_edges[min(bin_idx + 1, len(bin_edges) - 1)]
            values.append(float(np.random.uniform(low, high)))

        return values

    def _sample_from_frequency(
        self,
        frequency: dict[str, float],
        n: int = 1,
    ) -> list[str]:
        """
        Frekans tablosundan ağırlıklı örnekleme yapar.

        Args:
            frequency: {değer: frekans} eşleştirmesi
            n: Üretilecek değer sayısı

        Returns:
            Üretilen değerler listesi
        """
        if not frequency:
            return [self.fake.word() for _ in range(n)]

        values = list(frequency.keys())
        weights = list(frequency.values())
        total = sum(weights)
        if total == 0:
            return [random.choice(values) for _ in range(n)]

        probs = [w / total for w in weights]
        return list(np.random.choice(values, size=n, p=probs))

    # ═══════════════════════════════════════════════════════════════════
    # 5. Ana Üretim Pipeline
    # ═══════════════════════════════════════════════════════════════════

    def generate(
        self,
        table_configs: dict[str, dict[str, Any]],
        rules: Optional[dict[str, list[InferredRuleResult]]] = None,
        relationships: Optional[list[RelationshipCandidate]] = None,
        row_counts: Optional[dict[str, int]] = None,
        progress_callback: Optional[Callable[[GenerationProgress], None]] = None,
    ) -> GenerationResult:
        """
        Tüm tablolar için sentetik veri üretir.

        Args:
            table_configs: Tablo konfigürasyonları
                {tablo_adı: {
                    "columns": [
                        {"name": "col1", "data_type": "string", "semantic_type": "first_name",
                         "nullable": False, "statistics": {...}},
                        ...
                    ]
                }}
            rules: Tablo bazlı kural listeleri {tablo_adı: [InferredRuleResult, ...]}
            relationships: İlişki adayları listesi
            row_counts: Tablo bazlı satır sayıları {tablo_adı: N}
            progress_callback: İlerleme bildirimi callback'i

        Returns:
            GenerationResult nesnesi
        """
        import time
        start_time = time.time()

        self._progress_callback = progress_callback
        rules = rules or {}
        relationships = relationships or []
        row_counts = row_counts or {}
        result = GenerationResult()

        # Üretim sırasını belirle (topological sort)
        table_names = list(table_configs.keys())
        generation_order = self._determine_generation_order(table_names, relationships)
        result.generation_order = generation_order

        # Her tablo için üretim yap
        for table_name in generation_order:
            config = table_configs.get(table_name, {})
            target_rows = row_counts.get(table_name, settings.DEFAULT_BATCH_SIZE)
            table_rules = rules.get(table_name, [])

            logger.info(
                "Tablo üretimi başlıyor: %s (%d satır)", table_name, target_rows,
            )

            try:
                df = self._generate_table(
                    table_name=table_name,
                    config=config,
                    rules=table_rules,
                    relationships=relationships,
                    target_rows=target_rows,
                )
                result.tables[table_name] = df
                result.total_rows_generated += len(df)

                # FK havuzunu güncelle — sonraki child tablolar için
                self._update_fk_pool(table_name, df, relationships)

                logger.info(
                    "Tablo üretimi tamamlandı: %s → %d satır", table_name, len(df),
                )

            except Exception as e:
                logger.error("Tablo üretimi hatası [%s]: %s", table_name, str(e))
                result.progress[table_name] = GenerationProgress(
                    table_name=table_name,
                    status="failed",
                    error_message=str(e),
                )

        result.elapsed_seconds = time.time() - start_time

        logger.info(
            "Üretim tamamlandı — %d tablo, %d toplam satır, %.2f saniye",
            len(result.tables), result.total_rows_generated, result.elapsed_seconds,
        )

        return result

    def _generate_table(
        self,
        table_name: str,
        config: dict[str, Any],
        rules: list[InferredRuleResult],
        relationships: list[RelationshipCandidate],
        target_rows: int,
    ) -> pd.DataFrame:
        """
        Tek bir tablo için sentetik veri üretir (chunk bazlı).

        Args:
            table_name: Tablo adı
            config: Kolon konfigürasyonları
            rules: Uygulanan kurallar
            relationships: İlişki bilgileri
            target_rows: Hedef satır sayısı

        Returns:
            Üretilen DataFrame
        """
        columns = config.get("columns", [])
        if not columns:
            logger.warning("Tablo '%s' için kolon konfigürasyonu bulunamadı", table_name)
            return pd.DataFrame()

        # Chunk bazlı üretim
        total_chunks = math.ceil(target_rows / self.batch_size)
        all_chunks: list[pd.DataFrame] = []
        generated = 0

        progress = GenerationProgress(
            table_name=table_name,
            total_rows=target_rows,
            total_chunks=total_chunks,
            status="running",
        )

        for chunk_idx in range(total_chunks):
            chunk_size = min(self.batch_size, target_rows - generated)
            chunk_data = self._generate_chunk(
                table_name=table_name,
                columns=columns,
                rules=rules,
                relationships=relationships,
                chunk_size=chunk_size,
            )
            all_chunks.append(chunk_data)
            generated += len(chunk_data)

            # Progress güncelle
            progress.generated_rows = generated
            progress.current_chunk = chunk_idx + 1
            if self._progress_callback:
                self._progress_callback(progress)

        # Tüm chunk'ları birleştir
        if all_chunks:
            df = pd.concat(all_chunks, ignore_index=True)
        else:
            df = pd.DataFrame()

        progress.status = "completed"
        if self._progress_callback:
            self._progress_callback(progress)

        return df

    def _generate_chunk(
        self,
        table_name: str,
        columns: list[dict[str, Any]],
        rules: list[InferredRuleResult],
        relationships: list[RelationshipCandidate],
        chunk_size: int,
    ) -> pd.DataFrame:
        """
        Tek bir chunk (batch) veri üretir.

        Args:
            table_name: Tablo adı
            columns: Kolon bilgileri
            rules: Kurallar
            relationships: İlişkiler
            chunk_size: Üretilecek satır sayısı

        Returns:
            Chunk DataFrame'i
        """
        data: dict[str, list[Any]] = {}

        for col_info in columns:
            col_name = col_info["name"]
            data_type = col_info.get("data_type", "string")
            semantic_type_str = col_info.get("semantic_type")
            nullable = col_info.get("nullable", True)
            null_ratio = col_info.get("null_ratio", 0.0)
            statistics = col_info.get("statistics", {})

            # SemanticType enum'a dönüştür
            semantic_type: Optional[SemanticType] = None
            if semantic_type_str:
                try:
                    semantic_type = SemanticType(semantic_type_str)
                except (ValueError, KeyError):
                    pass

            # Kolon değerlerini üret
            col_values = self._generate_column_values(
                table_name=table_name,
                col_name=col_name,
                data_type=data_type,
                semantic_type=semantic_type,
                rules=rules,
                relationships=relationships,
                statistics=statistics,
                chunk_size=chunk_size,
                nullable=nullable,
                null_ratio=null_ratio,
            )
            data[col_name] = col_values

        return pd.DataFrame(data)

    def _generate_column_values(
        self,
        table_name: str,
        col_name: str,
        data_type: str,
        semantic_type: Optional[SemanticType],
        rules: list[InferredRuleResult],
        relationships: list[RelationshipCandidate],
        statistics: dict[str, Any],
        chunk_size: int,
        nullable: bool = True,
        null_ratio: float = 0.0,
    ) -> list[Any]:
        """
        Tek bir kolon için tüm değerleri üretir.

        Öncelik sırası:
        1. FK referansı (ilişkisel bütünlük)
        2. Histogram/frekans bazlı sampling (dağılım koruma)
        3. Kural bazlı üretim
        4. Semantik tip bazlı üretim
        5. Genel tip bazlı üretim

        Args:
            Çoklu parametreler — kolon konfigürasyonu ve kural bilgisi

        Returns:
            Üretilen değerler listesi
        """
        values: list[Any] = []

        # 1. FK referans kontrolü
        is_fk = self._is_fk_column(table_name, col_name, relationships)

        # 2. Kolon için geçerli kuralları filtrele
        col_rules = [r for r in rules if r.column_name == col_name and r.is_active]

        # UNIQUE kuralı var mı?
        has_unique = any(r.rule_type.upper() == "UNIQUE" for r in col_rules)

        # Histogram veya frekans bilgisi var mı?
        histogram = statistics.get("histogram")
        frequency = statistics.get("frequency", statistics.get("most_common_values"))

        for i in range(chunk_size):
            value: Any = None

            # FK değeri — parent tablodan çek
            if is_fk:
                value = self._resolve_fk_value(table_name, col_name, relationships)

            # Histogram bazlı sampling
            elif histogram and data_type in ("float", "decimal", "integer"):
                sampled = self._sample_from_histogram(histogram, n=1)
                value = sampled[0] if sampled else None
                if data_type == "integer" and value is not None:
                    value = int(round(value))

            # Frekans bazlı sampling (kategorik)
            elif frequency and isinstance(frequency, dict) and data_type == "string":
                sampled = self._sample_from_frequency(frequency, n=1)
                value = sampled[0] if sampled else None

            # Semantik tip bazlı üretim
            elif semantic_type and semantic_type != SemanticType.UNKNOWN:
                value = self._gen_value_by_semantic_type(semantic_type)

            # Genel tip bazlı üretim
            else:
                value = self._gen_by_data_type(data_type)

            # Kural uygula
            if col_rules:
                value = self._apply_rules_to_value(
                    value, col_name, table_name, col_rules, data_type, semantic_type,
                )

            # UNIQUE kontrolü
            if has_unique:
                pool_key = f"{table_name}.{col_name}"
                retries = 0
                while value in self._unique_pools[pool_key] and retries < self.max_unique_retries:
                    if semantic_type and semantic_type != SemanticType.UNKNOWN:
                        value = self._gen_value_by_semantic_type(semantic_type)
                    else:
                        value = self._gen_by_data_type(data_type)
                    if col_rules:
                        value = self._apply_rules_to_value(
                            value, col_name, table_name, col_rules, data_type, semantic_type,
                        )
                    retries += 1
                self._unique_pools[pool_key].add(value)

            # NULL enjeksiyonu
            if nullable and null_ratio > 0 and not is_fk:
                if random.random() < null_ratio:
                    # NOT_NULL kuralı varsa NULL yapma
                    if not any(r.rule_type.upper() == "NOT_NULL" for r in col_rules):
                        value = None

            values.append(value)

        return values

    def _is_fk_column(
        self,
        table_name: str,
        column_name: str,
        relationships: list[RelationshipCandidate],
    ) -> bool:
        """FK kolonu olup olmadığını kontrol eder."""
        for rel in relationships:
            if (rel.target_dataset_name == table_name and
                    rel.target_column == column_name):
                return True
        return False

    def _gen_by_data_type(self, data_type: str) -> Any:
        """Genel veri tipine göre rastgele değer üretir."""
        dt = data_type.lower()
        if dt in ("integer", "int", "bigint", "smallint"):
            return random.randint(1, 100000)
        elif dt in ("float", "double", "decimal", "numeric"):
            return round(random.uniform(0.0, 100000.0), 2)
        elif dt in ("boolean", "bool"):
            return random.choice([True, False])
        elif dt in ("date",):
            return self._gen_transaction_date()
        elif dt in ("datetime", "timestamp"):
            d = self._gen_transaction_date()
            return f"{d}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:00"
        else:
            return self.fake.word()

    def _update_fk_pool(
        self,
        table_name: str,
        df: pd.DataFrame,
        relationships: list[RelationshipCandidate],
    ) -> None:
        """
        Üretilen tablodan FK havuzunu günceller.

        Parent tablonun PK/unique kolonlarını havuza ekler,
        böylece child tablolar referans alabilir.
        """
        for rel in relationships:
            if rel.source_dataset_name == table_name:
                col = rel.source_column
                if col in df.columns:
                    pool_values = df[col].dropna().unique().tolist()
                    if table_name not in self._fk_pools:
                        self._fk_pools[table_name] = {}
                    self._fk_pools[table_name][col] = pool_values
                    logger.debug(
                        "FK havuzu güncellendi: %s.%s → %d benzersiz değer",
                        table_name, col, len(pool_values),
                    )

    # ═══════════════════════════════════════════════════════════════════
    # 6. Export — DataFrame, CSV, JSON, SQL
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def export_csv(
        result: GenerationResult,
        output_dir: str,
        encoding: str = "utf-8",
        separator: str = ",",
    ) -> dict[str, str]:
        """
        Üretilen verileri CSV dosyalarına yazar.

        Args:
            result: Üretim sonucu
            output_dir: Çıktı klasörü
            encoding: Karakter kodlaması
            separator: Alan ayırıcı

        Returns:
            {tablo_adı: dosya_yolu} eşleştirmesi
        """
        os.makedirs(output_dir, exist_ok=True)
        paths: dict[str, str] = {}

        for table_name, df in result.tables.items():
            file_path = os.path.join(output_dir, f"{table_name}.csv")
            df.to_csv(file_path, index=False, encoding=encoding, sep=separator)
            paths[table_name] = file_path
            logger.info("CSV yazıldı: %s (%d satır)", file_path, len(df))

        return paths

    @staticmethod
    def export_json(
        result: GenerationResult,
        output_dir: str,
        encoding: str = "utf-8",
        orient: str = "records",
    ) -> dict[str, str]:
        """
        Üretilen verileri JSON dosyalarına yazar.

        Args:
            result: Üretim sonucu
            output_dir: Çıktı klasörü
            encoding: Karakter kodlaması
            orient: pandas JSON orient (records, columns, index, split)

        Returns:
            {tablo_adı: dosya_yolu} eşleştirmesi
        """
        os.makedirs(output_dir, exist_ok=True)
        paths: dict[str, str] = {}

        for table_name, df in result.tables.items():
            file_path = os.path.join(output_dir, f"{table_name}.json")
            df.to_json(
                file_path, orient=orient, force_ascii=False,
                indent=2, date_format="iso",
            )
            paths[table_name] = file_path
            logger.info("JSON yazıldı: %s (%d satır)", file_path, len(df))

        return paths

    @staticmethod
    def export_sql(
        result: GenerationResult,
        output_dir: str,
        encoding: str = "utf-8",
        schema_name: Optional[str] = None,
        batch_insert_size: int = 100,
    ) -> dict[str, str]:
        """
        Üretilen verileri SQL INSERT ifadelerine dönüştürür.

        Args:
            result: Üretim sonucu
            output_dir: Çıktı klasörü
            encoding: Karakter kodlaması
            schema_name: SQL şema adı (opsiyonel)
            batch_insert_size: Tek INSERT ifadesindeki satır sayısı

        Returns:
            {tablo_adı: dosya_yolu} eşleştirmesi
        """
        os.makedirs(output_dir, exist_ok=True)
        paths: dict[str, str] = {}

        for table_name, df in result.tables.items():
            file_path = os.path.join(output_dir, f"{table_name}.sql")
            full_table = f"{schema_name}.{table_name}" if schema_name else table_name
            columns = list(df.columns)
            col_list = ", ".join(columns)

            with open(file_path, "w", encoding=encoding) as f:
                f.write(f"-- Sentetik veri: {table_name} ({len(df)} satır)\n")
                f.write(f"-- Üretim zamanı: {datetime.utcnow().isoformat()}\n\n")

                # Batch INSERT
                for batch_start in range(0, len(df), batch_insert_size):
                    batch_end = min(batch_start + batch_insert_size, len(df))
                    batch = df.iloc[batch_start:batch_end]

                    f.write(f"INSERT INTO {full_table} ({col_list}) VALUES\n")
                    row_strs: list[str] = []
                    for _, row in batch.iterrows():
                        vals: list[str] = []
                        for col in columns:
                            val = row[col]
                            if pd.isna(val):
                                vals.append("NULL")
                            elif isinstance(val, str):
                                escaped = val.replace("'", "''")
                                vals.append(f"'{escaped}'")
                            elif isinstance(val, bool):
                                vals.append("TRUE" if val else "FALSE")
                            elif isinstance(val, (int, float, np.integer, np.floating)):
                                vals.append(str(val))
                            else:
                                escaped = str(val).replace("'", "''")
                                vals.append(f"'{escaped}'")
                        row_strs.append(f"  ({', '.join(vals)})")

                    f.write(",\n".join(row_strs))
                    f.write(";\n\n")

            paths[table_name] = file_path
            logger.info("SQL yazıldı: %s (%d satır)", file_path, len(df))

        return paths

    def export_dataframes(self, result: GenerationResult) -> dict[str, pd.DataFrame]:
        """DataFrame'leri doğrudan döndürür."""
        return dict(result.tables)

    # ═══════════════════════════════════════════════════════════════════
    # 7. Kalite Kontrolü
    # ═══════════════════════════════════════════════════════════════════

    def validate_quality(
        self,
        result: GenerationResult,
        rules: Optional[dict[str, list[InferredRuleResult]]] = None,
        relationships: Optional[list[RelationshipCandidate]] = None,
        original_stats: Optional[dict[str, dict[str, Any]]] = None,
    ) -> dict[str, QualityReport]:
        """
        Üretilen verilerin kalite kontrolünü yapar.

        Kontrol edilen metrikler:
        1. Kural uygunluk oranı (her kural için)
        2. FK bütünlüğü (referans edilen değerler parent'ta var mı?)
        3. İstatistiksel karşılaştırma (ortalama, std, min, max)

        Args:
            result: Üretim sonucu
            rules: Uygulanan kurallar
            relationships: İlişkiler
            original_stats: Orijinal veri istatistikleri (karşılaştırma için)

        Returns:
            {tablo_adı: QualityReport} eşleştirmesi
        """
        rules = rules or {}
        relationships = relationships or []
        original_stats = original_stats or {}
        reports: dict[str, QualityReport] = {}

        for table_name, df in result.tables.items():
            report = QualityReport(
                table_name=table_name,
                total_rows=len(df),
            )

            # 1. Kural uygunluk kontrolü
            table_rules = rules.get(table_name, [])
            if table_rules:
                report.rule_compliance = self._check_rule_compliance(df, table_rules)

            # 2. FK bütünlük kontrolü
            fk_result = self._check_fk_integrity(
                table_name, df, result.tables, relationships,
            )
            if fk_result:
                report.fk_integrity = fk_result

            # 3. İstatistik karşılaştırma
            table_orig_stats = original_stats.get(table_name, {})
            if table_orig_stats:
                report.statistics_comparison = self._compare_statistics(
                    df, table_orig_stats,
                )

            # Genel skor hesapla
            report.overall_score = self._calculate_quality_score(report)
            reports[table_name] = report

            logger.info(
                "Kalite raporu: %s → skor=%.1f", table_name, report.overall_score,
            )

        result.quality_reports = reports
        return reports

    def _check_rule_compliance(
        self,
        df: pd.DataFrame,
        rules: list[InferredRuleResult],
    ) -> dict[str, Any]:
        """Her kural için uygunluk oranını hesaplar."""
        compliance: dict[str, Any] = {}

        for rule in rules:
            col_name = rule.column_name
            if col_name not in df.columns:
                continue

            rule_key = f"{col_name}_{rule.rule_type}"
            series = df[col_name]
            total = len(series)
            violations = 0

            rule_type = rule.rule_type.upper()
            defn = rule.definition

            if rule_type == "NOT_NULL":
                violations = int(series.isna().sum())

            elif rule_type == "UNIQUE":
                violations = int(total - series.nunique())

            elif rule_type == "RANGE":
                min_val = defn.get("min")
                max_val = defn.get("max")
                numeric = pd.to_numeric(series, errors="coerce")
                if min_val is not None:
                    violations += int((numeric < float(min_val)).sum())
                if max_val is not None:
                    violations += int((numeric > float(max_val)).sum())

            elif rule_type == "ENUM":
                allowed = set(str(v) for v in defn.get("values", []))
                if allowed:
                    str_series = series.dropna().astype(str)
                    violations = int((~str_series.isin(allowed)).sum())

            elif rule_type == "REGEX":
                pattern = defn.get("pattern", "")
                if pattern:
                    try:
                        compiled = re.compile(pattern)
                        str_series = series.dropna().astype(str)
                        violations = int(str_series.apply(
                            lambda x: not bool(compiled.match(x))
                        ).sum())
                    except re.error:
                        pass

            elif rule_type == "LENGTH":
                min_len = defn.get("min_length", 0)
                max_len = defn.get("max_length", float("inf"))
                str_series = series.dropna().astype(str)
                lengths = str_series.str.len()
                violations = int(((lengths < min_len) | (lengths > max_len)).sum())

            compliance_rate = ((total - violations) / total * 100) if total > 0 else 100.0
            compliance[rule_key] = {
                "rule_type": rule.rule_type,
                "column": col_name,
                "total_rows": total,
                "violations": violations,
                "compliance_percent": round(compliance_rate, 2),
            }

        return compliance

    def _check_fk_integrity(
        self,
        table_name: str,
        df: pd.DataFrame,
        all_tables: dict[str, pd.DataFrame],
        relationships: list[RelationshipCandidate],
    ) -> dict[str, Any]:
        """FK bütünlüğünü kontrol eder."""
        fk_results: dict[str, Any] = {}

        for rel in relationships:
            if rel.target_dataset_name != table_name:
                continue

            child_col = rel.target_column
            parent_name = rel.source_dataset_name
            parent_col = rel.source_column

            if child_col not in df.columns:
                continue

            parent_df = all_tables.get(parent_name)
            if parent_df is None or parent_col not in parent_df.columns:
                continue

            # Referans edilen değerlerin parent'ta bulunma oranı
            child_values = set(df[child_col].dropna().unique())
            parent_values = set(parent_df[parent_col].dropna().unique())
            orphans = child_values - parent_values
            integrity_rate = (
                ((len(child_values) - len(orphans)) / len(child_values) * 100)
                if child_values else 100.0
            )

            fk_key = f"{child_col} → {parent_name}.{parent_col}"
            fk_results[fk_key] = {
                "child_column": child_col,
                "parent_table": parent_name,
                "parent_column": parent_col,
                "child_unique_values": len(child_values),
                "orphan_count": len(orphans),
                "integrity_percent": round(integrity_rate, 2),
            }

        return fk_results

    @staticmethod
    def _compare_statistics(
        df: pd.DataFrame,
        original_stats: dict[str, Any],
    ) -> dict[str, Any]:
        """Üretilen ve orijinal verinin istatistiklerini karşılaştırır."""
        comparison: dict[str, Any] = {}

        for col_name, orig in original_stats.items():
            if col_name not in df.columns:
                continue

            series = df[col_name]
            synth: dict[str, Any] = {}

            # Sayısal istatistikler
            numeric = pd.to_numeric(series, errors="coerce")
            if numeric.notna().any():
                synth["mean"] = round(float(numeric.mean()), 2)
                synth["std"] = round(float(numeric.std()), 2)
                synth["min"] = round(float(numeric.min()), 2)
                synth["max"] = round(float(numeric.max()), 2)

            # NULL oranı
            synth["null_ratio"] = round(float(series.isna().mean()), 4)

            # Benzersiz oran
            synth["distinct_ratio"] = round(float(series.nunique() / max(len(series), 1)), 4)

            # Orijinal ile fark
            diffs: dict[str, float] = {}
            for metric in ("mean", "std", "null_ratio", "distinct_ratio"):
                orig_val = orig.get(metric)
                synth_val = synth.get(metric)
                if orig_val is not None and synth_val is not None:
                    try:
                        diff = abs(float(synth_val) - float(orig_val))
                        rel_diff = (diff / abs(float(orig_val))) * 100 if float(orig_val) != 0 else 0
                        diffs[f"{metric}_diff_percent"] = round(rel_diff, 2)
                    except (ValueError, ZeroDivisionError):
                        pass

            comparison[col_name] = {
                "original": orig,
                "synthetic": synth,
                "differences": diffs,
            }

        return comparison

    @staticmethod
    def _calculate_quality_score(report: QualityReport) -> float:
        """
        Genel kalite skorunu hesaplar (0-100).

        Bileşenler:
        - Kural uygunluğu: %50 ağırlık
        - FK bütünlüğü: %30 ağırlık
        - İstatistik benzerliği: %20 ağırlık
        """
        scores: list[float] = []
        weights: list[float] = []

        # Kural uygunluk ortalaması
        if report.rule_compliance:
            compliance_values = [
                v.get("compliance_percent", 100.0)
                for v in report.rule_compliance.values()
            ]
            if compliance_values:
                scores.append(sum(compliance_values) / len(compliance_values))
                weights.append(0.50)

        # FK bütünlük ortalaması
        if report.fk_integrity:
            integrity_values = [
                v.get("integrity_percent", 100.0)
                for v in report.fk_integrity.values()
            ]
            if integrity_values:
                scores.append(sum(integrity_values) / len(integrity_values))
                weights.append(0.30)

        # İstatistik benzerliği (farklar düşükse skor yüksek)
        if report.statistics_comparison:
            stat_scores: list[float] = []
            for col_data in report.statistics_comparison.values():
                diffs = col_data.get("differences", {})
                if diffs:
                    avg_diff = sum(diffs.values()) / len(diffs)
                    # %10'dan az fark → 100 puan, %50'den fazla → 0 puan
                    stat_score = max(0, 100 - (avg_diff * 2))
                    stat_scores.append(stat_score)
            if stat_scores:
                scores.append(sum(stat_scores) / len(stat_scores))
                weights.append(0.20)

        # Ağırlıklı ortalama
        if not scores:
            return 100.0  # Kontrol yapılmadıysa tam puan

        total_weight = sum(weights)
        if total_weight == 0:
            return 100.0

        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        return round(weighted_sum / total_weight, 2)

    # ═══════════════════════════════════════════════════════════════════
    # 8. Batch Üretim — İlişkisel Veri Zinciri
    # ═══════════════════════════════════════════════════════════════════

    def generate_relational_chain(
        self,
        customer_count: int = 1000,
        accounts_per_customer: tuple[int, int] = (1, 5),
        transactions_per_account: tuple[int, int] = (0, 50),
        progress_callback: Optional[Callable[[GenerationProgress], None]] = None,
    ) -> GenerationResult:
        """
        customer → accounts → transactions zincirini üretir.

        Bankacılık domain'ine özel hazır üretim pipeline'ı.
        FK referans bütünlüğü tam garanti edilir.

        Args:
            customer_count: Müşteri sayısı
            accounts_per_customer: Her müşteri için hesap aralığı (min, max)
            transactions_per_account: Her hesap için işlem aralığı (min, max)
            progress_callback: İlerleme callback'i

        Returns:
            GenerationResult — 3 tablo (customers, accounts, transactions)
        """
        import time
        start_time = time.time()
        self._progress_callback = progress_callback
        result = GenerationResult(generation_order=["customers", "accounts", "transactions"])

        # ── 1. Müşteriler ──────────────────────────────────────────────
        logger.info("Müşteri üretimi başlıyor: %d adet", customer_count)
        customers_data: list[dict[str, Any]] = []

        progress = GenerationProgress(
            table_name="customers", total_rows=customer_count,
            total_chunks=1, status="running",
        )

        for i in range(customer_count):
            first_name = self._gen_first_name()
            last_name = self._gen_last_name()
            city_data = self._pick_weighted_city()

            customer = {
                "musteri_no": f"MUS{100000 + i:08d}",
                "tckn": self._gen_tckn(),
                "ad": first_name,
                "soyad": last_name,
                "dogum_tarihi": self._gen_birth_date(),
                "cinsiyet": random.choice(["E", "K"]),
                "telefon": self._gen_phone(),
                "email": self._gen_email(),
                "adres": self._gen_address(),
                "sehir": city_data["name"],
                "ilce": random.choice(city_data["districts"]),
                "segment": self._gen_weighted_choice(_SEGMENTS),
                "musteri_tipi": self._gen_weighted_choice(_CUSTOMER_TYPES),
                "kredi_notu": self._gen_credit_score(),
                "kayit_tarihi": self._gen_transaction_date(),
            }
            customers_data.append(customer)

            if (i + 1) % 1000 == 0:
                progress.generated_rows = i + 1
                if self._progress_callback:
                    self._progress_callback(progress)

        customers_df = pd.DataFrame(customers_data)
        result.tables["customers"] = customers_df
        progress.generated_rows = customer_count
        progress.status = "completed"
        if self._progress_callback:
            self._progress_callback(progress)

        # ── 2. Hesaplar ───────────────────────────────────────────────
        logger.info("Hesap üretimi başlıyor")
        accounts_data: list[dict[str, Any]] = []
        account_idx = 0

        est_accounts = customer_count * (accounts_per_customer[0] + accounts_per_customer[1]) // 2
        acc_progress = GenerationProgress(
            table_name="accounts", total_rows=est_accounts,
            total_chunks=1, status="running",
        )

        for _, customer in customers_df.iterrows():
            num_accounts = random.randint(*accounts_per_customer)
            for _ in range(num_accounts):
                account = {
                    "hesap_no": f"HSP{200000 + account_idx:010d}",
                    "musteri_no": customer["musteri_no"],
                    "iban": self._gen_iban(),
                    "hesap_tipi": self._gen_weighted_choice(_ACCOUNT_TYPES),
                    "hesap_durumu": self._gen_weighted_choice(_ACCOUNT_STATUSES),
                    "bakiye": self._gen_balance(),
                    "para_birimi": self._gen_weighted_choice(_CURRENCIES),
                    "faiz_orani": self._gen_interest_rate(),
                    "sube_kodu": self._gen_branch_code(),
                    "acilis_tarihi": self._gen_transaction_date(),
                }
                accounts_data.append(account)
                account_idx += 1

                if account_idx % 2000 == 0:
                    acc_progress.generated_rows = account_idx
                    if self._progress_callback:
                        self._progress_callback(acc_progress)

        accounts_df = pd.DataFrame(accounts_data)
        result.tables["accounts"] = accounts_df
        acc_progress.generated_rows = len(accounts_df)
        acc_progress.total_rows = len(accounts_df)
        acc_progress.status = "completed"
        if self._progress_callback:
            self._progress_callback(acc_progress)

        # ── 3. İşlemler ──────────────────────────────────────────────
        logger.info("İşlem üretimi başlıyor")
        transactions_data: list[dict[str, Any]] = []
        tx_idx = 0

        est_tx = len(accounts_df) * (transactions_per_account[0] + transactions_per_account[1]) // 2
        tx_progress = GenerationProgress(
            table_name="transactions", total_rows=est_tx,
            total_chunks=1, status="running",
        )

        for _, account in accounts_df.iterrows():
            num_tx = random.randint(*transactions_per_account)
            for _ in range(num_tx):
                transaction = {
                    "islem_no": f"TXN{300000 + tx_idx:012d}",
                    "hesap_no": account["hesap_no"],
                    "islem_tipi": self._gen_weighted_choice(_TRANSACTION_TYPES),
                    "tutar": self._gen_amount(),
                    "para_birimi": account["para_birimi"],
                    "islem_tarihi": self._gen_transaction_date(),
                    "kanal": self._gen_weighted_choice(_CHANNELS),
                    "aciklama": self.fake.sentence(nb_words=4),
                    "referans_no": str(uuid.uuid4())[:12].upper(),
                }
                transactions_data.append(transaction)
                tx_idx += 1

                if tx_idx % 10000 == 0:
                    tx_progress.generated_rows = tx_idx
                    if self._progress_callback:
                        self._progress_callback(tx_progress)

        transactions_df = pd.DataFrame(transactions_data)
        result.tables["transactions"] = transactions_df
        tx_progress.generated_rows = len(transactions_df)
        tx_progress.total_rows = len(transactions_df)
        tx_progress.status = "completed"
        if self._progress_callback:
            self._progress_callback(tx_progress)

        result.total_rows_generated = (
            len(customers_df) + len(accounts_df) + len(transactions_df)
        )
        result.elapsed_seconds = time.time() - start_time

        logger.info(
            "İlişkisel zincir üretimi tamamlandı — "
            "%d müşteri, %d hesap, %d işlem (%.2f saniye)",
            len(customers_df), len(accounts_df), len(transactions_df),
            result.elapsed_seconds,
        )

        return result

    # ═══════════════════════════════════════════════════════════════════
    # 9. Yardımcı — Progress ve State Yönetimi
    # ═══════════════════════════════════════════════════════════════════

    def reset(self) -> None:
        """Üretici durumunu sıfırlar (benzersiz havuzlar ve FK havuzları)."""
        self._unique_pools.clear()
        self._fk_pools.clear()
        logger.info("SyntheticDataGenerator durumu sıfırlandı")

    def set_seed(self, seed: int) -> None:
        """Rastgelelik tohumunu ayarlar (tekrarlanabilirlik)."""
        self.seed = seed
        Faker.seed(seed)
        random.seed(seed)
        np.random.seed(seed)
        logger.info("Seed ayarlandı: %d", seed)
