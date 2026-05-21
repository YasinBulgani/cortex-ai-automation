"""
Semantik Kolon Sınıflandırıcı — ColumnClassifier Modülü.

Kolon adı analizi (fuzzy matching), değer bazlı sınıflandırma ve dağılım
bilgisi kullanarak her kolona semantik bir tip atar. Türkçe ve İngilizce
kolon adlarını destekler. SchemaAnalyzer'dan gelen ColumnAnalysis sonuçlarını
girdi olarak alır.

Desteklenen semantik tipler:
  - Kimlik: PERSON_NAME, FIRST_NAME, LAST_NAME, FULL_NAME, NATIONAL_ID, CUSTOMER_ID, ACCOUNT_ID
  - İletişim: PHONE, EMAIL, ADDRESS, CITY, DISTRICT
  - Finansal: IBAN, ACCOUNT_NUMBER, BALANCE, AMOUNT, CURRENCY, CREDIT_SCORE, CARD_LIMIT
  - Zaman: BIRTH_DATE, TRANSACTION_DATE, MATURITY_DATE, AGE
  - Kategorik: SEGMENT, CUSTOMER_TYPE, ACCOUNT_TYPE, ACCOUNT_STATUS, TRANSACTION_TYPE
  - Operasyonel: BRANCH_CODE, CHANNEL, INTEREST_RATE
  - Diğer: UNKNOWN
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from app.utils.helpers import normalize_column_name

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Semantik Tip Tanımları
# ═══════════════════════════════════════════════════════════════════════


class SemanticType(str, Enum):
    """Desteklenen semantik kolon tipleri."""

    # Kişisel bilgiler
    PERSON_NAME = "person_name"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    FULL_NAME = "full_name"
    BIRTH_DATE = "birth_date"
    AGE = "age"
    NATIONAL_ID = "national_id"       # TCKN

    # Müşteri ve hesap kimlikleri
    CUSTOMER_ID = "customer_id"
    ACCOUNT_ID = "account_id"

    # Finansal araçlar
    IBAN = "iban"
    ACCOUNT_NUMBER = "account_number"
    CREDIT_CARD = "credit_card"

    # İletişim bilgileri
    PHONE = "phone"
    EMAIL = "email"
    ADDRESS = "address"
    CITY = "city"
    DISTRICT = "district"

    # Segment ve tipler
    SEGMENT = "segment"
    CUSTOMER_TYPE = "customer_type"
    ACCOUNT_TYPE = "account_type"
    ACCOUNT_STATUS = "account_status"
    TRANSACTION_TYPE = "transaction_type"

    # Finansal değerler
    BALANCE = "balance"
    AMOUNT = "amount"
    CURRENCY = "currency"
    CREDIT_SCORE = "credit_score"
    CARD_LIMIT = "card_limit"

    # Zaman bilgileri
    TRANSACTION_DATE = "transaction_date"
    MATURITY_DATE = "maturity_date"

    # Operasyonel
    BRANCH_CODE = "branch_code"
    CHANNEL = "channel"
    INTEREST_RATE = "interest_rate"

    # Bilinmeyen
    UNKNOWN = "unknown"


# ═══════════════════════════════════════════════════════════════════════
# Sınıflandırma Sonuç Dataclass'ı
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ClassificationResult:
    """
    Tek bir kolon için semantik sınıflandırma sonucu.

    Birden fazla sinyal kaynağından (kolon adı, değer pattern, dağılım)
    birleştirilmiş nihai sonucu temsil eder.
    """

    column_name: str                               # Kolon adı
    semantic_type: SemanticType                     # Atanan semantik tip
    confidence: float                              # Güven skoru (0.0 — 1.0)

    # Alt sinyal detayları
    name_signal: Optional[str] = None              # Kolon adı eşleşmesi
    name_confidence: float = 0.0                   # Kolon adı güven skoru
    value_signal: Optional[str] = None             # Değer pattern eşleşmesi
    value_confidence: float = 0.0                  # Değer pattern güven skoru
    distribution_signal: Optional[str] = None      # Dağılım bazlı sinyal
    distribution_confidence: float = 0.0           # Dağılım güven skoru

    # Ek bilgiler
    reasoning: str = ""                            # Sınıflandırma gerekçesi
    alternative_types: list[dict[str, Any]] = field(default_factory=list)  # Alternatif tipler

    def to_dict(self) -> dict[str, Any]:
        """JSON serializable dict'e dönüştürür."""
        return {
            "column_name": self.column_name,
            "semantic_type": self.semantic_type.value,
            "confidence": round(self.confidence, 3),
            "name_signal": self.name_signal,
            "name_confidence": round(self.name_confidence, 3),
            "value_signal": self.value_signal,
            "value_confidence": round(self.value_confidence, 3),
            "distribution_signal": self.distribution_signal,
            "distribution_confidence": round(self.distribution_confidence, 3),
            "reasoning": self.reasoning,
            "alternative_types": self.alternative_types,
        }


