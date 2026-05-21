"""
PII (Kişisel Veri) Tespit Servisi — PIIDetector Modülü.

Kolon sınıflandırma sonuçlarını, pattern eşleşmelerini ve kolon adı
sezgisel analizini kullanarak kişisel ve hassas verileri tespit eder.
Her kolon için PII seviyesi, tespit yöntemi, güven skoru ve önerilen
aksiyon (SYNTHESIZE, MASK, HASH, KEEP, REDACT) belirler.

KVKK (6698 sayılı Kişisel Verilerin Korunması Kanunu) uyumlu etiketleme
sağlar. Türk bankacılık sektörüne özel veri kategorileri desteklenir.

PII Seviyeleri:
  - CRITICAL: TCKN, kredi kartı, şifre, banka hesap detayları
  - HIGH:     Ad-soyad, telefon, email, adres, IBAN
  - MEDIUM:   Doğum tarihi, yaş, müşteri numarası, şube kodu
  - LOW:      Şehir, segment, hesap tipi
  - NONE:     PII içermeyen veriler
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from app.services.column_classifier import (
    ClassificationResult,
    ColumnClassifier,
    SemanticType,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# PII Kategori ve Aksiyon Tanımları
# ═══════════════════════════════════════════════════════════════════════


class PIICategory(str, Enum):
    """PII hassasiyet kategorileri — KVKK uyumlu."""

    CRITICAL = "critical"   # Kritik — TCKN, kredi kartı, şifre
    HIGH = "high"           # Yüksek — ad-soyad, telefon, email, adres, IBAN
    MEDIUM = "medium"       # Orta — doğum tarihi, yaş, müşteri no
    LOW = "low"             # Düşük — şehir, segment, hesap tipi
    NONE = "none"           # PII yok


class PIIAction(str, Enum):
    """PII tespit edildiğinde önerilen aksiyon."""

    SYNTHESIZE = "synthesize"   # Sentetik veri ile değiştir (gerçekçi sahte veri üret)
    MASK = "mask"               # Maskele (ör. 123***789, a***@email.com)
    HASH = "hash"               # Hash'le (geri dönüşümsüz, ilişki korunur)
    KEEP = "keep"               # Olduğu gibi koru (PII yok veya düşük risk)
    REDACT = "redact"           # Tamamen sil / boşalt


class DetectionMethod(str, Enum):
    """PII tespit yöntemi."""

    SEMANTIC_TYPE = "semantic_type"       # ColumnClassifier sonucu
    PATTERN_MATCH = "pattern_match"       # Regex pattern eşleşmesi
    COLUMN_NAME = "column_name"           # Kolon adı sezgisel eşleştirme
    VALUE_ANALYSIS = "value_analysis"     # Değer bazlı tespit
    COMBINED = "combined"                 # Birden fazla yöntem birleşimi


# ═══════════════════════════════════════════════════════════════════════
# KVKK Veri Kategorileri
# ═══════════════════════════════════════════════════════════════════════


class KVKKCategory(str, Enum):
    """
    KVKK (6698) kapsamında kişisel veri kategorileri.

    Kanunun 6. maddesi özel nitelikli kişisel verileri,
    3. maddesi genel kişisel veri tanımını içerir.
    """

    KIMLIK = "kimlik"                 # Kimlik bilgileri (TCKN, ad, soyad)
    ILETISIM = "iletisim"             # İletişim bilgileri (tel, email, adres)
    FINANSAL = "finansal"             # Finansal bilgiler (bakiye, IBAN, kart)
    LOKASYON = "lokasyon"             # Lokasyon bilgileri (şehir, ilçe, adres)
    OZEL_NITELIKLI = "ozel_nitelikli"  # Özel nitelikli (sağlık, biyometrik vb.)
    MUSTERI_ISLEM = "musteri_islem"   # Müşteri işlem bilgileri
    DIGER = "diger"                   # Diğer kişisel veriler
    YOK = "yok"                       # Kişisel veri değil


# ═══════════════════════════════════════════════════════════════════════
# PII Tespit Sonuç Dataclass'ları
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class PIIResult:
    """
    Tek bir kolon için PII tespit sonucu.

    Semantik sınıflandırma, pattern analizi ve sezgisel eşleştirme
    sonuçlarını birleştirerek nihai PII değerlendirmesini içerir.
    """

    column_name: str                                # Kolon adı
    is_pii: bool                                    # PII içeriyor mu?
    pii_category: PIICategory                       # PII hassasiyet seviyesi
    recommended_action: PIIAction                   # Önerilen aksiyon
    confidence: float                               # Güven skoru (0.0 — 1.0)

    # Tespit detayları
    detection_method: DetectionMethod               # Tespit yöntemi
    semantic_type: Optional[str] = None             # Semantik tip (varsa)

    # KVKK uyumluluk
    kvkk_category: KVKKCategory = KVKKCategory.YOK  # KVKK veri kategorisi
    kvkk_description: str = ""                      # KVKK açıklaması

    # Maskeleme stratejisi
    masking_strategy: str = ""                      # Önerilen maskeleme yöntemi
    masking_example: str = ""                       # Maskeleme örneği

    # Ek bilgiler
    reasoning: str = ""                             # Tespit gerekçesi
    detected_patterns: list[str] = field(default_factory=list)  # Eşleşen pattern'lar

    def to_dict(self) -> dict[str, Any]:
        """JSON serializable dict'e dönüştürür."""
        return {
            "column_name": self.column_name,
            "is_pii": self.is_pii,
            "pii_category": self.pii_category.value,
            "recommended_action": self.recommended_action.value,
            "confidence": round(self.confidence, 3),
            "detection_method": self.detection_method.value,
            "semantic_type": self.semantic_type,
            "kvkk_category": self.kvkk_category.value,
            "kvkk_description": self.kvkk_description,
            "masking_strategy": self.masking_strategy,
            "masking_example": self.masking_example,
            "reasoning": self.reasoning,
            "detected_patterns": self.detected_patterns,
        }


