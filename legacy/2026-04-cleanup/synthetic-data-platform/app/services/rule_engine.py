"""
Rule Inference Engine — Otomatik Kural Çıkarım Motoru.

SchemaAnalyzer sonuçlarından ve ColumnClassifier semantik tiplerinden
otomatik olarak iş kuralları çıkarır. Bankacılık domainine özel kurallar:
  - RANGE: min/max değer aralıkları (bakiye, yaş, kredi notu)
  - ENUM: sabit değer kümeleri (segment, hesap tipi, para birimi)
  - REGEX: format kuralları (TCKN, IBAN, telefon)
  - DISTRIBUTION: istatistiksel dağılım kuralları (normal, lognormal, uniform)
  - DEPENDENCY: kolonlar arası bağımlılıklar (işlem tarihi > hesap açılış tarihi)
  - NOT_NULL: zorunlu alan kuralları
  - UNIQUE: benzersizlik kuralları
  - LENGTH: string uzunluk kuralları
  - CONDITIONAL: koşullu kurallar (segment=premium ise bakiye > 100000)

Desteklenen işlemler:
  - Otomatik kural çıkarma (infer)
  - Kural doğrulama (validate)
  - JSON/YAML dışa/içe aktarma (export/import)
  - InferredRule ORM modeli ile veritabanı entegrasyonu
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from app.models.dataset import RuleType

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Kural Sonuç Dataclass'ları
# ═══════════════════════════════════════════════════════════════════════


# Genişletilmiş kural tipleri — RuleType enum'unun üst kümesi.
# ORM'deki RuleType sadece 5 değer destekliyor (range, enum, regex, distribution, dependency).
# Ek tipler (not_null, unique, length, conditional) kural tanımı (definition) içinde
# "extended_type" alanı olarak saklanır, DB'ye kaydedilirken en yakın RuleType'a eşlenir.
EXTENDED_RULE_TYPES = {
    "RANGE", "ENUM", "REGEX", "DISTRIBUTION", "DEPENDENCY",
    "NOT_NULL", "UNIQUE", "LENGTH", "CONDITIONAL",
}

# Genişletilmiş tip → ORM RuleType eşleştirmesi
_EXTENDED_TO_ORM: dict[str, RuleType] = {
    "RANGE": RuleType.RANGE,
    "ENUM": RuleType.ENUM,
    "REGEX": RuleType.REGEX,
    "DISTRIBUTION": RuleType.DISTRIBUTION,
    "DEPENDENCY": RuleType.DEPENDENCY,
    # Genişletilmiş tipler en yakın ORM tipine eşlenir
    "NOT_NULL": RuleType.RANGE,          # Zorunlu alan → range (min_count=1)
    "UNIQUE": RuleType.RANGE,            # Benzersizlik → range (distinct_ratio=1.0)
    "LENGTH": RuleType.RANGE,            # String uzunluk → range (min_len, max_len)
    "CONDITIONAL": RuleType.DEPENDENCY,  # Koşullu → dependency
}


@dataclass
class InferredRuleResult:
    """
    Tek bir çıkarılmış kural sonucu.

    Hem in-memory kullanım hem de JSON/YAML export için kullanılır.
    InferredRule ORM modeline dönüştürülebilir yapıdadır.
    """

    rule_id: str                            # UUID formatında benzersiz kimlik
    column_name: str                        # Kuralın uygulandığı kolon
    rule_type: str                          # Kural tipi (EXTENDED_RULE_TYPES'dan biri)
    definition: dict[str, Any]              # Kural tanımı (parametreler, sınırlar vb.)
    confidence: float = 0.0                 # Güven skoru (0.0 — 1.0)
    is_active: bool = True                  # Kural aktif mi?
    description: str = ""                   # İnsan okunabilir açıklama
    source: str = "auto_inferred"           # Kuralın kaynağı (auto_inferred, manual, imported)
    created_at: str = ""                    # Oluşturulma zamanı (ISO 8601)

    def __post_init__(self) -> None:
        if not self.rule_id:
            self.rule_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """JSON serializable dict'e dönüştürür."""
        return asdict(self)

    def to_orm_dict(self) -> dict[str, Any]:
        """
        InferredRule ORM modeline uyumlu dict döndürür.

        Genişletilmiş tipler (NOT_NULL, UNIQUE, LENGTH, CONDITIONAL)
        en yakın RuleType enum değerine eşlenir.
        """
        orm_type = _EXTENDED_TO_ORM.get(self.rule_type, RuleType.RANGE)
        # Genişletilmiş tip bilgisini definition içinde sakla
        definition = dict(self.definition)
        if self.rule_type not in ("RANGE", "ENUM", "REGEX", "DISTRIBUTION", "DEPENDENCY"):
            definition["extended_type"] = self.rule_type
        return {
            "column_name": self.column_name,
            "rule_type": orm_type,
            "rule_definition": definition,
            "confidence_score": self.confidence,
            "is_active": self.is_active,
        }


@dataclass
class ValidationResult:
    """Kural doğrulama sonucu."""

    rule_id: str                            # Doğrulanan kuralın ID'si
    column_name: str                        # Kolon adı
    rule_type: str                          # Kural tipi
    is_valid: bool = True                   # Doğrulama başarılı mı?
    total_rows: int = 0                     # Toplam satır sayısı
    violation_count: int = 0                # İhlal sayısı
    violation_ratio: float = 0.0            # İhlal oranı (0.0 — 1.0)
    sample_violations: list[Any] = field(default_factory=list)  # Örnek ihlaller

    def to_dict(self) -> dict[str, Any]:
        """JSON serializable dict'e dönüştürür."""
        return asdict(self)


@dataclass
class RuleInferenceReport:
    """Tüm kurallar için çıkarım raporu."""

    dataset_name: str
    total_columns: int = 0
    total_rules: int = 0
    rules_by_type: dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    rules: list[InferredRuleResult] = field(default_factory=list)
    inferred_at: str = ""

    def __post_init__(self) -> None:
        if not self.inferred_at:
            self.inferred_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """JSON serializable dict'e dönüştürür."""
        return {
            "dataset_name": self.dataset_name,
            "total_columns": self.total_columns,
            "total_rules": self.total_rules,
            "rules_by_type": self.rules_by_type,
            "avg_confidence": round(self.avg_confidence, 3),
            "inferred_at": self.inferred_at,
            "rules": [r.to_dict() for r in self.rules],
        }


# ═══════════════════════════════════════════════════════════════════════
# Bankacılık Domain Sabitleri
# ═══════════════════════════════════════════════════════════════════════

# Bilinen regex pattern'lar — semantik tipe göre
_KNOWN_PATTERNS: dict[str, str] = {
    "tckn": r"^\d{11}$",
    "national_id": r"^\d{11}$",
    "iban": r"^TR\d{24}$",
    "phone": r"^(\+90|0)?[5][0-9]{9}$",
    "email": r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
    "credit_card": r"^\d{16}$",
    "account_number": r"^\d{10,16}$",
    "customer_id": r"^(MUS|CUS|MTR|BRC)?\d{6,12}$",
}