# ═══════════════════════════════════════════════════════════════════════
# Kolon Adı Eşleştirme Sözlüğü (Türkçe + İngilizce)
# ═══════════════════════════════════════════════════════════════════════

# Her semantik tip için olası kolon adlarını tanımlar.
# Anahtar: SemanticType, Değer: kolon adı varyasyonları listesi
# Not: Tüm değerler normalize edilmiş (küçük harf, ascii) formatta olmalıdır.

NAME_MAPPING: dict[SemanticType, list[str]] = {
    # ── Kişisel Bilgiler ──────────────────────────────────────────────
    SemanticType.PERSON_NAME: [
        "name", "isim", "person_name", "kisi_adi",
        "musteri_adi", "customer_name",
    ],
    SemanticType.FIRST_NAME: [
        "first_name", "firstname", "fname", "ad", "adi",
        "given_name", "givenname",
    ],
    SemanticType.LAST_NAME: [
        "last_name", "lastname", "lname", "soyad", "soyadi",
        "surname", "family_name", "familyname",
    ],
    SemanticType.FULL_NAME: [
        "full_name", "fullname", "ad_soyad", "adsoyad",
        "tam_ad", "tam_isim", "name_surname", "musteri_adi_soyadi",
    ],
    SemanticType.BIRTH_DATE: [
        "birth_date", "birthdate", "dob", "date_of_birth",
        "dogum_tarihi", "dogumtarihi", "dtarihi", "d_tarihi",
    ],
    SemanticType.AGE: [
        "age", "yas", "yasi", "customer_age", "musteri_yasi",
    ],
    SemanticType.NATIONAL_ID: [
        "tckn", "tc_kimlik", "tc_kimlik_no", "tckimlik",
        "national_id", "kimlik_no", "identity_number", "tc_no",
        "tcno", "tc", "kimlik_numarasi", "national_identity",
        "citizen_id", "vatandas_no",
    ],

    # ── Müşteri ve Hesap Kimlikleri ───────────────────────────────────
    SemanticType.CUSTOMER_ID: [
        "customer_id", "customerid", "musteri_no", "musteri_id",
        "musterino", "cust_id", "custid", "client_id", "clientid",
        "musteri_numarasi", "customer_number", "customer_no",
    ],
    SemanticType.ACCOUNT_ID: [
        "account_id", "accountid", "hesap_id", "hesap_no",
        "hesapno", "acc_id", "accid", "hesap_numarasi",
    ],

    # ── Finansal Araçlar ──────────────────────────────────────────────
    SemanticType.IBAN: [
        "iban", "iban_no", "iban_number", "iban_numarasi",
    ],
    SemanticType.ACCOUNT_NUMBER: [
        "account_number", "account_no", "accountno",
        "hesap_numarasi", "hesapno",
    ],
    SemanticType.CREDIT_CARD: [
        "credit_card", "creditcard", "card_number", "cardnumber",
        "kart_no", "kartno", "kart_numarasi", "kredi_karti",
        "kredikarti", "card_no",
    ],

    # ── İletişim Bilgileri ────────────────────────────────────────────
    SemanticType.PHONE: [
        "phone", "telephone", "tel", "telefon", "tel_no",
        "phone_number", "phonenumber", "telefon_no", "telefonno",
        "cep_telefonu", "cep_tel", "mobile", "gsm", "gsm_no",
    ],
    SemanticType.EMAIL: [
        "email", "e_mail", "mail", "eposta", "e_posta",
        "email_address", "mail_address", "mail_adresi",
    ],
    SemanticType.ADDRESS: [
        "address", "adres", "addr", "adres_satiri", "full_address",
        "tam_adres", "ikametgah", "ev_adresi", "is_adresi",
        "home_address", "work_address",
    ],
    SemanticType.CITY: [
        "city", "sehir", "il", "il_adi", "city_name",
        "cityname", "province", "il_kodu",
    ],
    SemanticType.DISTRICT: [
        "district", "ilce", "ilce_adi", "district_name",
        "districtname", "semt", "mahalle", "neighborhood",
    ],

    # ── Segment ve Tipler ─────────────────────────────────────────────
    SemanticType.SEGMENT: [
        "segment", "musteri_segmenti", "customer_segment",
        "seg", "segmenti", "segment_kodu", "segment_code",
    ],
    SemanticType.CUSTOMER_TYPE: [
        "customer_type", "customertype", "musteri_tipi",
        "musteri_turu", "cust_type", "client_type", "tip",
    ],
    SemanticType.ACCOUNT_TYPE: [
        "account_type", "accounttype", "hesap_tipi", "hesap_turu",
        "acc_type", "acctype", "hesap_cinsi",
    ],
    SemanticType.ACCOUNT_STATUS: [
        "account_status", "accountstatus", "hesap_durumu",
        "hesap_durum", "acc_status", "status", "durum",
    ],
    SemanticType.TRANSACTION_TYPE: [
        "transaction_type", "transactiontype", "islem_tipi",
        "islem_turu", "tx_type", "txtype", "islem_kodu",
        "operation_type", "operasyon_tipi",
    ],

    # ── Finansal Değerler ─────────────────────────────────────────────
    SemanticType.BALANCE: [
        "balance", "bakiye", "hesap_bakiyesi", "account_balance",
        "available_balance", "kullanilabilir_bakiye", "guncel_bakiye",
        "current_balance",
    ],
    SemanticType.AMOUNT: [
        "amount", "tutar", "miktar", "islem_tutari", "transaction_amount",
        "tx_amount", "txamount", "odeme_tutari", "payment_amount",
    ],
    SemanticType.CURRENCY: [
        "currency", "para_birimi", "doviz", "doviz_cinsi",
        "currency_code", "ccy", "para_birim",
    ],
    SemanticType.CREDIT_SCORE: [
        "credit_score", "creditscore", "kredi_skoru", "kredi_notu",
        "findeks", "findeks_skoru", "risk_skoru", "risk_score",
    ],
    SemanticType.CARD_LIMIT: [
        "card_limit", "cardlimit", "kart_limiti", "kredi_limiti",
        "credit_limit", "creditlimit", "limit", "toplam_limit",
        "total_limit",
    ],

    # ── Zaman Bilgileri ───────────────────────────────────────────────
    SemanticType.TRANSACTION_DATE: [
        "transaction_date", "transactiondate", "islem_tarihi",
        "tx_date", "txdate", "islem_zamani", "tarih", "date",
        "created_date", "olusturma_tarihi", "kayit_tarihi",
    ],
    SemanticType.MATURITY_DATE: [
        "maturity_date", "maturitydate", "vade_tarihi",
        "vade", "bitis_tarihi", "end_date", "expiry_date",
        "son_odeme_tarihi", "due_date",
    ],

    # ── Operasyonel ───────────────────────────────────────────────────
    SemanticType.BRANCH_CODE: [
        "branch_code", "branchcode", "sube_kodu", "subekodu",
        "branch_id", "branchid", "sube_no", "subeno",
        "branch", "sube", "branch_name", "sube_adi",
    ],
    SemanticType.CHANNEL: [
        "channel", "kanal", "islem_kanali", "transaction_channel",
        "channel_code", "kanal_kodu",
    ],
    SemanticType.INTEREST_RATE: [
        "interest_rate", "interestrate", "faiz_orani", "faiz",
        "rate", "oran", "yillik_faiz", "annual_rate",
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# Levenshtein Mesafe Hesaplama
# ═══════════════════════════════════════════════════════════════════════


def _levenshtein_distance(s1: str, s2: str) -> int:
    """
    İki string arasındaki Levenshtein (edit) mesafesini hesaplar.

    Ekleme, silme ve değiştirme işlemlerinin minimum sayısını bulur.
    Dinamik programlama yaklaşımı ile O(m*n) karmaşıklığında çalışır.

    Args:
        s1: Birinci string
        s2: İkinci string

    Returns:
        İki string arasındaki düzenleme mesafesi
    """
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    # Önceki satır (bellek optimizasyonu — sadece 2 satır tutuyoruz)
    previous_row = range(len(s2) + 1)

    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Ekleme, silme veya değiştirme maliyeti
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def _similarity_ratio(s1: str, s2: str) -> float:
    """
    İki string arasındaki benzerlik oranını hesaplar (0.0 — 1.0).

    Levenshtein mesafesini normalize ederek 0-1 arası benzerlik skoruna çevirir.
    1.0 = tamamen aynı, 0.0 = tamamen farklı.

    Args:
        s1: Birinci string
        s2: İkinci string

    Returns:
        Benzerlik oranı (0.0 — 1.0)
    """
    if not s1 and not s2:
        return 1.0
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    distance = _levenshtein_distance(s1, s2)
    return 1.0 - (distance / max_len)


# ═══════════════════════════════════════════════════════════════════════
# Değer Bazlı Sınıflandırma Yardımcıları
# ═══════════════════════════════════════════════════════════════════════


# Yaygın Türk şehir adları — city tespiti için
_TURKISH_CITIES: set[str] = {
    "istanbul", "ankara", "izmir", "bursa", "antalya", "adana",
    "konya", "gaziantep", "mersin", "diyarbakir", "kayseri",
    "eskisehir", "samsun", "denizli", "sanliurfa", "malatya",
    "trabzon", "erzurum", "van", "batman", "elazig", "manisa",
    "balikesir", "kahramanmaras", "aydin", "mugla", "tekirdag",
    "sakarya", "kocaeli", "hatay", "edirne", "canakkale",
}

# Yaygın segment değerleri
_SEGMENT_VALUES: set[str] = {
    "bireysel", "kurumsal", "ticari", "kobi", "platinum",
    "gold", "silver", "bronze", "vip", "premium", "standart",
    "retail", "corporate", "commercial", "sme", "private",
    "mass", "affluent", "wealth",
}

# Yaygın hesap tipi değerleri
_ACCOUNT_TYPE_VALUES: set[str] = {
    "vadesiz", "vadeli", "mevduat", "cari", "tasarruf",
    "yatirim", "kredi", "checking", "savings", "deposit",
    "current", "investment", "loan", "credit",
}

# Yaygın hesap durumu değerleri
_ACCOUNT_STATUS_VALUES: set[str] = {
    "aktif", "pasif", "kapali", "donmus", "blokeli",
    "active", "inactive", "closed", "frozen", "blocked",
    "suspended", "askiya_alinmis",
}

# Yaygın işlem tipi değerleri
_TRANSACTION_TYPE_VALUES: set[str] = {
    "havale", "eft", "virman", "atm", "pos", "transfer",
    "odeme", "cekme", "yatirma", "withdrawal", "deposit",
    "payment", "wire", "fee", "faiz", "komisyon",
}

# Yaygın kanal değerleri
_CHANNEL_VALUES: set[str] = {
    "internet", "mobil", "sube", "atm", "telefon", "pos",
    "api", "web", "mobile", "branch", "call_center",
    "internet_banking", "mobile_banking", "cagri_merkezi",
}

# Para birimi kodları
_CURRENCY_VALUES: set[str] = {
    "try", "tl", "usd", "eur", "gbp", "jpy", "chf",
    "turk_lirasi", "dolar", "euro", "sterlin",
}


# ═══════════════════════════════════════════════════════════════════════
# Ana Sınıflandırıcı — ColumnClassifier
# ═══════════════════════════════════════════════════════════════════════


class ColumnClassifier:
    """
    Semantik Kolon Sınıflandırıcı.

    Üç katmanlı sinyal birleştirme yaklaşımı:
      1. Kolon adı analizi (fuzzy matching ile Türkçe/İngilizce destek)
      2. Değer bazlı sınıflandırma (pattern ve örnek değer analizi)
      3. Dağılım bazlı çıkarım (istatistiksel profil)

    Her sinyal bağımsız olarak değerlendirilir ve ağırlıklı birleştirme ile
    nihai semantik tip ve güven skoru üretilir.

    Kullanım:
        classifier = ColumnClassifier()
        result = classifier.classify(column_analysis)
        results = classifier.classify_all(analysis_result.columns)
    """

    # Sinyal ağırlıkları — birleştirme sırasında kullanılır
    NAME_WEIGHT: float = 0.50        # Kolon adı sinyali ağırlığı
    VALUE_WEIGHT: float = 0.35       # Değer pattern sinyali ağırlığı
    DISTRIBUTION_WEIGHT: float = 0.15  # Dağılım sinyali ağırlığı

    # Fuzzy matching eşik değeri — bu değerin altındaki eşleşmeler yok sayılır
    FUZZY_THRESHOLD: float = 0.70

    # Minimum güven eşiği — bu değerin altındaki sonuçlar UNKNOWN olarak işaretlenir
    MIN_CONFIDENCE: float = 0.30

    def __init__(
        self,
        name_weight: float = 0.50,
        value_weight: float = 0.35,
        distribution_weight: float = 0.15,
        fuzzy_threshold: float = 0.70,
    ) -> None:
        """
        ColumnClassifier yapıcısı.

        Args:
            name_weight: Kolon adı sinyal ağırlığı (0.0 — 1.0)
            value_weight: Değer pattern sinyal ağırlığı (0.0 — 1.0)
            distribution_weight: Dağılım sinyal ağırlığı (0.0 — 1.0)
            fuzzy_threshold: Fuzzy matching minimum benzerlik eşiği
        """
        self.NAME_WEIGHT = name_weight
        self.VALUE_WEIGHT = value_weight
        self.DISTRIBUTION_WEIGHT = distribution_weight
        self.FUZZY_THRESHOLD = fuzzy_threshold

        # Ters indeks: normalize edilmiş kolon adı → SemanticType (hızlı arama)
        self._name_index: dict[str, SemanticType] = {}
        for stype, names in NAME_MAPPING.items():
            for name in names:
                self._name_index[name] = stype

        logger.info(
            "ColumnClassifier başlatıldı — ağırlıklar: ad=%.2f, değer=%.2f, dağılım=%.2f",
            self.NAME_WEIGHT, self.VALUE_WEIGHT, self.DISTRIBUTION_WEIGHT,
        )

    # ── Kolon Adı Analizi ─────────────────────────────────────────────

    def _classify_by_name(self, column_name: str) -> tuple[Optional[SemanticType], float]:
        """
        Kolon adından semantik tip çıkarır.

        Önce tam eşleşme (exact match), ardından alt-string kontrolü,
        en son fuzzy matching uygular. Türkçe karakter normalleştirmesi yapılır.

        Args:
            column_name: Ham kolon adı

        Returns:
            (semantik_tip, güven_skoru) çifti. Eşleşme yoksa (None, 0.0).
        """
        # Normalleştir — Türkçe karakter, küçük harf, alt çizgi
        normalized = normalize_column_name(column_name)

        # 1) Tam eşleşme kontrolü (en yüksek güven)
        if normalized in self._name_index:
            return self._name_index[normalized], 0.95

        # 2) Alt string kontrolü — kolon adı, bilinen bir ismi içeriyor mu?
        for known_name, stype in self._name_index.items():
            if len(known_name) >= 3 and known_name in normalized:
                return stype, 0.85
            if len(normalized) >= 3 and normalized in known_name:
                return stype, 0.80

        # 3) Fuzzy matching — Levenshtein benzerliği
        best_match: Optional[SemanticType] = None
        best_score: float = 0.0

        for known_name, stype in self._name_index.items():
            # Çok farklı uzunluktaki isimlerde fuzzy matching'i atla
            len_diff = abs(len(normalized) - len(known_name))
            if len_diff > max(len(normalized), len(known_name)) * 0.5:
                continue

            score = _similarity_ratio(normalized, known_name)
            if score > best_score and score >= self.FUZZY_THRESHOLD:
                best_score = score
                best_match = stype

        if best_match is not None:
            # Fuzzy eşleşme güven skoru — benzerlik oranına göre ölçeklenir
            confidence = best_score * 0.85  # Fuzzy → max %85 güven
            return best_match, confidence

        return None, 0.0

    # ── Değer Bazlı Sınıflandırma ────────────────────────────────────

    def _classify_by_values(
        self,
        column_name: str,
        data_type: str,
        semantic_type: Optional[str],
        detected_patterns: dict[str, float],
        sample_values: list[Any],
        most_common_values: list[dict[str, Any]],
    ) -> tuple[Optional[SemanticType], float]:
        """
        Örnek değerler ve pattern bilgisinden semantik tip çıkarır.

        SchemaAnalyzer'dan gelen pattern eşleşmeleri ve örnek değerler
        kullanılarak sınıflandırma yapılır.

        Args:
            column_name: Kolon adı
            data_type: Veri tipi (string, integer, float, date vb.)
            semantic_type: SchemaAnalyzer'ın atadığı semantik tip (varsa)
            detected_patterns: Tespit edilen pattern'lar ve oranları
            sample_values: Örnek değerler listesi
            most_common_values: En yaygın değerler listesi

        Returns:
            (semantik_tip, güven_skoru) çifti
        """
        # SchemaAnalyzer zaten bir semantik tip atamışsa onu kullan
        if semantic_type:
            mapped = self._map_analyzer_semantic_type(semantic_type)
            if mapped is not None:
                return mapped, 0.90

        # Pattern bazlı tespit
        pattern_result = self._classify_from_patterns(detected_patterns)
        if pattern_result[0] is not None:
            return pattern_result

        # Örnek değerlerden tespit — kategorik değerler
        value_result = self._classify_from_sample_values(
            sample_values, most_common_values, data_type
        )
        if value_result[0] is not None:
            return value_result

        return None, 0.0

    def _map_analyzer_semantic_type(self, semantic_type: str) -> Optional[SemanticType]:
        """
        SchemaAnalyzer'ın atadığı semantik tipi SemanticType enum'una çevirir.

        Args:
            semantic_type: SchemaAnalyzer'dan gelen tip string'i

        Returns:
            Eşleşen SemanticType veya None
        """
        mapping: dict[str, SemanticType] = {
            "tckn": SemanticType.NATIONAL_ID,
            "iban": SemanticType.IBAN,
            "credit_card": SemanticType.CREDIT_CARD,
            "email": SemanticType.EMAIL,
            "phone": SemanticType.PHONE,
            "url": SemanticType.UNKNOWN,  # URL kendi başına bir tip değil
            "currency": SemanticType.CURRENCY,
            "account_no": SemanticType.ACCOUNT_NUMBER,
            "customer_no": SemanticType.CUSTOMER_ID,
            "date": SemanticType.TRANSACTION_DATE,
        }
        return mapping.get(semantic_type.lower())

    def _classify_from_patterns(
        self, detected_patterns: dict[str, float]
    ) -> tuple[Optional[SemanticType], float]:
        """
        Tespit edilen pattern'lardan semantik tip çıkarır.

        Args:
            detected_patterns: Pattern adı → eşleşme oranı dict'i

        Returns:
            (semantik_tip, güven_skoru) çifti
        """
        if not detected_patterns:
            return None, 0.0

        # Pattern → SemanticType eşleştirmesi
        pattern_map: dict[str, SemanticType] = {
            "tckn": SemanticType.NATIONAL_ID,
            "iban": SemanticType.IBAN,
            "credit_card": SemanticType.CREDIT_CARD,
            "email": SemanticType.EMAIL,
            "phone": SemanticType.PHONE,
            "account_number": SemanticType.ACCOUNT_NUMBER,
            "customer_number": SemanticType.CUSTOMER_ID,
        }

        # En yüksek eşleşme oranına sahip pattern'ı bul
        best_type: Optional[SemanticType] = None
        best_ratio: float = 0.0

        for pattern_name, match_ratio in detected_patterns.items():
            # Pattern adını normalize et
            normalized_pattern = pattern_name.lower().replace(" ", "_")
            stype = pattern_map.get(normalized_pattern)
            if stype and match_ratio > best_ratio:
                best_ratio = match_ratio
                best_type = stype

        if best_type and best_ratio >= 0.5:
            # Eşleşme oranını güven skoruna çevir
            confidence = min(best_ratio * 0.95, 0.95)
            return best_type, confidence

        return None, 0.0

    def _classify_from_sample_values(
        self,
        sample_values: list[Any],
        most_common_values: list[dict[str, Any]],
        data_type: str,
    ) -> tuple[Optional[SemanticType], float]:
        """
        Örnek değerler ve yaygın değerlerden kategorik tip çıkarır.

        Args:
            sample_values: Örnek değerler
            most_common_values: En yaygın değerler
            data_type: Kolon veri tipi

        Returns:
            (semantik_tip, güven_skoru) çifti
        """
        if not sample_values and not most_common_values:
            return None, 0.0

        # Yaygın değerleri topla
        values_to_check: list[str] = []
        for sv in sample_values:
            if sv is not None:
                values_to_check.append(str(sv).strip().lower())
        for mcv in most_common_values:
            val = mcv.get("value")
            if val is not None:
                values_to_check.append(str(val).strip().lower())

        if not values_to_check:
            return None, 0.0

        # Kategorik değer kümesi kontrolü
        value_set = set(values_to_check)
        checks: list[tuple[set[str], SemanticType]] = [
            (_SEGMENT_VALUES, SemanticType.SEGMENT),
            (_ACCOUNT_TYPE_VALUES, SemanticType.ACCOUNT_TYPE),
            (_ACCOUNT_STATUS_VALUES, SemanticType.ACCOUNT_STATUS),
            (_TRANSACTION_TYPE_VALUES, SemanticType.TRANSACTION_TYPE),
            (_CHANNEL_VALUES, SemanticType.CHANNEL),
            (_CURRENCY_VALUES, SemanticType.CURRENCY),
            (_TURKISH_CITIES, SemanticType.CITY),
        ]

        for known_values, stype in checks:
            overlap = value_set & known_values
            if overlap:
                # Eşleşme oranı — kaç değer tanındı
                match_ratio = len(overlap) / max(len(value_set), 1)
                if match_ratio >= 0.3:
                    confidence = min(match_ratio + 0.3, 0.90)
                    return stype, confidence

        return None, 0.0

    # ── Dağılım Bazlı Sınıflandırma ──────────────────────────────────

    def _classify_by_distribution(
        self,
        data_type: str,
        min_value: Optional[str],
        max_value: Optional[str],
        mean_value: Optional[float],
        distinct_ratio: float,
        distribution: Optional[dict[str, Any]],
    ) -> tuple[Optional[SemanticType], float]:
        """
        İstatistiksel dağılım bilgisinden semantik tip çıkarır.

        Değer aralığı ve dağılım şekline bakarak:
          - 18-100 arası integer → yaş
          - 0-1000 arası integer (300-900 ağırlıklı) → kredi skoru
          - 0.0-1.0 arası float → faiz oranı
          - Geniş aralıklı float → bakiye / tutar
          - 3-5 haneli küçük kümeli integer → şube kodu

        Args:
            data_type: Veri tipi
            min_value: Minimum değer (string)
            max_value: Maksimum değer (string)
            mean_value: Ortalama değer
            distinct_ratio: Benzersiz değer oranı
            distribution: Dağılım bilgisi dict

        Returns:
            (semantik_tip, güven_skoru) çifti
        """
        if data_type not in ("integer", "float", "decimal"):
            return None, 0.0

        # Sayısal sınırları al
        try:
            num_min = float(min_value) if min_value is not None else None
            num_max = float(max_value) if max_value is not None else None
        except (ValueError, TypeError):
            return None, 0.0

        if num_min is None or num_max is None:
            return None, 0.0

        value_range = num_max - num_min

        # ── Yaş tespiti: 0-120 arası integer, düşük benzersizlik
        if data_type == "integer" and 0 <= num_min <= 18 and 50 <= num_max <= 120:
            if mean_value and 25 <= mean_value <= 60:
                return SemanticType.AGE, 0.70
            return SemanticType.AGE, 0.55

        # ── Kredi skoru: 0-1000 arası (genellikle 300-900)
        if data_type == "integer" and 0 <= num_min <= 400 and 700 <= num_max <= 1000:
            if mean_value and 400 <= mean_value <= 700:
                return SemanticType.CREDIT_SCORE, 0.65
            return SemanticType.CREDIT_SCORE, 0.45

        # ── Faiz oranı: 0.0-1.0 veya 0-100 arası küçük float
        if data_type in ("float", "decimal"):
            if 0.0 <= num_min and num_max <= 1.0 and distinct_ratio > 0.1:
                return SemanticType.INTEREST_RATE, 0.50
            if 0.0 <= num_min and num_max <= 100.0 and mean_value and mean_value < 50:
                if distinct_ratio > 0.05:
                    return SemanticType.INTEREST_RATE, 0.40

        # ── Bakiye / tutar: geniş aralıklı float değerler
        if data_type in ("float", "decimal") and value_range > 1000:
            return SemanticType.AMOUNT, 0.35

        # ── Şube kodu: 3-5 haneli integer, düşük benzersizlik
        if data_type == "integer" and 1 <= num_min and num_max <= 99999:
            if distinct_ratio < 0.05 and value_range < 10000:
                return SemanticType.BRANCH_CODE, 0.40

        return None, 0.0

    # ── Sinyal Birleştirme ────────────────────────────────────────────

    def _combine_signals(
        self,
        column_name: str,
        name_result: tuple[Optional[SemanticType], float],
        value_result: tuple[Optional[SemanticType], float],
        dist_result: tuple[Optional[SemanticType], float],
    ) -> ClassificationResult:
        """
        Üç sinyal kaynağını ağırlıklı olarak birleştirir.

        Eğer birden fazla sinyal aynı tipe işaret ediyorsa güven artar.
        Çelişen sinyallerde en yüksek ağırlıklı sinyal tercih edilir.

        Args:
            column_name: Kolon adı
            name_result: Kolon adı sinyali (tip, güven)
            value_result: Değer pattern sinyali (tip, güven)
            dist_result: Dağılım sinyali (tip, güven)

        Returns:
            Nihai ClassificationResult
        """
        name_type, name_conf = name_result
        value_type, value_conf = value_result
        dist_type, dist_conf = dist_result

        # Tüm adayları topla
        candidates: dict[SemanticType, float] = {}

        if name_type is not None:
            weighted = name_conf * self.NAME_WEIGHT
            candidates[name_type] = candidates.get(name_type, 0.0) + weighted

        if value_type is not None:
            weighted = value_conf * self.VALUE_WEIGHT
            candidates[value_type] = candidates.get(value_type, 0.0) + weighted

        if dist_type is not None:
            weighted = dist_conf * self.DISTRIBUTION_WEIGHT
            candidates[dist_type] = candidates.get(dist_type, 0.0) + weighted

        # Uzlaşma bonusu — birden fazla sinyal aynı tipe işaret ediyorsa
        for stype in candidates:
            agreement_count = sum([
                1 for t in [name_type, value_type, dist_type]
                if t == stype
            ])
            if agreement_count >= 2:
                candidates[stype] *= 1.15  # %15 bonus
            if agreement_count >= 3:
                candidates[stype] *= 1.10  # Ek %10 bonus

        # En iyi adayı seç
        if not candidates:
            return ClassificationResult(
                column_name=column_name,
                semantic_type=SemanticType.UNKNOWN,
                confidence=0.0,
                reasoning="Hiçbir sinyal kaynağından eşleşme bulunamadı.",
            )

        # Skorları normalize et (0-1 arası)
        max_possible = self.NAME_WEIGHT + self.VALUE_WEIGHT + self.DISTRIBUTION_WEIGHT
        best_type = max(candidates, key=candidates.get)  # type: ignore[arg-type]
        raw_score = candidates[best_type]
        normalized_confidence = min(raw_score / max_possible, 1.0)

        # Minimum güven kontrolü
        if normalized_confidence < self.MIN_CONFIDENCE:
            return ClassificationResult(
                column_name=column_name,
                semantic_type=SemanticType.UNKNOWN,
                confidence=normalized_confidence,
                reasoning=(
                    f"Güven skoru eşik değerin altında: "
                    f"{normalized_confidence:.3f} < {self.MIN_CONFIDENCE}"
                ),
            )

        # Gerekçe oluştur
        signals: list[str] = []
        if name_type:
            signals.append(f"kolon_adı → {name_type.value} (güven: {name_conf:.2f})")
        if value_type:
            signals.append(f"değer_pattern → {value_type.value} (güven: {value_conf:.2f})")
        if dist_type:
            signals.append(f"dağılım → {dist_type.value} (güven: {dist_conf:.2f})")

        reasoning = "Sinyaller: " + "; ".join(signals)

        # Alternatif tipleri topla (en fazla 3)
        alternatives = [
            {"type": st.value, "score": round(sc / max_possible, 3)}
            for st, sc in sorted(candidates.items(), key=lambda x: x[1], reverse=True)
            if st != best_type
        ][:3]

        return ClassificationResult(
            column_name=column_name,
            semantic_type=best_type,
            confidence=round(normalized_confidence, 3),
            name_signal=name_type.value if name_type else None,
            name_confidence=round(name_conf, 3),
            value_signal=value_type.value if value_type else None,
            value_confidence=round(value_conf, 3),
            distribution_signal=dist_type.value if dist_type else None,
            distribution_confidence=round(dist_conf, 3),
            reasoning=reasoning,
            alternative_types=alternatives,
        )

    # ── Public API ────────────────────────────────────────────────────

    def classify(self, column_analysis: Any) -> ClassificationResult:
        """
        Tek bir kolon için semantik sınıflandırma yapar.

        SchemaAnalyzer'dan gelen ColumnAnalysis nesnesini girdi olarak alır.
        Üç sinyal kaynağını (ad, değer, dağılım) birleştirerek nihai sonucu üretir.

        Args:
            column_analysis: SchemaAnalyzer'dan gelen ColumnAnalysis nesnesi.
                Beklenen alanlar: name, original_name, data_type, semantic_type,
                detected_patterns, sample_values, most_common_values, min_value,
                max_value, mean_value, distinct_ratio, distribution

        Returns:
            ClassificationResult nesnesi
        """
        col_name = getattr(column_analysis, "name", "unknown")

        try:
            # 1) Kolon adı sinyali
            name_result = self._classify_by_name(
                getattr(column_analysis, "original_name", col_name)
            )

            # 2) Değer bazlı sinyal
            value_result = self._classify_by_values(
                column_name=col_name,
                data_type=getattr(column_analysis, "data_type", "string"),
                semantic_type=getattr(column_analysis, "semantic_type", None),
                detected_patterns=getattr(column_analysis, "detected_patterns", {}),
                sample_values=getattr(column_analysis, "sample_values", []),
                most_common_values=getattr(column_analysis, "most_common_values", []),
            )

            # 3) Dağılım bazlı sinyal
            dist_result = self._classify_by_distribution(
                data_type=getattr(column_analysis, "data_type", "string"),
                min_value=getattr(column_analysis, "min_value", None),
                max_value=getattr(column_analysis, "max_value", None),
                mean_value=getattr(column_analysis, "mean_value", None),
                distinct_ratio=getattr(column_analysis, "distinct_ratio", 0.0),
                distribution=getattr(column_analysis, "distribution", None),
            )

            # 4) Sinyalleri birleştir
            result = self._combine_signals(col_name, name_result, value_result, dist_result)

            logger.debug(
                "Kolon '%s' sınıflandırıldı → %s (güven: %.3f)",
                col_name, result.semantic_type.value, result.confidence,
            )
            return result

        except Exception as e:
            logger.error("Kolon '%s' sınıflandırma hatası: %s", col_name, str(e))
            return ClassificationResult(
                column_name=col_name,
                semantic_type=SemanticType.UNKNOWN,
                confidence=0.0,
                reasoning=f"Sınıflandırma sırasında hata: {str(e)}",
            )

    def classify_all(
        self, columns: list[Any]
    ) -> list[ClassificationResult]:
        """
        Birden fazla kolonu toplu olarak sınıflandırır.

        Args:
            columns: ColumnAnalysis nesneleri listesi

        Returns:
            ClassificationResult listesi (giriş sırası korunur)
        """
        results: list[ClassificationResult] = []
        for col in columns:
            result = self.classify(col)
            results.append(result)

        # Özet istatistikleri logla
        classified = [r for r in results if r.semantic_type != SemanticType.UNKNOWN]
        unknown = [r for r in results if r.semantic_type == SemanticType.UNKNOWN]
        avg_conf = (
            sum(r.confidence for r in classified) / len(classified)
            if classified else 0.0
        )

        logger.info(
            "Toplu sınıflandırma tamamlandı — %d/%d kolon sınıflandırıldı "
            "(ortalama güven: %.3f), %d kolon UNKNOWN",
            len(classified), len(results), avg_conf, len(unknown),
        )
        return results

    def classify_to_dict(self, column_analysis: Any) -> dict[str, Any]:
        """
        Tek bir kolonu sınıflandırıp sonucu dict olarak döndürür.

        Args:
            column_analysis: ColumnAnalysis nesnesi

        Returns:
            Sınıflandırma sonucu dict
        """
        return self.classify(column_analysis).to_dict()

    def classify_all_to_dict(self, columns: list[Any]) -> list[dict[str, Any]]:
        """
        Tüm kolonları sınıflandırıp sonuçları dict listesi olarak döndürür.

        Args:
            columns: ColumnAnalysis nesneleri listesi

        Returns:
            Sınıflandırma sonuçları dict listesi
        """
        return [r.to_dict() for r in self.classify_all(columns)]