@dataclass
class PIIReport:
    """
    Tüm dataset için PII analiz raporu.

    Toplu analiz sonuçlarını, özet istatistikleri ve KVKK uyumluluk
    durumunu içerir.
    """

    dataset_name: str                               # Veri seti adı
    total_columns: int                              # Toplam kolon sayısı
    pii_columns: int                                # PII içeren kolon sayısı
    results: list[PIIResult]                        # Kolon bazlı sonuçlar

    # Seviye bazlı dağılım
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    # KVKK özeti
    kvkk_summary: dict[str, int] = field(default_factory=dict)

    # Risk skoru (0-100)
    overall_risk_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """JSON serializable dict'e dönüştürür."""
        return {
            "dataset_name": self.dataset_name,
            "total_columns": self.total_columns,
            "pii_columns": self.pii_columns,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "overall_risk_score": round(self.overall_risk_score, 1),
            "kvkk_summary": self.kvkk_summary,
            "results": [r.to_dict() for r in self.results],
        }


# ═══════════════════════════════════════════════════════════════════════
# Semantik Tip → PII Eşleştirme Tabloları
# ═══════════════════════════════════════════════════════════════════════

# Her semantik tip için PII kategorisi, aksiyon ve KVKK bilgisi
_SEMANTIC_PII_MAP: dict[SemanticType, dict[str, Any]] = {
    # ── CRITICAL ──────────────────────────────────────────────────────
    SemanticType.NATIONAL_ID: {
        "category": PIICategory.CRITICAL,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.KIMLIK,
        "kvkk_desc": "TC Kimlik Numarası — KVKK m.3 kapsamında kişisel veri",
        "mask_strategy": "İlk 3 ve son 2 hane göster, ortayı maskele",
        "mask_example": "123****89",
    },
    SemanticType.CREDIT_CARD: {
        "category": PIICategory.CRITICAL,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.FINANSAL,
        "kvkk_desc": "Kredi kartı numarası — KVKK m.3 kapsamında finansal veri",
        "mask_strategy": "Son 4 hane göster, kalanını maskele",
        "mask_example": "****-****-****-1234",
    },

    # ── HIGH ──────────────────────────────────────────────────────────
    SemanticType.PERSON_NAME: {
        "category": PIICategory.HIGH,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.KIMLIK,
        "kvkk_desc": "Ad soyad — KVKK m.3 kapsamında kimlik bilgisi",
        "mask_strategy": "İlk harf göster, kalanını maskele",
        "mask_example": "A***",
    },
    SemanticType.FIRST_NAME: {
        "category": PIICategory.HIGH,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.KIMLIK,
        "kvkk_desc": "Ad — KVKK m.3 kapsamında kimlik bilgisi",
        "mask_strategy": "İlk harf göster, kalanını maskele",
        "mask_example": "A***",
    },
    SemanticType.LAST_NAME: {
        "category": PIICategory.HIGH,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.KIMLIK,
        "kvkk_desc": "Soyad — KVKK m.3 kapsamında kimlik bilgisi",
        "mask_strategy": "İlk harf göster, kalanını maskele",
        "mask_example": "Y***",
    },
    SemanticType.FULL_NAME: {
        "category": PIICategory.HIGH,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.KIMLIK,
        "kvkk_desc": "Ad soyad — KVKK m.3 kapsamında kimlik bilgisi",
        "mask_strategy": "İlk harfleri göster, kalanını maskele",
        "mask_example": "A*** Y***",
    },
    SemanticType.PHONE: {
        "category": PIICategory.HIGH,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.ILETISIM,
        "kvkk_desc": "Telefon numarası — KVKK m.3 kapsamında iletişim bilgisi",
        "mask_strategy": "Son 4 hane göster, kalanını maskele",
        "mask_example": "+90*****4567",
    },
    SemanticType.EMAIL: {
        "category": PIICategory.HIGH,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.ILETISIM,
        "kvkk_desc": "E-posta adresi — KVKK m.3 kapsamında iletişim bilgisi",
        "mask_strategy": "İlk 2 karakter ve domain göster",
        "mask_example": "ah***@***.com",
    },
    SemanticType.ADDRESS: {
        "category": PIICategory.HIGH,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.LOKASYON,
        "kvkk_desc": "Adres — KVKK m.3 kapsamında lokasyon bilgisi",
        "mask_strategy": "Şehir bilgisi koru, detayları maskele",
        "mask_example": "*** Mah. *** Sok. İstanbul",
    },
    SemanticType.IBAN: {
        "category": PIICategory.HIGH,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.FINANSAL,
        "kvkk_desc": "IBAN numarası — KVKK m.3 kapsamında finansal veri",
        "mask_strategy": "Ülke kodu ve son 4 hane göster",
        "mask_example": "TR********************1234",
    },

    # ── MEDIUM ────────────────────────────────────────────────────────
    SemanticType.BIRTH_DATE: {
        "category": PIICategory.MEDIUM,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.KIMLIK,
        "kvkk_desc": "Doğum tarihi — KVKK m.3 kapsamında kimlik bilgisi",
        "mask_strategy": "Yılı koru, ay ve günü maskele",
        "mask_example": "**/**/1990",
    },
    SemanticType.AGE: {
        "category": PIICategory.MEDIUM,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.KIMLIK,
        "kvkk_desc": "Yaş — dolaylı kişisel veri (doğum tarihinden türetilebilir)",
        "mask_strategy": "Yaş grubuna dönüştür",
        "mask_example": "30-40",
    },
    SemanticType.CUSTOMER_ID: {
        "category": PIICategory.MEDIUM,
        "action": PIIAction.HASH,
        "kvkk": KVKKCategory.MUSTERI_ISLEM,
        "kvkk_desc": "Müşteri numarası — KVKK m.3 kapsamında müşteri işlem bilgisi",
        "mask_strategy": "Hash'le (ilişki koruma için deterministik)",
        "mask_example": "CUST_a1b2c3d4",
    },
    SemanticType.ACCOUNT_ID: {
        "category": PIICategory.MEDIUM,
        "action": PIIAction.HASH,
        "kvkk": KVKKCategory.FINANSAL,
        "kvkk_desc": "Hesap numarası — KVKK m.3 kapsamında finansal veri",
        "mask_strategy": "Hash'le (ilişki koruma için deterministik)",
        "mask_example": "ACC_e5f6g7h8",
    },
    SemanticType.ACCOUNT_NUMBER: {
        "category": PIICategory.MEDIUM,
        "action": PIIAction.HASH,
        "kvkk": KVKKCategory.FINANSAL,
        "kvkk_desc": "Banka hesap numarası — KVKK m.3 kapsamında finansal veri",
        "mask_strategy": "Hash'le (ilişki koruma için deterministik)",
        "mask_example": "ACC_e5f6g7h8",
    },
    SemanticType.BRANCH_CODE: {
        "category": PIICategory.MEDIUM,
        "action": PIIAction.KEEP,
        "kvkk": KVKKCategory.MUSTERI_ISLEM,
        "kvkk_desc": "Şube kodu — dolaylı lokasyon bilgisi",
        "mask_strategy": "Olduğu gibi koru (doğrudan PII değil)",
        "mask_example": "1234",
    },

    # ── LOW ───────────────────────────────────────────────────────────
    SemanticType.CITY: {
        "category": PIICategory.LOW,
        "action": PIIAction.KEEP,
        "kvkk": KVKKCategory.LOKASYON,
        "kvkk_desc": "Şehir — genel lokasyon bilgisi (tek başına PII değil)",
        "mask_strategy": "Olduğu gibi koru",
        "mask_example": "İstanbul",
    },
    SemanticType.DISTRICT: {
        "category": PIICategory.LOW,
        "action": PIIAction.KEEP,
        "kvkk": KVKKCategory.LOKASYON,
        "kvkk_desc": "İlçe — genel lokasyon bilgisi",
        "mask_strategy": "Olduğu gibi koru",
        "mask_example": "Kadıköy",
    },
    SemanticType.SEGMENT: {
        "category": PIICategory.LOW,
        "action": PIIAction.KEEP,
        "kvkk": KVKKCategory.MUSTERI_ISLEM,
        "kvkk_desc": "Müşteri segmenti — kategorik bilgi, doğrudan PII değil",
        "mask_strategy": "Olduğu gibi koru",
        "mask_example": "Bireysel",
    },
    SemanticType.CUSTOMER_TYPE: {
        "category": PIICategory.LOW,
        "action": PIIAction.KEEP,
        "kvkk": KVKKCategory.MUSTERI_ISLEM,
        "kvkk_desc": "Müşteri tipi — kategorik bilgi",
        "mask_strategy": "Olduğu gibi koru",
        "mask_example": "Kurumsal",
    },
    SemanticType.ACCOUNT_TYPE: {
        "category": PIICategory.LOW,
        "action": PIIAction.KEEP,
        "kvkk": KVKKCategory.MUSTERI_ISLEM,
        "kvkk_desc": "Hesap tipi — kategorik bilgi",
        "mask_strategy": "Olduğu gibi koru",
        "mask_example": "Vadesiz",
    },
    SemanticType.ACCOUNT_STATUS: {
        "category": PIICategory.LOW,
        "action": PIIAction.KEEP,
        "kvkk": KVKKCategory.MUSTERI_ISLEM,
        "kvkk_desc": "Hesap durumu — kategorik bilgi",
        "mask_strategy": "Olduğu gibi koru",
        "mask_example": "Aktif",
    },
    SemanticType.TRANSACTION_TYPE: {
        "category": PIICategory.LOW,
        "action": PIIAction.KEEP,
        "kvkk": KVKKCategory.MUSTERI_ISLEM,
        "kvkk_desc": "İşlem tipi — kategorik bilgi",
        "mask_strategy": "Olduğu gibi koru",
        "mask_example": "Havale",
    },
    SemanticType.CHANNEL: {
        "category": PIICategory.LOW,
        "action": PIIAction.KEEP,
        "kvkk": KVKKCategory.MUSTERI_ISLEM,
        "kvkk_desc": "İşlem kanalı — kategorik bilgi",
        "mask_strategy": "Olduğu gibi koru",
        "mask_example": "Mobil",
    },
    SemanticType.CURRENCY: {
        "category": PIICategory.NONE,
        "action": PIIAction.KEEP,
        "kvkk": KVKKCategory.YOK,
        "kvkk_desc": "Para birimi — kişisel veri değil",
        "mask_strategy": "Olduğu gibi koru",
        "mask_example": "TRY",
    },

    # ── PII Değil ────────────────────────────────────────────────────
    SemanticType.BALANCE: {
        "category": PIICategory.NONE,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.FINANSAL,
        "kvkk_desc": "Bakiye — tek başına PII değil ama finansal veri",
        "mask_strategy": "Sentetik değer üret (dağılımı koru)",
        "mask_example": "12345.67",
    },
    SemanticType.AMOUNT: {
        "category": PIICategory.NONE,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.FINANSAL,
        "kvkk_desc": "Tutar — tek başına PII değil ama finansal veri",
        "mask_strategy": "Sentetik değer üret (dağılımı koru)",
        "mask_example": "1500.00",
    },
    SemanticType.CREDIT_SCORE: {
        "category": PIICategory.NONE,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.FINANSAL,
        "kvkk_desc": "Kredi skoru — dolaylı finansal bilgi",
        "mask_strategy": "Sentetik değer üret (dağılımı koru)",
        "mask_example": "680",
    },
    SemanticType.CARD_LIMIT: {
        "category": PIICategory.NONE,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.FINANSAL,
        "kvkk_desc": "Kart limiti — dolaylı finansal bilgi",
        "mask_strategy": "Sentetik değer üret (dağılımı koru)",
        "mask_example": "25000.00",
    },
    SemanticType.INTEREST_RATE: {
        "category": PIICategory.NONE,
        "action": PIIAction.KEEP,
        "kvkk": KVKKCategory.YOK,
        "kvkk_desc": "Faiz oranı — kişisel veri değil",
        "mask_strategy": "Olduğu gibi koru",
        "mask_example": "0.18",
    },
    SemanticType.TRANSACTION_DATE: {
        "category": PIICategory.NONE,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.MUSTERI_ISLEM,
        "kvkk_desc": "İşlem tarihi — tek başına PII değil",
        "mask_strategy": "Sentetik tarih üret (zaman aralığını koru)",
        "mask_example": "2024-06-15",
    },
    SemanticType.MATURITY_DATE: {
        "category": PIICategory.NONE,
        "action": PIIAction.SYNTHESIZE,
        "kvkk": KVKKCategory.MUSTERI_ISLEM,
        "kvkk_desc": "Vade tarihi — tek başına PII değil",
        "mask_strategy": "Sentetik tarih üret",
        "mask_example": "2025-12-31",
    },
    SemanticType.UNKNOWN: {
        "category": PIICategory.NONE,
        "action": PIIAction.KEEP,
        "kvkk": KVKKCategory.YOK,
        "kvkk_desc": "Bilinmeyen tip — manuel inceleme önerilir",
        "mask_strategy": "Olduğu gibi koru (manuel inceleme gerekebilir)",
        "mask_example": "",
    },
}