# Semantik tip → beklenen aralık bilgisi (bankacılık domaini)
_SEMANTIC_RANGES: dict[str, dict[str, Any]] = {
    "age": {"min": 18, "max": 90, "distribution": "normal", "params": {"mean": 38, "std": 12}},
    "credit_score": {"min": 300, "max": 900, "distribution": "normal", "params": {"mean": 620, "std": 100}},
    "balance": {"min": 0, "max": 999_999_999, "distribution": "lognormal", "params": {"mean": 10000, "std": 50000}},
    "amount": {"min": 0.01, "max": 999_999_999, "distribution": "lognormal", "params": {"mean": 1500, "std": 8000}},
    "interest_rate": {"min": 0.0, "max": 1.0, "distribution": "uniform", "params": {"low": 0.05, "high": 0.45}},
    "card_limit": {"min": 1000, "max": 500_000, "distribution": "lognormal", "params": {"mean": 15000, "std": 25000}},
}

# Semantik tip → bilinen enum değerleri
_SEMANTIC_ENUMS: dict[str, list[str]] = {
    "segment": ["bireysel", "ticari", "kurumsal", "kobi", "premium", "vip"],
    "customer_type": ["bireysel", "kurumsal", "ticari"],
    "account_type": ["vadesiz", "vadeli", "mevduat", "cari", "tasarruf", "yatirim", "kredi"],
    "account_status": ["aktif", "pasif", "kapali", "donmus", "blokeli"],
    "transaction_type": ["havale", "eft", "virman", "atm", "pos", "transfer", "odeme"],
    "channel": ["internet", "mobil", "sube", "atm", "telefon", "pos", "api"],
    "currency": ["TRY", "USD", "EUR", "GBP"],
    "city": [],  # Çok sayıda olduğu için veriden çıkarılır
}


# ═══════════════════════════════════════════════════════════════════════
# Ana Sınıf — RuleInferenceEngine
# ═══════════════════════════════════════════════════════════════════════


class RuleInferenceEngine:
    """
    Otomatik Kural Çıkarım Motoru.

    SchemaAnalyzer sonuçlarından ve ColumnClassifier semantik tiplerinden
    otomatik olarak bankacılık iş kuralları çıkarır.

    Kural çıkarma sırası:
      1. NOT_NULL — Zorunlu alan tespiti (null_ratio < eşik)
      2. UNIQUE — Benzersizlik tespiti (distinct_ratio > eşik)
      3. REGEX — Pattern format kuralları (TCKN, IBAN, telefon vb.)
      4. ENUM — Sabit değer kümeleri (az sayıda benzersiz değer)
      5. RANGE — Sayısal aralık kuralları (percentile bazlı)
      6. LENGTH — String uzunluk kuralları
      7. DISTRIBUTION — İstatistiksel dağılım kuralları
      8. DEPENDENCY — Kolonlar arası bağımlılık kuralları
      9. CONDITIONAL — Koşullu kurallar (segment bazlı vb.)

    Kullanım:
        engine = RuleInferenceEngine()
        report = engine.infer_rules(analysis_result, classifications)
        engine.export_rules(report.rules, "rules/output.json")
    """

    # ── Yapılandırma Eşikleri ─────────────────────────────────────────

    # NOT_NULL eşiği — null oranı bunun altındaysa alan zorunlu sayılır
    NOT_NULL_THRESHOLD: float = 0.01

    # UNIQUE eşiği — distinct oranı bunun üstündeyse alan benzersiz sayılır
    UNIQUE_THRESHOLD: float = 0.99

    # ENUM eşiği — benzersiz değer sayısı bunun altındaysa enum kuralı üretilir
    ENUM_MAX_DISTINCT: int = 25

    # ENUM minimum frekans — en az bu kadar görülmüş değerler enum'a dahil edilir
    ENUM_MIN_FREQUENCY: float = 0.005  # %0.5

    # Percentile aralığı — RANGE kuralları için kullanılır
    RANGE_PERCENTILE_LOW: float = 1.0    # P1
    RANGE_PERCENTILE_HIGH: float = 99.0  # P99

    # Minimum güven eşiği — bunun altındaki kurallar üretilmez
    MIN_CONFIDENCE: float = 0.3

    def __init__(
        self,
        not_null_threshold: float = 0.01,
        unique_threshold: float = 0.99,
        enum_max_distinct: int = 25,
        range_percentile_low: float = 1.0,
        range_percentile_high: float = 99.0,
        min_confidence: float = 0.3,
        rules_dir: str = "rules",
    ) -> None:
        """
        RuleInferenceEngine yapıcısı.

        Args:
            not_null_threshold: NOT_NULL kuralı için null oranı eşiği
            unique_threshold: UNIQUE kuralı için distinct oranı eşiği
            enum_max_distinct: ENUM kuralı için maksimum benzersiz değer sayısı
            range_percentile_low: RANGE kuralı alt percentile (ör. P1)
            range_percentile_high: RANGE kuralı üst percentile (ör. P99)
            min_confidence: Minimum güven skoru eşiği
            rules_dir: Kural dosyaları klasörü
        """
        self.NOT_NULL_THRESHOLD = not_null_threshold
        self.UNIQUE_THRESHOLD = unique_threshold
        self.ENUM_MAX_DISTINCT = enum_max_distinct
        self.RANGE_PERCENTILE_LOW = range_percentile_low
        self.RANGE_PERCENTILE_HIGH = range_percentile_high
        self.MIN_CONFIDENCE = min_confidence
        self.rules_dir = Path(rules_dir)

        logger.info(
            "RuleInferenceEngine başlatıldı — NOT_NULL=%.3f, UNIQUE=%.3f, "
            "ENUM_MAX=%d, RANGE=[P%.0f-P%.0f]",
            self.NOT_NULL_THRESHOLD, self.UNIQUE_THRESHOLD,
            self.ENUM_MAX_DISTINCT,
            self.RANGE_PERCENTILE_LOW, self.RANGE_PERCENTILE_HIGH,
        )

    # ═════════════════════════════════════════════════════════════════
    # Güven Skoru Hesaplama
    # ═════════════════════════════════════════════════════════════════

    def _compute_confidence(
        self,
        base_confidence: float,
        null_ratio: float = 0.0,
        sample_size: int = 0,
        match_ratio: float = 1.0,
    ) -> float:
        """
        Veri kalitesine dayalı güven skoru hesaplar.

        Faktörler:
          - Temel güven skoru (kural tipine göre)
          - Null oranı cezası (çok null varsa güven düşer)
          - Örnek büyüklüğü bonusu (büyük veri seti → yüksek güven)
          - Pattern eşleşme oranı çarpanı

        Args:
            base_confidence: Temel güven skoru (0.0 — 1.0)
            null_ratio: Kolondaki null oranı
            sample_size: Örnek (veya toplam) satır sayısı
            match_ratio: Pattern eşleşme oranı (0.0 — 1.0)

        Returns:
            Hesaplanan güven skoru (0.0 — 1.0 arasında clamp edilmiş)
        """
        score = base_confidence

        # Null oranı cezası — yüksek null oranı güveni düşürür
        if null_ratio > 0.5:
            score *= 0.6
        elif null_ratio > 0.2:
            score *= 0.8
        elif null_ratio > 0.05:
            score *= 0.9

        # Örnek büyüklüğü bonusu
        if sample_size >= 10_000:
            score *= 1.05
        elif sample_size >= 1_000:
            score *= 1.02
        elif sample_size < 100:
            score *= 0.85

        # Pattern eşleşme oranı çarpanı
        score *= max(match_ratio, 0.1)

        # 0.0 — 1.0 arasında sınırla
        return max(0.0, min(1.0, score))

    # ═════════════════════════════════════════════════════════════════
    # Kural Çıkarma Mekanizmaları
    # ═════════════════════════════════════════════════════════════════

    def _infer_not_null(self, col: Any) -> Optional[InferredRuleResult]:
        """
        NOT_NULL kuralı çıkarır.

        Null oranı eşik değerin altındaysa kolon zorunlu kabul edilir.

        Args:
            col: ColumnAnalysis nesnesi

        Returns:
            InferredRuleResult veya None
        """
        null_ratio = getattr(col, "null_ratio", 0.0) or 0.0
        total_count = getattr(col, "total_count", 0) or 0

        if null_ratio < self.NOT_NULL_THRESHOLD:
            confidence = self._compute_confidence(
                base_confidence=0.90,
                null_ratio=null_ratio,
                sample_size=total_count,
            )
            return InferredRuleResult(
                rule_id=str(uuid.uuid4()),
                column_name=getattr(col, "name", ""),
                rule_type="NOT_NULL",
                definition={
                    "nullable": False,
                    "observed_null_ratio": round(null_ratio, 6),
                },
                confidence=round(confidence, 3),
                description=f"Zorunlu alan — null oranı: {null_ratio:.4%}",
            )
        return None

    def _infer_unique(self, col: Any) -> Optional[InferredRuleResult]:
        """
        UNIQUE kuralı çıkarır.

        Benzersiz değer oranı eşik değerin üstündeyse kolon unique kabul edilir.

        Args:
            col: ColumnAnalysis nesnesi

        Returns:
            InferredRuleResult veya None
        """
        distinct_ratio = getattr(col, "distinct_ratio", 0.0) or 0.0
        total_count = getattr(col, "total_count", 0) or 0

        if distinct_ratio > self.UNIQUE_THRESHOLD and total_count > 10:
            confidence = self._compute_confidence(
                base_confidence=0.88,
                sample_size=total_count,
                match_ratio=distinct_ratio,
            )
            return InferredRuleResult(
                rule_id=str(uuid.uuid4()),
                column_name=getattr(col, "name", ""),
                rule_type="UNIQUE",
                definition={
                    "unique": True,
                    "observed_distinct_ratio": round(distinct_ratio, 6),
                },
                confidence=round(confidence, 3),
                description=f"Benzersiz alan — distinct oranı: {distinct_ratio:.4%}",
            )
        return None

    def _infer_regex(
        self, col: Any, semantic_type: Optional[str] = None
    ) -> Optional[InferredRuleResult]:
        """
        REGEX kuralı çıkarır.

        Tespit edilen pattern veya semantik tipe göre regex kuralı üretir.
        Bankacılık formatları: TCKN, IBAN, telefon, email, kredi kartı.

        Args:
            col: ColumnAnalysis nesnesi
            semantic_type: Semantik tip (varsa)

        Returns:
            InferredRuleResult veya None
        """
        col_name = getattr(col, "name", "")
        pattern = getattr(col, "pattern", None)
        detected_patterns = getattr(col, "detected_patterns", {}) or {}
        total_count = getattr(col, "total_count", 0) or 0
        null_ratio = getattr(col, "null_ratio", 0.0) or 0.0

        # Öncelik 1: Semantik tipe göre bilinen pattern
        if semantic_type and semantic_type in _KNOWN_PATTERNS:
            known_pattern = _KNOWN_PATTERNS[semantic_type]
            # Detected pattern'lardan eşleşme oranını al
            match_ratio = 1.0
            for pname, pratio in detected_patterns.items():
                if semantic_type in pname.lower():
                    match_ratio = pratio
                    break

            confidence = self._compute_confidence(
                base_confidence=0.92,
                null_ratio=null_ratio,
                sample_size=total_count,
                match_ratio=match_ratio,
            )
            return InferredRuleResult(
                rule_id=str(uuid.uuid4()),
                column_name=col_name,
                rule_type="REGEX",
                definition={
                    "pattern": known_pattern,
                    "semantic_type": semantic_type,
                    "match_ratio": round(match_ratio, 4),
                },
                confidence=round(confidence, 3),
                description=f"Format kuralı ({semantic_type}) — pattern: {known_pattern}",
            )

        # Öncelik 2: Tespit edilen pattern'lardan en güçlüsü
        if detected_patterns:
            best_pattern_name = max(detected_patterns, key=detected_patterns.get)
            best_ratio = detected_patterns[best_pattern_name]

            if best_ratio >= 0.5 and best_pattern_name in _KNOWN_PATTERNS:
                confidence = self._compute_confidence(
                    base_confidence=0.85,
                    null_ratio=null_ratio,
                    sample_size=total_count,
                    match_ratio=best_ratio,
                )
                return InferredRuleResult(
                    rule_id=str(uuid.uuid4()),
                    column_name=col_name,
                    rule_type="REGEX",
                    definition={
                        "pattern": _KNOWN_PATTERNS[best_pattern_name],
                        "detected_pattern": best_pattern_name,
                        "match_ratio": round(best_ratio, 4),
                    },
                    confidence=round(confidence, 3),
                    description=f"Format kuralı — {best_pattern_name} ({best_ratio:.0%} eşleşme)",
                )

        # Öncelik 3: SchemaAnalyzer'dan gelen pattern
        if pattern:
            confidence = self._compute_confidence(
                base_confidence=0.70,
                null_ratio=null_ratio,
                sample_size=total_count,
            )
            return InferredRuleResult(
                rule_id=str(uuid.uuid4()),
                column_name=col_name,
                rule_type="REGEX",
                definition={
                    "pattern": pattern,
                    "source": "schema_analyzer",
                },
                confidence=round(confidence, 3),
                description=f"Tespit edilen pattern: {pattern}",
            )

        return None

    def _infer_enum(
        self, col: Any, semantic_type: Optional[str] = None
    ) -> Optional[InferredRuleResult]:
        """
        ENUM kuralı çıkarır.

        Az sayıda benzersiz değere sahip kolonlar için sabit değer listesi üretir.
        Frekans analizi ile düşük frekanslı değerler filtrelenir.

        Args:
            col: ColumnAnalysis nesnesi
            semantic_type: Semantik tip (varsa)

        Returns:
            InferredRuleResult veya None
        """
        col_name = getattr(col, "name", "")
        data_type = getattr(col, "data_type", "string")
        distinct_count = getattr(col, "distinct_count", 0) or 0
        total_count = getattr(col, "total_count", 0) or 0
        null_ratio = getattr(col, "null_ratio", 0.0) or 0.0
        most_common = getattr(col, "most_common_values", []) or []

        # Sayısal ve tarih kolonlarda enum çıkarma (genellikle anlamlı değil)
        if data_type in ("integer", "float", "decimal", "date", "datetime"):
            # Sadece çok az sayıda benzersiz değer varsa (ör. 2-5)
            if distinct_count > 5:
                return None

        # Benzersiz değer sayısı eşiği
        if distinct_count < 2 or distinct_count > self.ENUM_MAX_DISTINCT:
            return None

        # Değer listesi oluştur — frekans analizi
        enum_values: list[dict[str, Any]] = []
        for item in most_common:
            val = item.get("value")
            count = item.get("count", 0)
            ratio = item.get("ratio", 0.0)

            if val is not None and ratio >= self.ENUM_MIN_FREQUENCY:
                enum_values.append({
                    "value": val,
                    "frequency": round(ratio, 4),
                })

        if len(enum_values) < 2:
            return None

        # Semantik tipe göre bilinen enum ile karşılaştır
        known_enum = _SEMANTIC_ENUMS.get(semantic_type or "", [])
        if known_enum:
            observed_values = {str(e["value"]).lower() for e in enum_values}
            overlap = observed_values & {v.lower() for v in known_enum}
            match_ratio = len(overlap) / max(len(observed_values), 1) if observed_values else 0.0
        else:
            match_ratio = 1.0

        confidence = self._compute_confidence(
            base_confidence=0.88,
            null_ratio=null_ratio,
            sample_size=total_count,
            match_ratio=max(match_ratio, 0.5),
        )

        return InferredRuleResult(
            rule_id=str(uuid.uuid4()),
            column_name=col_name,
            rule_type="ENUM",
            definition={
                "values": [e["value"] for e in enum_values],
                "frequencies": {str(e["value"]): e["frequency"] for e in enum_values},
                "allow_null": null_ratio > self.NOT_NULL_THRESHOLD,
                "distinct_count": distinct_count,
            },
            confidence=round(confidence, 3),
            description=(
                f"Sabit değer kümesi — {distinct_count} benzersiz değer: "
                f"{', '.join(str(e['value']) for e in enum_values[:5])}"
                f"{'...' if len(enum_values) > 5 else ''}"
            ),
        )

    def _infer_range(
        self, col: Any, semantic_type: Optional[str] = None
    ) -> Optional[InferredRuleResult]:
        """
        RANGE kuralı çıkarır.

        Sayısal kolonlar için percentile bazlı min/max aralığı belirler.
        Semantik tipe göre bankacılık domainine uygun sınırlar kullanılır.

        Args:
            col: ColumnAnalysis nesnesi
            semantic_type: Semantik tip (varsa)

        Returns:
            InferredRuleResult veya None
        """
        col_name = getattr(col, "name", "")
        data_type = getattr(col, "data_type", "string")
        total_count = getattr(col, "total_count", 0) or 0
        null_ratio = getattr(col, "null_ratio", 0.0) or 0.0

        # Sadece sayısal tipler
        if data_type not in ("integer", "float", "decimal"):
            return None

        # Min/max değerleri al
        try:
            min_val = float(getattr(col, "min_value", None))
            max_val = float(getattr(col, "max_value", None))
        except (TypeError, ValueError):
            return None

        mean_val = getattr(col, "mean_value", None)
        std_val = getattr(col, "std_value", None)
        median_val = getattr(col, "median_value", None)

        # Percentile bazlı aralık — istatistiklerden hesapla
        distribution_info = getattr(col, "distribution", None) or {}
        quartiles = distribution_info.get("quartiles", {})

        # P1/P99 veya Q1-IQR/Q3+IQR tabanlı aralık hesaplama
        if quartiles:
            q1 = quartiles.get("q1", min_val)
            q3 = quartiles.get("q3", max_val)
            iqr = q3 - q1 if q1 is not None and q3 is not None else 0
            range_min = max(min_val, q1 - 1.5 * iqr) if iqr > 0 else min_val
            range_max = min(max_val, q3 + 1.5 * iqr) if iqr > 0 else max_val
        else:
            range_min = min_val
            range_max = max_val

        # Semantik tipe göre domain sınırları uygula
        domain_range = _SEMANTIC_RANGES.get(semantic_type or "", {})
        if domain_range:
            # Domain sınırlarını kullan ama gözlemlenen veriyle harmanlama
            range_min = max(range_min, domain_range.get("min", range_min))
            range_max = min(range_max, domain_range.get("max", range_max))

        # Integer ise tam sayıya yuvarla
        if data_type == "integer":
            range_min = int(math.floor(range_min))
            range_max = int(math.ceil(range_max))

        # Temel confidence
        base_conf = 0.85 if domain_range else 0.78
        confidence = self._compute_confidence(
            base_confidence=base_conf,
            null_ratio=null_ratio,
            sample_size=total_count,
        )

        definition: dict[str, Any] = {
            "min": range_min,
            "max": range_max,
            "observed_min": min_val,
            "observed_max": max_val,
        }
        if mean_val is not None:
            definition["mean"] = round(mean_val, 4)
        if std_val is not None:
            definition["std"] = round(std_val, 4)
        if median_val is not None:
            definition["median"] = round(median_val, 4)
        if data_type == "integer":
            definition["data_type"] = "integer"

        return InferredRuleResult(
            rule_id=str(uuid.uuid4()),
            column_name=col_name,
            rule_type="RANGE",
            definition=definition,
            confidence=round(confidence, 3),
            description=(
                f"Değer aralığı [{range_min} — {range_max}]"
                f"{' (' + semantic_type + ')' if semantic_type else ''}"
            ),
        )

    def _infer_length(self, col: Any) -> Optional[InferredRuleResult]:
        """
        LENGTH kuralı çıkarır.

        String kolonlar için minimum ve maksimum karakter uzunluğu belirler.

        Args:
            col: ColumnAnalysis nesnesi

        Returns:
            InferredRuleResult veya None
        """
        data_type = getattr(col, "data_type", "string")
        if data_type != "string":
            return None

        min_length = getattr(col, "min_length", None)
        max_length = getattr(col, "max_length", None)
        avg_length = getattr(col, "avg_length", None)
        total_count = getattr(col, "total_count", 0) or 0
        null_ratio = getattr(col, "null_ratio", 0.0) or 0.0

        if min_length is None or max_length is None:
            return None

        if min_length == 0 and max_length == 0:
            return None

        confidence = self._compute_confidence(
            base_confidence=0.82,
            null_ratio=null_ratio,
            sample_size=total_count,
        )

        definition: dict[str, Any] = {
            "min_length": min_length,
            "max_length": max_length,
        }
        if avg_length is not None:
            definition["avg_length"] = round(avg_length, 2)

        return InferredRuleResult(
            rule_id=str(uuid.uuid4()),
            column_name=getattr(col, "name", ""),
            rule_type="LENGTH",
            definition=definition,
            confidence=round(confidence, 3),
            description=f"String uzunluk [{min_length} — {max_length}] karakter",
        )

    def _infer_distribution(
        self, col: Any, semantic_type: Optional[str] = None
    ) -> Optional[InferredRuleResult]:
        """
        DISTRIBUTION kuralı çıkarır.

        Sayısal kolonlar için istatistiksel dağılım tipini ve parametrelerini belirler.
        Desteklenen dağılımlar: normal, lognormal, uniform, exponential, skewed.

        Args:
            col: ColumnAnalysis nesnesi
            semantic_type: Semantik tip (varsa)

        Returns:
            InferredRuleResult veya None
        """
        data_type = getattr(col, "data_type", "string")
        if data_type not in ("integer", "float", "decimal"):
            return None

        mean_val = getattr(col, "mean_value", None)
        std_val = getattr(col, "std_value", None)
        median_val = getattr(col, "median_value", None)
        total_count = getattr(col, "total_count", 0) or 0
        null_ratio = getattr(col, "null_ratio", 0.0) or 0.0
        distribution_info = getattr(col, "distribution", None) or {}

        if mean_val is None or std_val is None:
            return None

        # Dağılım tipini tespit et
        dist_type = "normal"  # varsayılan
        dist_params: dict[str, Any] = {"mean": round(mean_val, 4), "std": round(std_val, 4)}

        # Semantik tipe göre bilinen dağılım
        domain_range = _SEMANTIC_RANGES.get(semantic_type or "", {})
        if domain_range and "distribution" in domain_range:
            dist_type = domain_range["distribution"]
            dist_params.update(domain_range.get("params", {}))
            # Gözlemlenen değerlerle güncelle
            dist_params["mean"] = round(mean_val, 4)
            dist_params["std"] = round(std_val, 4)
        else:
            # Çarpıklık analizi ile dağılım tespiti
            skewness = distribution_info.get("skewness")
            kurtosis = distribution_info.get("kurtosis")

            if skewness is not None:
                if abs(skewness) < 0.5:
                    dist_type = "normal"
                elif skewness > 2.0:
                    dist_type = "lognormal"
                elif skewness > 0.5:
                    dist_type = "skewed_right"
                elif skewness < -0.5:
                    dist_type = "skewed_left"

            # Uniform kontrolü — düşük std / range oranı
            try:
                min_val = float(getattr(col, "min_value", 0))
                max_val = float(getattr(col, "max_value", 0))
                value_range = max_val - min_val
                if value_range > 0 and std_val / value_range < 0.15:
                    dist_type = "uniform"
                    dist_params["low"] = round(min_val, 4)
                    dist_params["high"] = round(max_val, 4)
            except (TypeError, ValueError, ZeroDivisionError):
                pass

        if median_val is not None:
            dist_params["median"] = round(median_val, 4)

        confidence = self._compute_confidence(
            base_confidence=0.75,
            null_ratio=null_ratio,
            sample_size=total_count,
        )

        return InferredRuleResult(
            rule_id=str(uuid.uuid4()),
            column_name=getattr(col, "name", ""),
            rule_type="DISTRIBUTION",
            definition={
                "distribution": dist_type,
                "params": dist_params,
            },
            confidence=round(confidence, 3),
            description=f"Dağılım: {dist_type} (μ={mean_val:.2f}, σ={std_val:.2f})",
        )

    def _infer_date_range(self, col: Any) -> Optional[InferredRuleResult]:
        """
        Tarih kolonları için RANGE kuralı çıkarır.

        Args:
            col: ColumnAnalysis nesnesi

        Returns:
            InferredRuleResult veya None
        """
        data_type = getattr(col, "data_type", "string")
        if data_type not in ("date", "datetime"):
            return None

        min_val = getattr(col, "min_value", None)
        max_val = getattr(col, "max_value", None)
        total_count = getattr(col, "total_count", 0) or 0
        null_ratio = getattr(col, "null_ratio", 0.0) or 0.0
        pattern = getattr(col, "pattern", None)

        if not min_val or not max_val:
            return None

        confidence = self._compute_confidence(
            base_confidence=0.80,
            null_ratio=null_ratio,
            sample_size=total_count,
        )

        definition: dict[str, Any] = {
            "min_date": str(min_val),
            "max_date": str(max_val),
            "data_type": data_type,
        }
        if pattern:
            definition["format"] = pattern

        return InferredRuleResult(
            rule_id=str(uuid.uuid4()),
            column_name=getattr(col, "name", ""),
            rule_type="RANGE",
            definition=definition,
            confidence=round(confidence, 3),
            description=f"Tarih aralığı [{min_val} — {max_val}]",
        )

    def _infer_dependencies(
        self,
        columns: list[Any],
        classifications: Optional[dict[str, Any]] = None,
    ) -> list[InferredRuleResult]:
        """
        Kolonlar arası DEPENDENCY kuralları çıkarır.

        Bilinen bağımlılıklar (bankacılık domaini):
          - işlem_tarihi > hesap_acilis_tarihi
          - vade_tarihi > işlem_tarihi
          - kullanilabilir_bakiye <= toplam_bakiye
          - kart_limit > 0 ise hesap_tipi = kredi

        Args:
            columns: Tüm ColumnAnalysis nesneleri listesi
            classifications: Kolon adı → semantik tip eşleştirmesi

        Returns:
            DEPENDENCY kuralları listesi
        """
        rules: list[InferredRuleResult] = []
        cls = classifications or {}

        # Kolon adlarını semantik tiplerine göre grupla
        col_by_semantic: dict[str, str] = {}
        for col in columns:
            col_name = getattr(col, "name", "")
            semantic = cls.get(col_name, getattr(col, "semantic_type", None))
            if semantic:
                col_by_semantic[semantic] = col_name

        # Tarih bağımlılıkları — işlem tarihi > hesap açılış tarihi
        date_deps = [
            ("transaction_date", "birth_date", ">", "İşlem tarihi doğum tarihinden sonra olmalı"),
            ("maturity_date", "transaction_date", ">=", "Vade tarihi işlem tarihinden sonra olmalı"),
        ]
        for later_type, earlier_type, op, desc in date_deps:
            later_col = col_by_semantic.get(later_type)
            earlier_col = col_by_semantic.get(earlier_type)
            if later_col and earlier_col:
                rules.append(InferredRuleResult(
                    rule_id=str(uuid.uuid4()),
                    column_name=later_col,
                    rule_type="DEPENDENCY",
                    definition={
                        "depends_on": earlier_col,
                        "operator": op,
                        "dependency_type": "temporal",
                    },
                    confidence=0.85,
                    description=desc,
                ))

        # Finansal bağımlılıklar
        balance_col = col_by_semantic.get("balance")
        limit_col = col_by_semantic.get("card_limit")
        if balance_col and limit_col:
            rules.append(InferredRuleResult(
                rule_id=str(uuid.uuid4()),
                column_name=balance_col,
                rule_type="DEPENDENCY",
                definition={
                    "depends_on": limit_col,
                    "operator": "<=",
                    "dependency_type": "financial_constraint",
                },
                confidence=0.70,
                description="Bakiye kart limitini geçmemeli (kredi hesapları için)",
            ))

        return rules

    def _infer_conditionals(
        self,
        columns: list[Any],
        classifications: Optional[dict[str, Any]] = None,
    ) -> list[InferredRuleResult]:
        """
        CONDITIONAL kurallar çıkarır.

        Bankacılık domain bilgisine dayalı koşullu kurallar:
          - segment=premium → bakiye > 100000
          - hesap_tipi=vadeli → vade_tarihi NOT NULL
          - musteri_tipi=kurumsal → segment IN (ticari, kurumsal)

        Args:
            columns: Tüm ColumnAnalysis nesneleri listesi
            classifications: Kolon adı → semantik tip eşleştirmesi

        Returns:
            CONDITIONAL kuralları listesi
        """
        rules: list[InferredRuleResult] = []
        cls = classifications or {}

        # Kolon adlarını semantik tiplerine göre grupla
        col_by_semantic: dict[str, str] = {}
        for col in columns:
            col_name = getattr(col, "name", "")
            semantic = cls.get(col_name, getattr(col, "semantic_type", None))
            if semantic:
                col_by_semantic[semantic] = col_name

        segment_col = col_by_semantic.get("segment")
        balance_col = col_by_semantic.get("balance")
        account_type_col = col_by_semantic.get("account_type")
        maturity_col = col_by_semantic.get("maturity_date")

        # Premium segment → yüksek bakiye
        if segment_col and balance_col:
            rules.append(InferredRuleResult(
                rule_id=str(uuid.uuid4()),
                column_name=balance_col,
                rule_type="CONDITIONAL",
                definition={
                    "condition": {
                        "column": segment_col,
                        "operator": "in",
                        "value": ["premium", "vip", "platinum"],
                    },
                    "then": {
                        "column": balance_col,
                        "operator": ">",
                        "value": 100_000,
                    },
                },
                confidence=0.72,
                description="Premium/VIP segment → bakiye > 100.000 TL",
            ))

        # Vadeli hesap → vade tarihi zorunlu
        if account_type_col and maturity_col:
            rules.append(InferredRuleResult(
                rule_id=str(uuid.uuid4()),
                column_name=maturity_col,
                rule_type="CONDITIONAL",
                definition={
                    "condition": {
                        "column": account_type_col,
                        "operator": "==",
                        "value": "vadeli",
                    },
                    "then": {
                        "column": maturity_col,
                        "operator": "not_null",
                    },
                },
                confidence=0.80,
                description="Vadeli hesap → vade tarihi zorunlu",
            ))

        return rules

    # ═════════════════════════════════════════════════════════════════
    # Ana Çıkarım Metodu
    # ═════════════════════════════════════════════════════════════════

    def infer_rules(
        self,
        analysis_result: Any,
        classifications: Optional[dict[str, str]] = None,
    ) -> RuleInferenceReport:
        """
        Tüm kolonlar için kuralları otomatik çıkarır.

        SchemaAnalyzer'dan gelen AnalysisResult ve ColumnClassifier'dan gelen
        semantik tip eşleştirmelerini kullanarak kapsamlı kural seti üretir.

        Args:
            analysis_result: SchemaAnalyzer'dan gelen AnalysisResult nesnesi.
                Beklenen alanlar: columns (list[ColumnAnalysis]), file_name
            classifications: Kolon adı → semantik tip string eşleştirmesi
                Örnek: {"bakiye": "balance", "musteri_no": "customer_id"}

        Returns:
            RuleInferenceReport — Tüm çıkarılmış kurallar ve istatistikler
        """
        columns = getattr(analysis_result, "columns", [])
        dataset_name = getattr(analysis_result, "file_name", "unknown")
        cls_map = classifications or {}

        all_rules: list[InferredRuleResult] = []

        logger.info(
            "Kural çıkarımı başlıyor — %d kolon, veri seti: '%s'",
            len(columns), dataset_name,
        )

        for col in columns:
            col_name = getattr(col, "name", "")
            semantic_type = cls_map.get(col_name, getattr(col, "semantic_type", None))

            try:
                # 1. NOT_NULL kuralı
                not_null = self._infer_not_null(col)
                if not_null and not_null.confidence >= self.MIN_CONFIDENCE:
                    all_rules.append(not_null)

                # 2. UNIQUE kuralı
                unique = self._infer_unique(col)
                if unique and unique.confidence >= self.MIN_CONFIDENCE:
                    all_rules.append(unique)

                # 3. REGEX kuralı
                regex = self._infer_regex(col, semantic_type)
                if regex and regex.confidence >= self.MIN_CONFIDENCE:
                    all_rules.append(regex)

                # 4. ENUM kuralı (REGEX yoksa — çakışma önleme)
                if not regex:
                    enum_rule = self._infer_enum(col, semantic_type)
                    if enum_rule and enum_rule.confidence >= self.MIN_CONFIDENCE:
                        all_rules.append(enum_rule)

                # 5. RANGE kuralı (sayısal)
                range_rule = self._infer_range(col, semantic_type)
                if range_rule and range_rule.confidence >= self.MIN_CONFIDENCE:
                    all_rules.append(range_rule)

                # 6. Tarih RANGE kuralı
                date_range = self._infer_date_range(col)
                if date_range and date_range.confidence >= self.MIN_CONFIDENCE:
                    all_rules.append(date_range)

                # 7. LENGTH kuralı
                length = self._infer_length(col)
                if length and length.confidence >= self.MIN_CONFIDENCE:
                    all_rules.append(length)

                # 8. DISTRIBUTION kuralı
                dist = self._infer_distribution(col, semantic_type)
                if dist and dist.confidence >= self.MIN_CONFIDENCE:
                    all_rules.append(dist)

            except Exception as e:
                logger.warning(
                    "Kolon '%s' için kural çıkarma hatası: %s", col_name, str(e)
                )
                continue

        # 9. DEPENDENCY kuralları (kolon çiftleri arası)
        try:
            deps = self._infer_dependencies(columns, cls_map)
            all_rules.extend(r for r in deps if r.confidence >= self.MIN_CONFIDENCE)
        except Exception as e:
            logger.warning("Bağımlılık kuralı çıkarma hatası: %s", str(e))

        # 10. CONDITIONAL kurallar
        try:
            conditionals = self._infer_conditionals(columns, cls_map)
            all_rules.extend(r for r in conditionals if r.confidence >= self.MIN_CONFIDENCE)
        except Exception as e:
            logger.warning("Koşullu kural çıkarma hatası: %s", str(e))

        # Rapor oluştur
        rules_by_type: dict[str, int] = {}
        for r in all_rules:
            rules_by_type[r.rule_type] = rules_by_type.get(r.rule_type, 0) + 1

        avg_conf = (
            sum(r.confidence for r in all_rules) / len(all_rules)
            if all_rules else 0.0
        )

        report = RuleInferenceReport(
            dataset_name=dataset_name,
            total_columns=len(columns),
            total_rules=len(all_rules),
            rules_by_type=rules_by_type,
            avg_confidence=avg_conf,
            rules=all_rules,
        )

        logger.info(
            "Kural çıkarımı tamamlandı — %d kolon, %d kural üretildi "
            "(ortalama güven: %.3f). Tip dağılımı: %s",
            len(columns), len(all_rules), avg_conf, rules_by_type,
        )

        return report

    # ═════════════════════════════════════════════════════════════════
    # Kural Doğrulama
    # ═════════════════════════════════════════════════════════════════

    def validate_rules(
        self,
        rules: list[InferredRuleResult],
        data: Any,
    ) -> list[ValidationResult]:
        """
        Kuralları mevcut veriye karşı doğrular.

        Her kural için ihlal sayısı ve oranını hesaplar.

        Args:
            rules: Doğrulanacak kurallar listesi
            data: pandas DataFrame formatında veri

        Returns:
            ValidationResult listesi
        """
        import pandas as pd

        results: list[ValidationResult] = []

        if not isinstance(data, pd.DataFrame):
            logger.error("validate_rules — veri pandas DataFrame olmalı")
            return results

        total_rows = len(data)

        for rule in rules:
            col_name = rule.column_name

            # Kolon veri setinde var mı?
            if col_name not in data.columns:
                results.append(ValidationResult(
                    rule_id=rule.rule_id,
                    column_name=col_name,
                    rule_type=rule.rule_type,
                    is_valid=False,
                    total_rows=total_rows,
                    violation_count=total_rows,
                    violation_ratio=1.0,
                    sample_violations=[f"Kolon '{col_name}' veri setinde bulunamadı"],
                ))
                continue

            series = data[col_name]
            violation_mask = None
            violations: list[Any] = []

            try:
                if rule.rule_type == "NOT_NULL":
                    violation_mask = series.isna()

                elif rule.rule_type == "UNIQUE":
                    duplicated = series.duplicated(keep=False)
                    violation_mask = duplicated & ~series.isna()

                elif rule.rule_type == "RANGE":
                    defn = rule.definition
                    if "min" in defn and "max" in defn:
                        numeric_series = pd.to_numeric(series, errors="coerce")
                        non_null = ~numeric_series.isna()
                        below = numeric_series < defn["min"]
                        above = numeric_series > defn["max"]
                        violation_mask = non_null & (below | above)
                    elif "min_date" in defn and "max_date" in defn:
                        # Tarih aralığı doğrulama
                        date_series = pd.to_datetime(series, errors="coerce")
                        non_null = ~date_series.isna()
                        try:
                            min_dt = pd.to_datetime(defn["min_date"])
                            max_dt = pd.to_datetime(defn["max_date"])
                            below = date_series < min_dt
                            above = date_series > max_dt
                            violation_mask = non_null & (below | above)
                        except Exception:
                            violation_mask = pd.Series([False] * total_rows)

                elif rule.rule_type == "ENUM":
                    allowed = set(str(v) for v in rule.definition.get("values", []))
                    non_null = ~series.isna()
                    not_in_enum = ~series.astype(str).isin(allowed)
                    violation_mask = non_null & not_in_enum

                elif rule.rule_type == "REGEX":
                    pattern_str = rule.definition.get("pattern", "")
                    if pattern_str:
                        non_null = ~series.isna()
                        matches = series.astype(str).str.match(pattern_str, na=False)
                        violation_mask = non_null & ~matches

                elif rule.rule_type == "LENGTH":
                    defn = rule.definition
                    min_len = defn.get("min_length", 0)
                    max_len = defn.get("max_length", float("inf"))
                    non_null = ~series.isna()
                    lengths = series.astype(str).str.len()
                    too_short = lengths < min_len
                    too_long = lengths > max_len
                    violation_mask = non_null & (too_short | too_long)

                # İhlal hesapla
                if violation_mask is not None:
                    violation_count = int(violation_mask.sum())
                    violation_ratio = violation_count / total_rows if total_rows > 0 else 0.0

                    # Örnek ihlaller (en fazla 5)
                    if violation_count > 0:
                        sample_idx = violation_mask[violation_mask].index[:5]
                        violations = series.loc[sample_idx].tolist()

                    results.append(ValidationResult(
                        rule_id=rule.rule_id,
                        column_name=col_name,
                        rule_type=rule.rule_type,
                        is_valid=violation_count == 0,
                        total_rows=total_rows,
                        violation_count=violation_count,
                        violation_ratio=round(violation_ratio, 6),
                        sample_violations=violations,
                    ))
                else:
                    # Doğrulanamayan kural tipi (DEPENDENCY, CONDITIONAL vb.)
                    results.append(ValidationResult(
                        rule_id=rule.rule_id,
                        column_name=col_name,
                        rule_type=rule.rule_type,
                        is_valid=True,
                        total_rows=total_rows,
                        violation_count=0,
                        violation_ratio=0.0,
                        sample_violations=[],
                    ))

            except Exception as e:
                logger.warning(
                    "Kural doğrulama hatası (kural=%s, kolon=%s): %s",
                    rule.rule_id, col_name, str(e),
                )
                results.append(ValidationResult(
                    rule_id=rule.rule_id,
                    column_name=col_name,
                    rule_type=rule.rule_type,
                    is_valid=False,
                    total_rows=total_rows,
                    violation_count=0,
                    violation_ratio=0.0,
                    sample_violations=[f"Doğrulama hatası: {str(e)}"],
                ))

        return results

    # ═════════════════════════════════════════════════════════════════
    # Dışa / İçe Aktarma (Export / Import)
    # ═════════════════════════════════════════════════════════════════

    def export_rules(
        self,
        rules: list[InferredRuleResult],
        file_path: str,
        format: str = "json",
    ) -> str:
        """
        Kuralları JSON veya YAML dosyasına dışa aktarır.

        Args:
            rules: Dışa aktarılacak kurallar listesi
            file_path: Hedef dosya yolu
            format: Dosya formatı — "json" veya "yaml"

        Returns:
            Yazılan dosyanın mutlak yolu
        """
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        rules_data = [r.to_dict() for r in rules]
        export_data = {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "total_rules": len(rules_data),
            "rules": rules_data,
        }

        if format.lower() == "yaml":
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    export_data, f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

        logger.info("Kurallar dışa aktarıldı — %s (%d kural)", output_path, len(rules_data))
        return str(output_path.resolve())

    def import_rules(
        self,
        file_path: str,
    ) -> list[InferredRuleResult]:
        """
        JSON veya YAML dosyasından kuralları içe aktarır.

        Args:
            file_path: Kaynak dosya yolu

        Returns:
            İçe aktarılan kurallar listesi

        Raises:
            FileNotFoundError: Dosya bulunamazsa
            ValueError: Geçersiz dosya formatıysa
        """
        input_path = Path(file_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Kural dosyası bulunamadı: {file_path}")

        suffix = input_path.suffix.lower()
        with open(input_path, "r", encoding="utf-8") as f:
            if suffix in (".yaml", ".yml"):
                raw_data = yaml.safe_load(f)
            elif suffix == ".json":
                raw_data = json.load(f)
            else:
                raise ValueError(f"Desteklenmeyen dosya formatı: {suffix}")

        # Uyumlu format kontrolü
        if isinstance(raw_data, dict) and "rules" in raw_data:
            rules_list = raw_data["rules"]
        elif isinstance(raw_data, list):
            rules_list = raw_data
        else:
            raise ValueError("Geçersiz kural dosyası formatı — 'rules' listesi bekleniyor")

        imported: list[InferredRuleResult] = []
        for item in rules_list:
            if not isinstance(item, dict):
                continue
            try:
                rule = InferredRuleResult(
                    rule_id=item.get("rule_id", str(uuid.uuid4())),
                    column_name=item.get("column_name", ""),
                    rule_type=item.get("rule_type", "RANGE"),
                    definition=item.get("definition", {}),
                    confidence=float(item.get("confidence", 0.0)),
                    is_active=bool(item.get("is_active", True)),
                    description=item.get("description", ""),
                    source=item.get("source", "imported"),
                    created_at=item.get("created_at", ""),
                )
                imported.append(rule)
            except Exception as e:
                logger.warning("Kural içe aktarma atlandı: %s — %s", item, str(e))

        logger.info("Kurallar içe aktarıldı — %s (%d kural)", input_path, len(imported))
        return imported

    # ═════════════════════════════════════════════════════════════════
    # Veritabanı Entegrasyonu
    # ═════════════════════════════════════════════════════════════════

    def save_to_db(
        self,
        rules: list[InferredRuleResult],
        dataset_id: int,
        db_session: Any,
    ) -> list[Any]:
        """
        Kuralları InferredRule ORM modeli ile veritabanına kaydeder.

        Args:
            rules: Kaydedilecek kurallar listesi
            dataset_id: Ait olduğu veri seti ID'si
            db_session: SQLAlchemy Session nesnesi

        Returns:
            Oluşturulan InferredRule ORM nesneleri listesi
        """
        from app.models.dataset import InferredRule as InferredRuleModel

        orm_objects: list[Any] = []

        for rule in rules:
            orm_dict = rule.to_orm_dict()
            orm_obj = InferredRuleModel(
                dataset_id=dataset_id,
                column_name=orm_dict["column_name"],
                rule_type=orm_dict["rule_type"],
                rule_definition=orm_dict["rule_definition"],
                confidence_score=orm_dict["confidence_score"],
                is_active=orm_dict["is_active"],
            )
            db_session.add(orm_obj)
            orm_objects.append(orm_obj)

        try:
            db_session.commit()
            logger.info(
                "Kurallar veritabanına kaydedildi — dataset_id=%d, %d kural",
                dataset_id, len(orm_objects),
            )
        except Exception as e:
            db_session.rollback()
            logger.error(
                "Kural kaydetme hatası (dataset_id=%d): %s", dataset_id, str(e)
            )
            raise

        return orm_objects

    def load_from_db(
        self,
        dataset_id: int,
        db_session: Any,
        active_only: bool = True,
    ) -> list[InferredRuleResult]:
        """
        Veritabanından kuralları yükler ve InferredRuleResult listesine dönüştürür.

        Args:
            dataset_id: Veri seti ID'si
            db_session: SQLAlchemy Session nesnesi
            active_only: Yalnızca aktif kuralları yükle

        Returns:
            InferredRuleResult listesi
        """
        from app.models.dataset import InferredRule as InferredRuleModel

        query = db_session.query(InferredRuleModel).filter(
            InferredRuleModel.dataset_id == dataset_id
        )
        if active_only:
            query = query.filter(InferredRuleModel.is_active.is_(True))

        orm_rules = query.all()
        results: list[InferredRuleResult] = []

        for orm_obj in orm_rules:
            definition = orm_obj.rule_definition or {}
            # Genişletilmiş tipi definition'dan geri al
            extended_type = definition.pop("extended_type", None)
            rule_type = extended_type or orm_obj.rule_type.value.upper()

            results.append(InferredRuleResult(
                rule_id=str(orm_obj.id),
                column_name=orm_obj.column_name,
                rule_type=rule_type,
                definition=definition,
                confidence=orm_obj.confidence_score,
                is_active=orm_obj.is_active,
                source="database",
            ))

        logger.info(
            "Kurallar veritabanından yüklendi — dataset_id=%d, %d kural",
            dataset_id, len(results),
        )
        return results

    # ═════════════════════════════════════════════════════════════════
    # YAML Tabanlı Kural Dosyası Yükleme (Eski API uyumluluğu)
    # ═════════════════════════════════════════════════════════════════

    def load_rules_from_dir(self) -> list[InferredRuleResult]:
        """
        rules/ klasöründeki tüm JSON ve YAML dosyalarını yükler.

        Eski RuleEngine API'si ile geriye dönük uyumludur.

        Returns:
            Yüklenen kurallar listesi
        """
        all_rules: list[InferredRuleResult] = []

        if not self.rules_dir.exists():
            logger.warning("Kural klasörü bulunamadı: %s", self.rules_dir)
            return all_rules

        for pattern in ("*.json", "*.yaml", "*.yml"):
            for rule_file in self.rules_dir.glob(pattern):
                try:
                    imported = self.import_rules(str(rule_file))
                    all_rules.extend(imported)
                except Exception as e:
                    logger.warning("Kural dosyası yükleme hatası (%s): %s", rule_file, str(e))

        logger.info(
            "Klasörden kurallar yüklendi — %s (%d dosya, %d kural)",
            self.rules_dir, len(list(self.rules_dir.glob("*"))), len(all_rules),
        )
        return all_rules

    def get_rules_for_column(
        self,
        rules: list[InferredRuleResult],
        column_name: str,
        rule_types: Optional[list[str]] = None,
    ) -> list[InferredRuleResult]:
        """
        Belirli bir kolon için geçerli kuralları filtreler.

        Args:
            rules: Tüm kurallar listesi
            column_name: Kolon adı
            rule_types: İsteğe bağlı tip filtresi

        Returns:
            Filtrelenmiş kurallar listesi
        """
        filtered = [r for r in rules if r.column_name == column_name and r.is_active]
        if rule_types:
            filtered = [r for r in filtered if r.rule_type in rule_types]
        return filtered