# ═══════════════════════════════════════════════════════════════════════
# Kolon Adı Bazlı Sezgisel PII Tespiti
# ═══════════════════════════════════════════════════════════════════════

# Kolon adında geçmesi durumunda PII seviyesini yükselten anahtar kelimeler
_PII_NAME_KEYWORDS: dict[PIICategory, list[str]] = {
    PIICategory.CRITICAL: [
        "tckn", "tc_kimlik", "kimlik_no", "national_id", "ssn",
        "kredi_karti", "credit_card", "card_number", "kart_no",
        "sifre", "password", "passwd", "pin", "pin_code",
        "cvv", "cvc", "security_code",
    ],
    PIICategory.HIGH: [
        "ad_soyad", "adsoyad", "name", "isim", "first_name", "last_name",
        "soyad", "surname", "full_name",
        "telefon", "phone", "tel", "gsm", "mobile", "cep",
        "email", "e_mail", "eposta", "mail",
        "adres", "address",
        "iban",
    ],
    PIICategory.MEDIUM: [
        "dogum_tarihi", "birth_date", "dob",
        "yas", "age",
        "musteri_no", "customer_id", "musteri_id",
        "hesap_no", "account_no", "account_id",
        "sube_kodu", "branch_code",
    ],
    PIICategory.LOW: [
        "sehir", "city", "il",
        "ilce", "district",
        "segment",
        "hesap_tipi", "account_type",
        "durum", "status",
    ],
}

# ═══════════════════════════════════════════════════════════════════════
# Değer Bazlı PII Pattern'ları
# ═══════════════════════════════════════════════════════════════════════

# Değerlerde PII tespit eden regex pattern'lar
_PII_VALUE_PATTERNS: dict[str, dict[str, Any]] = {
    "tckn": {
        "pattern": re.compile(r"^[1-9]\d{10}$"),
        "category": PIICategory.CRITICAL,
        "description": "TCKN formatı (11 haneli, 0 ile başlamaz)",
    },
    "credit_card": {
        "pattern": re.compile(r"^\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}$"),
        "category": PIICategory.CRITICAL,
        "description": "Kredi kartı numarası formatı (16 hane)",
    },
    "iban_tr": {
        "pattern": re.compile(r"^TR\d{24}$", re.IGNORECASE),
        "category": PIICategory.HIGH,
        "description": "Türk IBAN formatı (TR + 24 hane)",
    },
    "email": {
        "pattern": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
        "category": PIICategory.HIGH,
        "description": "Email adresi formatı",
    },
    "phone_tr": {
        "pattern": re.compile(r"^(\+90|0)?5\d{9}$"),
        "category": PIICategory.HIGH,
        "description": "Türk cep telefonu formatı",
    },
}


# ═══════════════════════════════════════════════════════════════════════
# Ana Tespit Sınıfı — PIIDetector
# ═══════════════════════════════════════════════════════════════════════


class PIIDetector:
    """
    PII (Kişisel Veri) Tespit Servisi.

    Dört katmanlı tespit yaklaşımı:
      1. Semantik tip bazlı — ColumnClassifier sonuçlarını kullan
      2. Pattern bazlı — Regex ile değer eşleştirmesi
      3. Kolon adı bazlı — Sezgisel anahtar kelime eşleştirmesi
      4. Değer bazlı — Örnek değerlerden tespit

    Her kolon için PII seviyesi, güven skoru, önerilen aksiyon ve
    KVKK uyumluluk bilgisi üretilir.

    Kullanım:
        classifier = ColumnClassifier()
        detector = PIIDetector(classifier)

        # Tek kolon
        result = detector.detect(column_analysis)

        # Toplu analiz
        report = detector.analyze_dataset("dataset_1", column_analyses)
    """

    def __init__(self, classifier: Optional[ColumnClassifier] = None) -> None:
        """
        PIIDetector yapıcısı.

        Args:
            classifier: Kolon sınıflandırıcı nesnesi.
                None ise otomatik oluşturulur.
        """
        self._classifier = classifier or ColumnClassifier()
        logger.info("PIIDetector başlatıldı.")

    # ── Semantik Tip Bazlı Tespit ─────────────────────────────────────

    def _detect_by_semantic_type(
        self, classification: ClassificationResult
    ) -> Optional[PIIResult]:
        """
        ColumnClassifier sonucundan PII tespiti yapar.

        Args:
            classification: Semantik sınıflandırma sonucu

        Returns:
            PIIResult veya None (eşleşme yoksa)
        """
        stype = classification.semantic_type
        pii_info = _SEMANTIC_PII_MAP.get(stype)

        if pii_info is None:
            return None

        category: PIICategory = pii_info["category"]
        is_pii = category != PIICategory.NONE

        return PIIResult(
            column_name=classification.column_name,
            is_pii=is_pii,
            pii_category=category,
            recommended_action=pii_info["action"],
            confidence=classification.confidence,
            detection_method=DetectionMethod.SEMANTIC_TYPE,
            semantic_type=stype.value,
            kvkk_category=pii_info["kvkk"],
            kvkk_description=pii_info["kvkk_desc"],
            masking_strategy=pii_info["mask_strategy"],
            masking_example=pii_info["mask_example"],
            reasoning=(
                f"Semantik tip '{stype.value}' → PII kategorisi: {category.value}"
            ),
        )

    # ── Pattern Bazlı Tespit ─────────────────────────────────────────

    def _detect_by_patterns(
        self, column_name: str, sample_values: list[Any]
    ) -> Optional[PIIResult]:
        """
        Örnek değerlerdeki pattern'lara bakarak PII tespiti yapar.

        Args:
            column_name: Kolon adı
            sample_values: Örnek değerler listesi

        Returns:
            PIIResult veya None
        """
        if not sample_values:
            return None

        # Her pattern'ı kontrol et
        detected: list[tuple[str, PIICategory, float]] = []

        for value in sample_values:
            if value is None:
                continue
            str_val = str(value).strip().replace(" ", "").replace("-", "")

            for pattern_name, info in _PII_VALUE_PATTERNS.items():
                if info["pattern"].match(str_val):
                    detected.append((pattern_name, info["category"], 1.0))

        if not detected:
            return None

        # En yüksek seviyeli tespiti seç
        category_order = {
            PIICategory.CRITICAL: 4,
            PIICategory.HIGH: 3,
            PIICategory.MEDIUM: 2,
            PIICategory.LOW: 1,
        }
        detected.sort(key=lambda x: category_order.get(x[1], 0), reverse=True)
        best_name, best_category, _ = detected[0]

        # Eşleşme oranını hesapla
        non_null_count = sum(1 for v in sample_values if v is not None)
        match_count = len(detected)
        match_ratio = match_count / max(non_null_count, 1)
        confidence = min(match_ratio * 0.9, 0.95)

        # PII bilgilerini al
        pii_info = _PII_VALUE_PATTERNS[best_name]

        # Semantik tip → aksiyon eşleştirmesi
        action_map: dict[PIICategory, PIIAction] = {
            PIICategory.CRITICAL: PIIAction.SYNTHESIZE,
            PIICategory.HIGH: PIIAction.SYNTHESIZE,
            PIICategory.MEDIUM: PIIAction.HASH,
            PIICategory.LOW: PIIAction.KEEP,
        }

        return PIIResult(
            column_name=column_name,
            is_pii=True,
            pii_category=best_category,
            recommended_action=action_map.get(best_category, PIIAction.KEEP),
            confidence=confidence,
            detection_method=DetectionMethod.PATTERN_MATCH,
            reasoning=f"Pattern eşleşmesi: {pii_info['description']}",
            detected_patterns=[d[0] for d in detected],
        )

    # ── Kolon Adı Bazlı Tespit ───────────────────────────────────────

    def _detect_by_column_name(self, column_name: str) -> Optional[PIIResult]:
        """
        Kolon adındaki anahtar kelimelere bakarak PII tespiti yapar.

        Args:
            column_name: Kolon adı

        Returns:
            PIIResult veya None
        """
        from app.utils.helpers import normalize_column_name
        normalized = normalize_column_name(column_name)

        for category, keywords in _PII_NAME_KEYWORDS.items():
            for keyword in keywords:
                if keyword in normalized or normalized in keyword:
                    # Eşleşme güveni — tam eşleşme vs. kısmi eşleşme
                    if normalized == keyword:
                        confidence = 0.85
                    elif keyword in normalized:
                        confidence = 0.70
                    else:
                        confidence = 0.60

                    # Varsayılan aksiyon
                    action_map: dict[PIICategory, PIIAction] = {
                        PIICategory.CRITICAL: PIIAction.SYNTHESIZE,
                        PIICategory.HIGH: PIIAction.SYNTHESIZE,
                        PIICategory.MEDIUM: PIIAction.HASH,
                        PIICategory.LOW: PIIAction.KEEP,
                    }

                    return PIIResult(
                        column_name=column_name,
                        is_pii=category != PIICategory.NONE,
                        pii_category=category,
                        recommended_action=action_map.get(category, PIIAction.KEEP),
                        confidence=confidence,
                        detection_method=DetectionMethod.COLUMN_NAME,
                        reasoning=(
                            f"Kolon adı eşleşmesi: '{normalized}' ≈ '{keyword}' "
                            f"→ {category.value}"
                        ),
                    )

        return None

    # ── Sonuç Birleştirme ─────────────────────────────────────────────

    def _combine_results(
        self,
        column_name: str,
        semantic_result: Optional[PIIResult],
        pattern_result: Optional[PIIResult],
        name_result: Optional[PIIResult],
    ) -> PIIResult:
        """
        Farklı tespit yöntemlerinden gelen sonuçları birleştirir.

        Öncelik sırası:
          1. Semantik tip (en güvenilir, ColumnClassifier sonucu)
          2. Pattern eşleşmesi (regex doğrudan)
          3. Kolon adı sezgisel

        Birden fazla yöntem eşleşirse güven artar.

        Args:
            column_name: Kolon adı
            semantic_result: Semantik tip bazlı sonuç
            pattern_result: Pattern bazlı sonuç
            name_result: Kolon adı bazlı sonuç

        Returns:
            Birleştirilmiş nihai PIIResult
        """
        results = [r for r in [semantic_result, pattern_result, name_result] if r is not None]

        if not results:
            # Hiçbir yöntem PII tespit edemedi
            return PIIResult(
                column_name=column_name,
                is_pii=False,
                pii_category=PIICategory.NONE,
                recommended_action=PIIAction.KEEP,
                confidence=0.0,
                detection_method=DetectionMethod.COMBINED,
                kvkk_category=KVKKCategory.YOK,
                kvkk_description="PII tespit edilmedi — kişisel veri değil",
                masking_strategy="Olduğu gibi koru",
                reasoning="Hiçbir tespit yöntemiyle PII bulunamadı.",
            )

        # Kategori öncelik sıralaması
        category_priority = {
            PIICategory.CRITICAL: 4,
            PIICategory.HIGH: 3,
            PIICategory.MEDIUM: 2,
            PIICategory.LOW: 1,
            PIICategory.NONE: 0,
        }

        # En yüksek seviyeli sonucu bul
        results.sort(
            key=lambda r: (category_priority.get(r.pii_category, 0), r.confidence),
            reverse=True,
        )
        best = results[0]

        # Birden fazla yöntem PII tespit ettiyse güveni artır
        pii_results = [r for r in results if r.is_pii]
        if len(pii_results) >= 2:
            confidence_boost = min(best.confidence * 1.15, 0.99)
            detection_method = DetectionMethod.COMBINED
            methods = [r.detection_method.value for r in pii_results]
            reasoning = (
                f"Çoklu tespit ({', '.join(methods)}): "
                f"{best.reasoning}"
            )
        else:
            confidence_boost = best.confidence
            detection_method = best.detection_method
            reasoning = best.reasoning

        # KVKK ve maskeleme bilgisi: en zengin kaynaktan al
        # Semantic result KVKK bilgisi taşır, pattern/name result taşımayabilir
        kvkk_cat = best.kvkk_category
        kvkk_desc = best.kvkk_description
        mask_strategy = best.masking_strategy
        mask_example = best.masking_example
        sem_type = best.semantic_type

        # Eğer best sonuçta KVKK bilgisi yoksa diğer kaynaklardan al
        if kvkk_cat == KVKKCategory.YOK or not kvkk_desc:
            for fallback in results:
                if fallback.kvkk_category != KVKKCategory.YOK and fallback.kvkk_description:
                    kvkk_cat = fallback.kvkk_category
                    kvkk_desc = fallback.kvkk_description
                    break

        if not mask_strategy:
            for fallback in results:
                if fallback.masking_strategy:
                    mask_strategy = fallback.masking_strategy
                    mask_example = fallback.masking_example
                    break

        if not sem_type:
            for fallback in results:
                if fallback.semantic_type:
                    sem_type = fallback.semantic_type
                    break

        # Nihai sonuç — en iyi sonucun detaylarını kullan ama güveni güncelle
        return PIIResult(
            column_name=column_name,
            is_pii=best.is_pii,
            pii_category=best.pii_category,
            recommended_action=best.recommended_action,
            confidence=round(confidence_boost, 3),
            detection_method=detection_method,
            semantic_type=sem_type,
            kvkk_category=kvkk_cat,
            kvkk_description=kvkk_desc,
            masking_strategy=mask_strategy,
            masking_example=mask_example,
            reasoning=reasoning,
            detected_patterns=best.detected_patterns,
        )

    # ── Public API ────────────────────────────────────────────────────

    def detect(self, column_analysis: Any) -> PIIResult:
        """
        Tek bir kolon için PII tespiti yapar.

        SchemaAnalyzer'dan gelen ColumnAnalysis nesnesini girdi olarak alır.
        Önce ColumnClassifier ile semantik tip belirler, ardından pattern ve
        kolon adı analizini birleştirerek nihai PII değerlendirmesini üretir.

        Args:
            column_analysis: SchemaAnalyzer'dan gelen ColumnAnalysis nesnesi

        Returns:
            PIIResult nesnesi
        """
        col_name = getattr(column_analysis, "name", "unknown")

        try:
            # 1) ColumnClassifier ile semantik sınıflandırma
            classification = self._classifier.classify(column_analysis)

            # 2) Semantik tip bazlı PII tespiti
            semantic_result = self._detect_by_semantic_type(classification)

            # 3) Pattern bazlı PII tespiti
            sample_values = getattr(column_analysis, "sample_values", [])
            pattern_result = self._detect_by_patterns(col_name, sample_values)

            # 4) Kolon adı bazlı PII tespiti
            original_name = getattr(column_analysis, "original_name", col_name)
            name_result = self._detect_by_column_name(original_name)

            # 5) Sonuçları birleştir
            result = self._combine_results(
                col_name, semantic_result, pattern_result, name_result
            )

            logger.debug(
                "PII tespiti — kolon '%s': is_pii=%s, kategori=%s, güven=%.3f",
                col_name, result.is_pii, result.pii_category.value, result.confidence,
            )
            return result

        except Exception as e:
            logger.error("PII tespiti hatası — kolon '%s': %s", col_name, str(e))
            return PIIResult(
                column_name=col_name,
                is_pii=False,
                pii_category=PIICategory.NONE,
                recommended_action=PIIAction.KEEP,
                confidence=0.0,
                detection_method=DetectionMethod.COMBINED,
                reasoning=f"PII tespiti sırasında hata: {str(e)}",
            )

    def detect_all(self, columns: list[Any]) -> list[PIIResult]:
        """
        Birden fazla kolonu toplu olarak analiz eder.

        Args:
            columns: ColumnAnalysis nesneleri listesi

        Returns:
            PIIResult listesi (giriş sırası korunur)
        """
        results: list[PIIResult] = []
        for col in columns:
            result = self.detect(col)
            results.append(result)

        # Özet logla
        pii_count = sum(1 for r in results if r.is_pii)
        logger.info(
            "Toplu PII tespiti tamamlandı — %d/%d kolon PII içeriyor.",
            pii_count, len(results),
        )
        return results

    def analyze_dataset(
        self,
        dataset_name: str,
        columns: list[Any],
    ) -> PIIReport:
        """
        Tüm dataset için kapsamlı PII analiz raporu üretir.

        Her kolon için PII tespiti yapar, seviye dağılımını hesaplar,
        genel risk skoru belirler ve KVKK özeti oluşturur.

        Args:
            dataset_name: Veri seti adı
            columns: ColumnAnalysis nesneleri listesi

        Returns:
            PIIReport nesnesi
        """
        results = self.detect_all(columns)

        # Seviye sayıları
        critical = sum(1 for r in results if r.pii_category == PIICategory.CRITICAL)
        high = sum(1 for r in results if r.pii_category == PIICategory.HIGH)
        medium = sum(1 for r in results if r.pii_category == PIICategory.MEDIUM)
        low = sum(1 for r in results if r.pii_category == PIICategory.LOW)
        pii_count = sum(1 for r in results if r.is_pii)

        # KVKK özeti
        kvkk_summary: dict[str, int] = {}
        for r in results:
            cat = r.kvkk_category.value
            kvkk_summary[cat] = kvkk_summary.get(cat, 0) + 1

        # Genel risk skoru (0-100)
        # Ağırlıklar: critical=40, high=25, medium=15, low=5
        total_cols = max(len(results), 1)
        risk_score = (
            (critical * 40 + high * 25 + medium * 15 + low * 5) / total_cols
        )
        risk_score = min(risk_score, 100.0)

        report = PIIReport(
            dataset_name=dataset_name,
            total_columns=len(results),
            pii_columns=pii_count,
            results=results,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            kvkk_summary=kvkk_summary,
            overall_risk_score=risk_score,
        )

        logger.info(
            "PII Raporu — '%s': %d kolon, %d PII (%d critical, %d high, "
            "%d medium, %d low), risk skoru: %.1f",
            dataset_name, len(results), pii_count,
            critical, high, medium, low, risk_score,
        )
        return report

    def detect_to_dict(self, column_analysis: Any) -> dict[str, Any]:
        """Tek kolon PII sonucunu dict olarak döndürür."""
        return self.detect(column_analysis).to_dict()

    def analyze_dataset_to_dict(
        self, dataset_name: str, columns: list[Any]
    ) -> dict[str, Any]:
        """Dataset PII raporunu dict olarak döndürür."""
        return self.analyze_dataset(dataset_name, columns).to_dict()
