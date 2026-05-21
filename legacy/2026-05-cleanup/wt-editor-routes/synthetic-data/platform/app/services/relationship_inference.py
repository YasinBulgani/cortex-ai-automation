"""
İlişki Çıkarım Motoru — RelationshipInference Modülü.

Veri setleri (tablolar) arasındaki ilişkileri otomatik olarak tespit eder.
Kolon adı eşleştirme, semantik tip analizi, değer kümesi karşılaştırma ve
referential integrity kontrolü ile yabancı anahtar ve mantıksal ilişkileri bulur.

Bankacılık domainine özel ilişki desenleri:
  - customer → accounts (1:N, customer_id)
  - customer → cards (1:N, customer_id)
  - account → transactions (1:N, account_id)
  - customer → credits (1:N, customer_id)
  - account → deposits (1:N, account_id)
  - branch → customers (1:N, branch_code)

Yetenekler:
  - Kolon adı ve semantik tip eşleştirme (fuzzy matching destekli)
  - Değer kümesi örtüşme analizi (Jaccard benzerliği)
  - Referential integrity doğrulama
  - Kardinalite analizi (1:1, 1:N, N:1, N:N)
  - İlişki güven skoru hesaplama
  - İlişki grafiği oluşturma ve topological sort
  - Döngü tespiti (cycle detection)
  - Çoklu dataset arası ilişki tespiti
  - TableRelationship ORM uyumlu kaydetme/okuma
  - JSON export/import
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from app.models.dataset import (
    Cardinality,
    RelationshipType,
    TableRelationship,
)
from app.services.column_classifier import SemanticType

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Veri Yapıları
# ═══════════════════════════════════════════════════════════════════════


class RelationshipDirection(str, Enum):
    """İlişki yönü — veri üretim sırasını belirler."""

    PARENT_TO_CHILD = "parent_to_child"   # Ebeveyn → çocuk (1:N'de parent tarafı)
    CHILD_TO_PARENT = "child_to_parent"   # Çocuk → ebeveyn (FK sahibi)
    BIDIRECTIONAL = "bidirectional"        # Çift yönlü (N:N)


@dataclass
class ColumnInfo:
    """
    İlişki tespitinde kullanılan kolon bilgisi.

    Dataset analiz sonuçlarından veya doğrudan sağlanan bilgilerden oluşturulur.
    """

    name: str                                      # Kolon adı
    dataset_id: int                                # Ait olduğu dataset ID
    dataset_name: str = ""                         # Dataset adı (okunabilirlik)
    semantic_type: Optional[SemanticType] = None   # Semantik tip
    data_type: str = "string"                      # Veri tipi (string, integer vb.)
    distinct_count: int = 0                        # Benzersiz değer sayısı
    total_count: int = 0                           # Toplam değer sayısı
    null_ratio: float = 0.0                        # NULL oranı
    sample_values: list[Any] = field(default_factory=list)  # Örnek değerler


@dataclass
class RelationshipCandidate:
    """
    Tespit edilen ilişki adayı — doğrulama öncesi ham sonuç.

    Birden fazla sinyal kaynağından birleştirilerek nihai skor hesaplanır.
    """

    source_dataset_id: int                         # Kaynak dataset ID
    source_dataset_name: str                       # Kaynak dataset adı
    source_column: str                             # Kaynak kolon adı
    target_dataset_id: int                         # Hedef dataset ID
    target_dataset_name: str                       # Hedef dataset adı
    target_column: str                             # Hedef kolon adı

    # İlişki özellikleri
    relationship_type: RelationshipType = RelationshipType.INFERRED
    cardinality: Cardinality = Cardinality.ONE_TO_MANY
    direction: RelationshipDirection = RelationshipDirection.PARENT_TO_CHILD
    confidence_score: float = 0.0                  # Birleşik güven skoru

    # Alt sinyaller — skor bileşenleri
    name_match_score: float = 0.0                  # Kolon adı benzerliği
    semantic_match_score: float = 0.0              # Semantik tip uyumu
    value_overlap_score: float = 0.0               # Değer kümesi örtüşmesi
    referential_integrity_score: float = 0.0       # Referential integrity

    # Ek bilgiler
    reasoning: str = ""                            # Tespit gerekçesi
    is_banking_domain: bool = False                # Bankacılık domain ilişkisi mi?

    def to_dict(self) -> dict[str, Any]:
        """JSON serializable dict'e dönüştürür."""
        return {
            "source_dataset_id": self.source_dataset_id,
            "source_dataset_name": self.source_dataset_name,
            "source_column": self.source_column,
            "target_dataset_id": self.target_dataset_id,
            "target_dataset_name": self.target_dataset_name,
            "target_column": self.target_column,
            "relationship_type": self.relationship_type.value,
            "cardinality": self.cardinality.value,
            "direction": self.direction.value,
            "confidence_score": round(self.confidence_score, 3),
            "name_match_score": round(self.name_match_score, 3),
            "semantic_match_score": round(self.semantic_match_score, 3),
            "value_overlap_score": round(self.value_overlap_score, 3),
            "referential_integrity_score": round(self.referential_integrity_score, 3),
            "reasoning": self.reasoning,
            "is_banking_domain": self.is_banking_domain,
        }


@dataclass
class RelationshipGraph:
    """
    Dataset'ler arası ilişki grafiği.

    Topological sort ile veri üretim sırasını belirler,
    döngü tespiti yapar ve bağımlılık ağacını görselleştirir.
    """

    nodes: list[int] = field(default_factory=list)              # Dataset ID'leri
    node_names: dict[int, str] = field(default_factory=dict)    # ID → isim eşleştirmesi
    edges: list[RelationshipCandidate] = field(default_factory=list)  # İlişki kenarları
    adjacency: dict[int, list[int]] = field(default_factory=lambda: defaultdict(list))
    in_degree: dict[int, int] = field(default_factory=lambda: defaultdict(int))

    # Analiz sonuçları
    generation_order: list[int] = field(default_factory=list)   # Topological sort sırası
    has_cycle: bool = False                                     # Döngü var mı?
    cycle_nodes: list[int] = field(default_factory=list)        # Döngüdeki node'lar
    connected_components: list[list[int]] = field(default_factory=list)  # Bağlı bileşenler

    def to_dict(self) -> dict[str, Any]:
        """JSON serializable dict'e dönüştürür."""
        return {
            "nodes": self.nodes,
            "node_names": {str(k): v for k, v in self.node_names.items()},
            "edges": [e.to_dict() for e in self.edges],
            "generation_order": self.generation_order,
            "generation_order_names": [
                self.node_names.get(nid, str(nid)) for nid in self.generation_order
            ],
            "has_cycle": self.has_cycle,
            "cycle_nodes": self.cycle_nodes,
            "connected_components": self.connected_components,
        }


@dataclass
class InferenceReport:
    """
    İlişki çıkarım raporu — dataset bazlı özet.
    """

    dataset_count: int = 0                         # Analiz edilen dataset sayısı
    relationship_count: int = 0                    # Tespit edilen ilişki sayısı
    avg_confidence: float = 0.0                    # Ortalama güven skoru
    banking_domain_count: int = 0                  # Bankacılık domain ilişkisi sayısı
    type_distribution: dict[str, int] = field(default_factory=dict)
    cardinality_distribution: dict[str, int] = field(default_factory=dict)
    graph: Optional[RelationshipGraph] = None      # İlişki grafiği

    def to_dict(self) -> dict[str, Any]:
        """JSON serializable dict'e dönüştürür."""
        return {
            "dataset_count": self.dataset_count,
            "relationship_count": self.relationship_count,
            "avg_confidence": round(self.avg_confidence, 3),
            "banking_domain_count": self.banking_domain_count,
            "type_distribution": self.type_distribution,
            "cardinality_distribution": self.cardinality_distribution,
            "graph": self.graph.to_dict() if self.graph else None,
        }


# ═══════════════════════════════════════════════════════════════════════
# Bankacılık Domain İlişki Desenleri
# ═══════════════════════════════════════════════════════════════════════

# Her desen: (kaynak_tablo_pattern, hedef_tablo_pattern, bağlayıcı_kolon, kardinalite)
# Kaynak = parent (1 tarafı), Hedef = child (N tarafı)


@dataclass
class BankingRelationshipPattern:
    """Bankacılık domain'ine özgü ilişki deseni."""

    source_table_keywords: list[str]     # Kaynak tablo adı anahtar kelimeleri
    target_table_keywords: list[str]     # Hedef tablo adı anahtar kelimeleri
    link_column_keywords: list[str]      # Bağlayıcı kolon adı anahtar kelimeleri
    link_semantic_type: Optional[SemanticType]  # Bağlayıcı kolon semantik tipi
    cardinality: Cardinality             # Beklenen kardinalite
    description: str                     # Açıklama


# Bankacılık ilişki desenleri — yaygın banka veri modeli ilişkileri
_BANKING_PATTERNS: list[BankingRelationshipPattern] = [
    BankingRelationshipPattern(
        source_table_keywords=["customer", "musteri", "client", "muteri"],
        target_table_keywords=["account", "hesap", "acc"],
        link_column_keywords=["customer_id", "musteri_no", "musteri_id", "cust_id", "client_id"],
        link_semantic_type=SemanticType.CUSTOMER_ID,
        cardinality=Cardinality.ONE_TO_MANY,
        description="Müşteri → Hesaplar (bir müşterinin birden fazla hesabı olabilir)",
    ),
    BankingRelationshipPattern(
        source_table_keywords=["customer", "musteri", "client"],
        target_table_keywords=["card", "kart", "kredi_karti", "credit_card"],
        link_column_keywords=["customer_id", "musteri_no", "musteri_id", "cust_id"],
        link_semantic_type=SemanticType.CUSTOMER_ID,
        cardinality=Cardinality.ONE_TO_MANY,
        description="Müşteri → Kartlar (bir müşterinin birden fazla kartı olabilir)",
    ),
    BankingRelationshipPattern(
        source_table_keywords=["account", "hesap", "acc"],
        target_table_keywords=["transaction", "islem", "hareket", "tx"],
        link_column_keywords=["account_id", "hesap_no", "hesap_id", "acc_id"],
        link_semantic_type=SemanticType.ACCOUNT_ID,
        cardinality=Cardinality.ONE_TO_MANY,
        description="Hesap → İşlemler (bir hesapta birden fazla işlem olabilir)",
    ),
    BankingRelationshipPattern(
        source_table_keywords=["customer", "musteri", "client"],
        target_table_keywords=["credit", "kredi", "loan", "borc"],
        link_column_keywords=["customer_id", "musteri_no", "musteri_id", "cust_id"],
        link_semantic_type=SemanticType.CUSTOMER_ID,
        cardinality=Cardinality.ONE_TO_MANY,
        description="Müşteri → Krediler (bir müşterinin birden fazla kredisi olabilir)",
    ),
    BankingRelationshipPattern(
        source_table_keywords=["account", "hesap", "acc"],
        target_table_keywords=["deposit", "mevduat", "vadeli"],
        link_column_keywords=["account_id", "hesap_no", "hesap_id", "acc_id"],
        link_semantic_type=SemanticType.ACCOUNT_ID,
        cardinality=Cardinality.ONE_TO_MANY,
        description="Hesap → Mevduatlar (bir hesapta birden fazla mevduat olabilir)",
    ),
    BankingRelationshipPattern(
        source_table_keywords=["branch", "sube", "subeler"],
        target_table_keywords=["customer", "musteri", "client"],
        link_column_keywords=["branch_code", "sube_kodu", "branch_id", "sube_no"],
        link_semantic_type=SemanticType.BRANCH_CODE,
        cardinality=Cardinality.ONE_TO_MANY,
        description="Şube → Müşteriler (bir şubede birden fazla müşteri olabilir)",
    ),
    BankingRelationshipPattern(
        source_table_keywords=["branch", "sube"],
        target_table_keywords=["account", "hesap", "acc"],
        link_column_keywords=["branch_code", "sube_kodu", "branch_id", "sube_no"],
        link_semantic_type=SemanticType.BRANCH_CODE,
        cardinality=Cardinality.ONE_TO_MANY,
        description="Şube → Hesaplar (bir şubede birden fazla hesap olabilir)",
    ),
    BankingRelationshipPattern(
        source_table_keywords=["customer", "musteri", "client"],
        target_table_keywords=["address", "adres", "iletisim", "contact"],
        link_column_keywords=["customer_id", "musteri_no", "musteri_id", "cust_id"],
        link_semantic_type=SemanticType.CUSTOMER_ID,
        cardinality=Cardinality.ONE_TO_MANY,
        description="Müşteri → Adresler (bir müşterinin birden fazla adresi olabilir)",
    ),
]

# İlişki bağlayıcı kolon desenleri — kolon adından ilişki tespiti
# Sondaki _id, _no, _code gibi son ekler yabancı anahtar işaret eder
_FK_SUFFIXES: list[str] = [
    "_id", "_no", "_code", "_key", "_ref",
    "_numarasi", "_kodu", "_kimlik",
]

# Semantik tip → olası parent tablo eşleştirmesi
_SEMANTIC_TO_TABLE: dict[SemanticType, list[str]] = {
    SemanticType.CUSTOMER_ID: ["customer", "musteri", "client"],
    SemanticType.ACCOUNT_ID: ["account", "hesap", "acc"],
    SemanticType.BRANCH_CODE: ["branch", "sube"],
}


# ═══════════════════════════════════════════════════════════════════════
# Levenshtein Mesafe (yerel kopya — bağımsızlık için)
# ═══════════════════════════════════════════════════════════════════════


def _levenshtein_ratio(s1: str, s2: str) -> float:
    """
    İki string arasındaki benzerlik oranını hesaplar (0.0 — 1.0).

    Args:
        s1: Birinci string
        s2: İkinci string

    Returns:
        Benzerlik oranı (1.0 = aynı)
    """
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0

    # Dinamik programlama — Levenshtein mesafesi
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return 1.0 - (prev_row[-1] / max_len)


def _normalize_name(name: str) -> str:
    """
    Kolon/tablo adını normalize eder (küçük harf, Türkçe → ASCII).

    Args:
        name: Ham isim

    Returns:
        Normalize edilmiş isim
    """
    result = name.lower().strip()
    # Türkçe karakter dönüşümü
    tr_map = str.maketrans({
        "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
        "Ç": "c", "Ğ": "g", "İ": "i", "Ö": "o", "Ş": "s", "Ü": "u",
    })
    result = result.translate(tr_map)
    # Alfanumerik olmayan karakterleri alt çizgiye çevir
    result = "".join(c if c.isalnum() or c == "_" else "_" for c in result)
    # Birden fazla alt çizgiyi tek alt çizgiye indir
    while "__" in result:
        result = result.replace("__", "_")
    return result.strip("_")


# ═══════════════════════════════════════════════════════════════════════
# Ana Sınıf — RelationshipInference
# ═══════════════════════════════════════════════════════════════════════


class RelationshipInference:
    """
    Tablolar Arası İlişki Çıkarım Motoru.

    Birden fazla veri seti (tablo) arasındaki ilişkileri otomatik olarak tespit eder.
    Kolon adı eşleştirme, semantik tip analizi, değer kümesi karşılaştırma ve
    referential integrity kontrolü ile çok katmanlı ilişki çıkarımı yapar.

    Kullanım:
        engine = RelationshipInference()

        # Kolon bilgilerini ekle
        engine.add_dataset_columns(dataset_id=1, name="customers", columns=[...])
        engine.add_dataset_columns(dataset_id=2, name="accounts", columns=[...])

        # İlişkileri çıkar
        candidates = engine.infer_relationships()

        # İlişki grafiği oluştur
        graph = engine.build_relationship_graph(candidates)

        # Veri üretim sırasını al
        order = graph.generation_order
    """

    # Sinyal ağırlıkları — güven skoru hesaplamada kullanılır
    NAME_MATCH_WEIGHT: float = 0.30          # Kolon adı eşleşme ağırlığı
    SEMANTIC_MATCH_WEIGHT: float = 0.25      # Semantik tip uyum ağırlığı
    VALUE_OVERLAP_WEIGHT: float = 0.25       # Değer örtüşme ağırlığı
    REFERENTIAL_INTEGRITY_WEIGHT: float = 0.20  # Referential integrity ağırlığı

    # Eşik değerleri
    MIN_CONFIDENCE: float = 0.40             # Minimum güven skoru
    MIN_VALUE_OVERLAP: float = 0.10          # Minimum değer örtüşme oranı
    FUZZY_THRESHOLD: float = 0.75            # Fuzzy matching eşiği
    BANKING_DOMAIN_BONUS: float = 0.15       # Bankacılık domain bonus skoru

    def __init__(
        self,
        min_confidence: float = 0.40,
        banking_domain_bonus: float = 0.15,
    ) -> None:
        """
        RelationshipInference yapıcısı.

        Args:
            min_confidence: Minimum güven skoru eşiği (0.0 — 1.0)
            banking_domain_bonus: Bankacılık domain pattern eşleşme bonusu
        """
        self.MIN_CONFIDENCE = min_confidence
        self.BANKING_DOMAIN_BONUS = banking_domain_bonus

        # Dataset kolon bilgileri — dataset_id → kolon listesi
        self._datasets: dict[int, list[ColumnInfo]] = {}
        # Dataset isimleri — dataset_id → isim
        self._dataset_names: dict[int, str] = {}

        logger.info(
            "RelationshipInference başlatıldı — min_confidence=%.2f, "
            "banking_bonus=%.2f",
            self.MIN_CONFIDENCE, self.BANKING_DOMAIN_BONUS,
        )

    # ── Dataset Yönetimi ──────────────────────────────────────────────

    def add_dataset_columns(
        self,
        dataset_id: int,
        name: str,
        columns: list[ColumnInfo],
    ) -> None:
        """
        Analiz edilecek dataset kolon bilgilerini ekler.

        Args:
            dataset_id: Dataset ID
            name: Dataset adı (tablo adı)
            columns: Kolon bilgileri listesi
        """
        self._datasets[dataset_id] = columns
        self._dataset_names[dataset_id] = name

        # Kolon bilgilerinde dataset referanslarını güncelle
        for col in columns:
            col.dataset_id = dataset_id
            col.dataset_name = name

        logger.info(
            "Dataset eklendi: id=%d, name='%s', kolon_sayısı=%d",
            dataset_id, name, len(columns),
        )

    def add_dataset_from_analysis(
        self,
        dataset_id: int,
        name: str,
        column_analyses: list[Any],
        classification_results: Optional[list[Any]] = None,
    ) -> None:
        """
        SchemaAnalyzer ve ColumnClassifier sonuçlarından dataset ekler.

        Args:
            dataset_id: Dataset ID
            name: Dataset adı
            column_analyses: SchemaAnalyzer ColumnAnalysis nesneleri
            classification_results: ColumnClassifier ClassificationResult nesneleri
        """
        columns: list[ColumnInfo] = []
        # Sınıflandırma sonuçlarını kolon adına göre indeksle
        classification_map: dict[str, Any] = {}
        if classification_results:
            for cr in classification_results:
                col_name = getattr(cr, "column_name", "")
                classification_map[col_name] = cr

        for ca in column_analyses:
            col_name = getattr(ca, "name", "unknown")
            # Semantik tipi sınıflandırma sonucundan al
            semantic_type = None
            cr = classification_map.get(col_name)
            if cr:
                st = getattr(cr, "semantic_type", None)
                if st and isinstance(st, SemanticType) and st != SemanticType.UNKNOWN:
                    semantic_type = st

            col_info = ColumnInfo(
                name=col_name,
                dataset_id=dataset_id,
                dataset_name=name,
                semantic_type=semantic_type,
                data_type=getattr(ca, "data_type", "string"),
                distinct_count=int(
                    getattr(ca, "distinct_ratio", 0.0)
                    * getattr(ca, "total_count", 0)
                ),
                total_count=getattr(ca, "total_count", 0),
                null_ratio=getattr(ca, "null_ratio", 0.0),
                sample_values=getattr(ca, "sample_values", []) or [],
            )
            columns.append(col_info)

        self.add_dataset_columns(dataset_id, name, columns)

    def clear(self) -> None:
        """Tüm dataset bilgilerini temizler."""
        self._datasets.clear()
        self._dataset_names.clear()
        logger.info("Tüm dataset bilgileri temizlendi.")

    # ── Kolon Adı Eşleştirme ──────────────────────────────────────────

    def _compute_name_match_score(
        self, col_a: ColumnInfo, col_b: ColumnInfo
    ) -> float:
        """
        İki kolon arasında isim benzerliğine dayalı eşleşme skoru hesaplar.

        Aynı isim veya bilinen FK son ekleri (ör. customer_id — customers.id)
        kontrolü yapılır.

        Args:
            col_a: Birinci kolon
            col_b: İkinci kolon

        Returns:
            Eşleşme skoru (0.0 — 1.0)
        """
        name_a = _normalize_name(col_a.name)
        name_b = _normalize_name(col_b.name)

        # 1) Tam eşleşme
        if name_a == name_b:
            return 0.95

        # 2) FK pattern kontrolü — col_a "xxx_id" ise col_b.table "xxx" veya "xxxs"
        for suffix in _FK_SUFFIXES:
            if name_a.endswith(suffix):
                base = name_a[: -len(suffix)]
                target_table = _normalize_name(col_b.dataset_name)
                # Tablo adı eşleşmesi (tekil/çoğul)
                if base and (
                    target_table == base
                    or target_table == base + "s"
                    or target_table.startswith(base)
                ):
                    # Hedef kolon "id" veya primary key ise
                    if name_b in ("id", f"{base}_id", "no", f"{base}_no"):
                        return 0.90
                    return 0.70

            if name_b.endswith(suffix):
                base = name_b[: -len(suffix)]
                source_table = _normalize_name(col_a.dataset_name)
                if base and (
                    source_table == base
                    or source_table == base + "s"
                    or source_table.startswith(base)
                ):
                    if name_a in ("id", f"{base}_id", "no", f"{base}_no"):
                        return 0.90
                    return 0.70

        # 3) Fuzzy matching — Levenshtein benzerliği
        ratio = _levenshtein_ratio(name_a, name_b)
        if ratio >= self.FUZZY_THRESHOLD:
            return ratio * 0.80  # Fuzzy eşleşme → max %80 güven

        return 0.0

    # ── Semantik Tip Eşleştirme ────────────────────────────────────────

    def _compute_semantic_match_score(
        self, col_a: ColumnInfo, col_b: ColumnInfo
    ) -> float:
        """
        İki kolon arasında semantik tip uyumunu kontrol eder.

        Aynı semantik tipe sahip kolonlar ilişki adayıdır.

        Args:
            col_a: Birinci kolon
            col_b: İkinci kolon

        Returns:
            Uyum skoru (0.0 — 1.0)
        """
        if col_a.semantic_type is None or col_b.semantic_type is None:
            return 0.0

        # Aynı semantik tip → yüksek uyum
        if col_a.semantic_type == col_b.semantic_type:
            # ID/key tipler için daha yüksek güven
            if col_a.semantic_type in (
                SemanticType.CUSTOMER_ID,
                SemanticType.ACCOUNT_ID,
                SemanticType.BRANCH_CODE,
            ):
                return 0.95

            # Diğer eşleşen tipler
            return 0.70

        # Uyumlu tip çiftleri (ör. ACCOUNT_NUMBER ↔ ACCOUNT_ID)
        compatible_pairs: list[tuple[SemanticType, SemanticType]] = [
            (SemanticType.ACCOUNT_NUMBER, SemanticType.ACCOUNT_ID),
            (SemanticType.CUSTOMER_ID, SemanticType.NATIONAL_ID),
        ]
        pair = (col_a.semantic_type, col_b.semantic_type)
        reverse_pair = (col_b.semantic_type, col_a.semantic_type)
        if pair in compatible_pairs or reverse_pair in compatible_pairs:
            return 0.60

        return 0.0

    # ── Değer Kümesi Analizi ──────────────────────────────────────────

    def _compute_value_overlap_score(
        self, col_a: ColumnInfo, col_b: ColumnInfo
    ) -> float:
        """
        İki kolon arasında değer kümesi örtüşmesini hesaplar (Jaccard benzerliği).

        Args:
            col_a: Birinci kolon (potansiyel child — FK tarafı)
            col_b: İkinci kolon (potansiyel parent — PK tarafı)

        Returns:
            Örtüşme skoru (0.0 — 1.0)
        """
        values_a = set(str(v) for v in col_a.sample_values if v is not None)
        values_b = set(str(v) for v in col_b.sample_values if v is not None)

        if not values_a or not values_b:
            return 0.0

        intersection = values_a & values_b
        if not intersection:
            return 0.0

        # Jaccard benzerliği
        union = values_a | values_b
        jaccard = len(intersection) / len(union) if union else 0.0

        # Inclusion oranı — child değerlerinin kaçı parent'ta var
        inclusion_ratio = len(intersection) / len(values_a) if values_a else 0.0

        # İkisinin ağırlıklı ortalaması (inclusion daha önemli)
        score = (jaccard * 0.4) + (inclusion_ratio * 0.6)
        return min(score, 1.0)

    # ── Referential Integrity ─────────────────────────────────────────

    def _compute_referential_integrity(
        self, child_col: ColumnInfo, parent_col: ColumnInfo
    ) -> float:
        """
        Referential integrity skorunu hesaplar.

        Child kolonundaki tüm değerlerin parent kolonunda mevcut olup olmadığını
        kontrol eder (örnek değerler üzerinden yaklaşık hesaplama).

        Args:
            child_col: Child kolon (FK tarafı)
            parent_col: Parent kolon (PK tarafı)

        Returns:
            RI skoru (0.0 — 1.0)
        """
        child_values = set(str(v) for v in child_col.sample_values if v is not None)
        parent_values = set(str(v) for v in parent_col.sample_values if v is not None)

        if not child_values or not parent_values:
            return 0.0

        # Child'daki kaç değer parent'ta bulunuyor
        matched = child_values & parent_values
        ri_score = len(matched) / len(child_values) if child_values else 0.0

        return ri_score

    # ── Kardinalite Analizi ───────────────────────────────────────────

    def _determine_cardinality(
        self, col_a: ColumnInfo, col_b: ColumnInfo
    ) -> Cardinality:
        """
        İki kolon arasındaki kardinaliteyi belirler.

        Distinct oranlarına bakarak 1:1, 1:N, N:1 veya N:N ilişki tipini tespit eder.

        Args:
            col_a: Kaynak kolon
            col_b: Hedef kolon

        Returns:
            Kardinalite enum değeri
        """
        # Distinct ratio hesapla
        ratio_a = (col_a.distinct_count / col_a.total_count
                   if col_a.total_count > 0 else 0.0)
        ratio_b = (col_b.distinct_count / col_b.total_count
                   if col_b.total_count > 0 else 0.0)

        # Yüksek benzersizlik → unique (PK tarafı)
        a_is_unique = ratio_a > 0.95
        b_is_unique = ratio_b > 0.95

        if a_is_unique and b_is_unique:
            return Cardinality.ONE_TO_ONE
        elif a_is_unique and not b_is_unique:
            # A unique, B tekrarlı → A parent, B child → 1:N
            return Cardinality.ONE_TO_MANY
        elif not a_is_unique and b_is_unique:
            # A tekrarlı, B unique → N:1
            return Cardinality.MANY_TO_ONE
        else:
            # İkisi de tekrarlı → N:N
            return Cardinality.MANY_TO_MANY

    # ── Bankacılık Domain Eşleştirme ──────────────────────────────────

    def _check_banking_pattern(
        self,
        source_name: str,
        target_name: str,
        col_a: ColumnInfo,
        col_b: ColumnInfo,
    ) -> Optional[BankingRelationshipPattern]:
        """
        Bankacılık domain ilişki desenlerini kontrol eder.

        Args:
            source_name: Kaynak dataset adı
            target_name: Hedef dataset adı
            col_a: Kaynak kolon
            col_b: Hedef kolon

        Returns:
            Eşleşen pattern veya None
        """
        norm_source = _normalize_name(source_name)
        norm_target = _normalize_name(target_name)
        norm_col_a = _normalize_name(col_a.name)
        norm_col_b = _normalize_name(col_b.name)

        for pattern in _BANKING_PATTERNS:
            # Tablo adı kontrolü — düz yön
            source_match = any(kw in norm_source for kw in pattern.source_table_keywords)
            target_match = any(kw in norm_target for kw in pattern.target_table_keywords)

            if not (source_match and target_match):
                # Ters yönü de dene
                source_match_rev = any(kw in norm_target for kw in pattern.source_table_keywords)
                target_match_rev = any(kw in norm_source for kw in pattern.target_table_keywords)
                if not (source_match_rev and target_match_rev):
                    continue

            # Bağlayıcı kolon kontrolü
            col_match = (
                any(kw in norm_col_a for kw in pattern.link_column_keywords)
                or any(kw in norm_col_b for kw in pattern.link_column_keywords)
            )

            # Semantik tip kontrolü
            sem_match = False
            if pattern.link_semantic_type:
                sem_match = (
                    col_a.semantic_type == pattern.link_semantic_type
                    or col_b.semantic_type == pattern.link_semantic_type
                )

            if col_match or sem_match:
                return pattern

        return None

    # ── İlişki Skoru Hesaplama ────────────────────────────────────────

    def _compute_confidence_score(
        self,
        name_score: float,
        semantic_score: float,
        value_score: float,
        ri_score: float,
        is_banking_domain: bool,
    ) -> float:
        """
        Çoklu sinyal kaynaklarından birleşik güven skoru hesaplar.

        Args:
            name_score: Kolon adı eşleşme skoru
            semantic_score: Semantik tip uyum skoru
            value_score: Değer örtüşme skoru
            ri_score: Referential integrity skoru
            is_banking_domain: Bankacılık domain pattern eşleşmesi

        Returns:
            Birleşik güven skoru (0.0 — 1.0)
        """
        # Ağırlıklı toplam
        weighted_score = (
            name_score * self.NAME_MATCH_WEIGHT
            + semantic_score * self.SEMANTIC_MATCH_WEIGHT
            + value_score * self.VALUE_OVERLAP_WEIGHT
            + ri_score * self.REFERENTIAL_INTEGRITY_WEIGHT
        )

        # Bankacılık domain bonusu
        if is_banking_domain:
            weighted_score += self.BANKING_DOMAIN_BONUS

        # Birden fazla sinyal uyum bonusu
        active_signals = sum(
            1 for s in [name_score, semantic_score, value_score, ri_score] if s > 0.1
        )
        if active_signals >= 3:
            weighted_score *= 1.10  # %10 bonus — 3+ sinyal uyumu
        if active_signals >= 4:
            weighted_score *= 1.05  # Ek %5 bonus — tüm sinyaller uyumlu

        return min(weighted_score, 1.0)

    # ── İlişki Çıkarım (Ana Metod) ───────────────────────────────────

    def infer_relationships(self) -> list[RelationshipCandidate]:
        """
        Tüm dataset çiftleri arasındaki ilişkileri tespit eder.

        Her dataset çifti için kolon adı, semantik tip, değer örtüşme ve
        referential integrity analizi yaparak ilişki adayları üretir.

        Returns:
            RelationshipCandidate listesi (güven skoruna göre sıralı)
        """
        candidates: list[RelationshipCandidate] = []
        dataset_ids = list(self._datasets.keys())

        if len(dataset_ids) < 2:
            logger.warning(
                "İlişki tespiti için en az 2 dataset gerekli. Mevcut: %d",
                len(dataset_ids),
            )
            return candidates

        logger.info(
            "İlişki çıkarımı başlıyor — %d dataset, %d olası çift",
            len(dataset_ids),
            len(dataset_ids) * (len(dataset_ids) - 1) // 2,
        )

        # Her dataset çifti için kontrol
        for i, ds_a_id in enumerate(dataset_ids):
            for ds_b_id in dataset_ids[i + 1:]:
                pair_candidates = self._infer_pair_relationships(ds_a_id, ds_b_id)
                candidates.extend(pair_candidates)

        # Güven skoruna göre sırala (yüksekten düşüğe)
        candidates.sort(key=lambda c: c.confidence_score, reverse=True)

        # Çakışan ilişkileri filtrele — aynı kolon çifti için en iyiyi tut
        filtered = self._filter_duplicate_relationships(candidates)

        logger.info(
            "İlişki çıkarımı tamamlandı — %d aday tespit edildi, "
            "%d aday filtreleme sonrası kaldı",
            len(candidates), len(filtered),
        )

        return filtered

    def _infer_pair_relationships(
        self, ds_a_id: int, ds_b_id: int
    ) -> list[RelationshipCandidate]:
        """
        İki dataset arasındaki ilişkileri tespit eder.

        Args:
            ds_a_id: Birinci dataset ID
            ds_b_id: İkinci dataset ID

        Returns:
            İlişki adayları listesi
        """
        candidates: list[RelationshipCandidate] = []
        cols_a = self._datasets.get(ds_a_id, [])
        cols_b = self._datasets.get(ds_b_id, [])
        name_a = self._dataset_names.get(ds_a_id, str(ds_a_id))
        name_b = self._dataset_names.get(ds_b_id, str(ds_b_id))

        for col_a in cols_a:
            for col_b in cols_b:
                # Aynı veri tipi ailesinde olmalı (string↔string, int↔int)
                if not self._compatible_data_types(col_a.data_type, col_b.data_type):
                    continue

                # Sinyal skorlarını hesapla
                name_score = self._compute_name_match_score(col_a, col_b)
                semantic_score = self._compute_semantic_match_score(col_a, col_b)
                value_score = self._compute_value_overlap_score(col_a, col_b)
                ri_score = self._compute_referential_integrity(col_a, col_b)

                # Bankacılık domain kontrolü
                banking_pattern = self._check_banking_pattern(
                    name_a, name_b, col_a, col_b
                )
                is_banking = banking_pattern is not None

                # Birleşik güven skoru
                confidence = self._compute_confidence_score(
                    name_score, semantic_score, value_score, ri_score, is_banking,
                )

                # Minimum güven eşiği kontrolü
                if confidence < self.MIN_CONFIDENCE:
                    continue

                # Kardinalite belirle
                cardinality = self._determine_cardinality(col_a, col_b)
                if banking_pattern:
                    cardinality = banking_pattern.cardinality

                # Yönü belirle — parent → child
                source_id, target_id = ds_a_id, ds_b_id
                source_name, target_name = name_a, name_b
                source_col, target_col = col_a.name, col_b.name

                # Eğer B parent ve A child ise yönü çevir
                if cardinality == Cardinality.MANY_TO_ONE:
                    source_id, target_id = ds_b_id, ds_a_id
                    source_name, target_name = name_b, name_a
                    source_col, target_col = col_b.name, col_a.name
                    cardinality = Cardinality.ONE_TO_MANY

                # İlişki tipini belirle
                rel_type = RelationshipType.INFERRED
                if name_score >= 0.90:
                    rel_type = RelationshipType.FOREIGN_KEY
                elif is_banking:
                    rel_type = RelationshipType.LOGICAL

                # Gerekçe oluştur
                reasons: list[str] = []
                if name_score > 0:
                    reasons.append(f"kolon_adı_eşleşme={name_score:.2f}")
                if semantic_score > 0:
                    reasons.append(f"semantik_uyum={semantic_score:.2f}")
                if value_score > 0:
                    reasons.append(f"değer_örtüşme={value_score:.2f}")
                if ri_score > 0:
                    reasons.append(f"referential_integrity={ri_score:.2f}")
                if is_banking and banking_pattern:
                    reasons.append(
                        f"bankacılık_domain='{banking_pattern.description}'"
                    )

                candidate = RelationshipCandidate(
                    source_dataset_id=source_id,
                    source_dataset_name=source_name,
                    source_column=source_col,
                    target_dataset_id=target_id,
                    target_dataset_name=target_name,
                    target_column=target_col,
                    relationship_type=rel_type,
                    cardinality=cardinality,
                    direction=RelationshipDirection.PARENT_TO_CHILD,
                    confidence_score=confidence,
                    name_match_score=name_score,
                    semantic_match_score=semantic_score,
                    value_overlap_score=value_score,
                    referential_integrity_score=ri_score,
                    reasoning="; ".join(reasons),
                    is_banking_domain=is_banking,
                )
                candidates.append(candidate)

        return candidates

    def _compatible_data_types(self, type_a: str, type_b: str) -> bool:
        """
        İki veri tipinin ilişki için uyumlu olup olmadığını kontrol eder.

        Args:
            type_a: Birinci veri tipi
            type_b: İkinci veri tipi

        Returns:
            Uyumlu ise True
        """
        # Tip ailesi grupları
        numeric_types = {"integer", "float", "decimal", "bigint", "smallint", "numeric"}
        string_types = {"string", "varchar", "text", "char", "nvarchar"}
        date_types = {"date", "datetime", "timestamp"}

        a_lower = type_a.lower()
        b_lower = type_b.lower()

        # Aynı tip
        if a_lower == b_lower:
            return True

        # Aynı aile
        if a_lower in numeric_types and b_lower in numeric_types:
            return True
        if a_lower in string_types and b_lower in string_types:
            return True
        if a_lower in date_types and b_lower in date_types:
            return True

        # String ↔ herhangi bir tip (string olarak saklanan ID'ler)
        if a_lower in string_types or b_lower in string_types:
            return True

        return False

    def _filter_duplicate_relationships(
        self, candidates: list[RelationshipCandidate]
    ) -> list[RelationshipCandidate]:
        """
        Çakışan ilişki adaylarını filtreler — aynı kolon çifti için en iyiyi tutar.

        Args:
            candidates: Sıralı aday listesi

        Returns:
            Filtrelenmiş aday listesi
        """
        seen_pairs: set[tuple[int, str, int, str]] = set()
        filtered: list[RelationshipCandidate] = []

        for candidate in candidates:
            pair_key = (
                candidate.source_dataset_id,
                candidate.source_column,
                candidate.target_dataset_id,
                candidate.target_column,
            )
            # Ters yönü de kontrol et
            reverse_key = (
                candidate.target_dataset_id,
                candidate.target_column,
                candidate.source_dataset_id,
                candidate.source_column,
            )

            if pair_key not in seen_pairs and reverse_key not in seen_pairs:
                seen_pairs.add(pair_key)
                filtered.append(candidate)

        return filtered

    # ── İlişki Grafiği ────────────────────────────────────────────────

    def build_relationship_graph(
        self, candidates: list[RelationshipCandidate]
    ) -> RelationshipGraph:
        """
        İlişki adaylarından yönlü graf oluşturur.

        Topological sort ile veri üretim sırasını belirler ve
        döngü tespiti yapar.

        Args:
            candidates: İlişki adayları listesi

        Returns:
            RelationshipGraph nesnesi
        """
        graph = RelationshipGraph()

        # Node'ları topla
        all_nodes: set[int] = set()
        for ds_id in self._datasets:
            all_nodes.add(ds_id)
        for c in candidates:
            all_nodes.add(c.source_dataset_id)
            all_nodes.add(c.target_dataset_id)

        graph.nodes = sorted(all_nodes)
        graph.node_names = {**self._dataset_names}
        graph.edges = candidates

        # Adjacency list ve in-degree oluştur
        # Kenar yönü: parent → child (source → target)
        adjacency: dict[int, list[int]] = defaultdict(list)
        in_degree: dict[int, int] = {n: 0 for n in all_nodes}

        for c in candidates:
            adjacency[c.source_dataset_id].append(c.target_dataset_id)
            in_degree[c.target_dataset_id] = in_degree.get(c.target_dataset_id, 0) + 1

        graph.adjacency = adjacency
        graph.in_degree = in_degree

        # Topological sort (Kahn algoritması)
        generation_order, has_cycle = self._topological_sort(
            graph.nodes, adjacency, dict(in_degree)
        )
        graph.generation_order = generation_order
        graph.has_cycle = has_cycle

        # Döngü tespiti
        if has_cycle:
            graph.cycle_nodes = self._detect_cycle_nodes(graph.nodes, adjacency)
            logger.warning(
                "Döngü tespit edildi! Döngüdeki node'lar: %s",
                graph.cycle_nodes,
            )

        # Bağlı bileşenler (connected components)
        graph.connected_components = self._find_connected_components(
            graph.nodes, adjacency
        )

        logger.info(
            "İlişki grafiği oluşturuldu — %d node, %d edge, döngü=%s, "
            "bileşen=%d, üretim_sırası=%s",
            len(graph.nodes), len(graph.edges), graph.has_cycle,
            len(graph.connected_components),
            [graph.node_names.get(n, str(n)) for n in graph.generation_order],
        )

        return graph

    def _topological_sort(
        self,
        nodes: list[int],
        adjacency: dict[int, list[int]],
        in_degree: dict[int, int],
    ) -> tuple[list[int], bool]:
        """
        Kahn algoritması ile topological sort.

        Veri üretim sırasını belirler: parent tablolar önce, child tablolar sonra.

        Args:
            nodes: Node ID listesi
            adjacency: Adjacency list
            in_degree: In-degree sayıları

        Returns:
            (sıralı_node_listesi, döngü_var_mı) çifti
        """
        # Gelen kenarı olmayan node'larla başla (root tablolar)
        queue: deque[int] = deque()
        for node in nodes:
            if in_degree.get(node, 0) == 0:
                queue.append(node)

        result: list[int] = []
        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Tüm node'lar işlenmemişse döngü var demektir
        has_cycle = len(result) != len(nodes)

        # Döngü varsa, kalan node'ları da ekle (üretim sırası tam olsun)
        if has_cycle:
            remaining = [n for n in nodes if n not in result]
            result.extend(remaining)

        return result, has_cycle

    def _detect_cycle_nodes(
        self,
        nodes: list[int],
        adjacency: dict[int, list[int]],
    ) -> list[int]:
        """
        DFS ile döngüdeki node'ları tespit eder.

        Args:
            nodes: Node ID listesi
            adjacency: Adjacency list

        Returns:
            Döngüde yer alan node ID listesi
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[int, int] = {n: WHITE for n in nodes}
        cycle_nodes: set[int] = set()

        def dfs(node: int) -> bool:
            """DFS ile döngü tespiti (True = döngü bulundu)."""
            color[node] = GRAY
            for neighbor in adjacency.get(node, []):
                if color.get(neighbor, WHITE) == GRAY:
                    # Back edge — döngü!
                    cycle_nodes.add(node)
                    cycle_nodes.add(neighbor)
                    return True
                if color.get(neighbor, WHITE) == WHITE:
                    if dfs(neighbor):
                        cycle_nodes.add(node)
                        return True
            color[node] = BLACK
            return False

        for node in nodes:
            if color.get(node, WHITE) == WHITE:
                dfs(node)

        return sorted(cycle_nodes)

    def _find_connected_components(
        self,
        nodes: list[int],
        adjacency: dict[int, list[int]],
    ) -> list[list[int]]:
        """
        Yönsüz graf olarak bağlı bileşenleri bulur (BFS).

        Args:
            nodes: Node ID listesi
            adjacency: Adjacency list (yönlü)

        Returns:
            Bağlı bileşenler listesi
        """
        # Yönsüz adjacency oluştur
        undirected: dict[int, set[int]] = defaultdict(set)
        for src, targets in adjacency.items():
            for tgt in targets:
                undirected[src].add(tgt)
                undirected[tgt].add(src)

        visited: set[int] = set()
        components: list[list[int]] = []

        for node in nodes:
            if node in visited:
                continue
            # BFS ile bileşeni bul
            component: list[int] = []
            bfs_queue: deque[int] = deque([node])
            visited.add(node)
            while bfs_queue:
                current = bfs_queue.popleft()
                component.append(current)
                for neighbor in undirected.get(current, set()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        bfs_queue.append(neighbor)
            components.append(sorted(component))

        return components

    # ── Veritabanı Entegrasyonu ───────────────────────────────────────

    def save_to_db(
        self,
        candidates: list[RelationshipCandidate],
        db_session: Any,
        clear_existing: bool = True,
    ) -> list[TableRelationship]:
        """
        İlişki adaylarını veritabanına TableRelationship olarak kaydeder.

        Args:
            candidates: İlişki adayları listesi
            db_session: SQLAlchemy Session nesnesi
            clear_existing: Mevcut ilişkileri silip yeniden oluştur

        Returns:
            Kaydedilen TableRelationship ORM nesneleri
        """
        saved: list[TableRelationship] = []

        try:
            if clear_existing:
                # İlgili dataset'lerin mevcut ilişkilerini sil
                ds_ids: set[int] = set()
                for c in candidates:
                    ds_ids.add(c.source_dataset_id)
                    ds_ids.add(c.target_dataset_id)

                if ds_ids:
                    db_session.query(TableRelationship).filter(
                        (TableRelationship.source_dataset_id.in_(ds_ids))
                        | (TableRelationship.target_dataset_id.in_(ds_ids))
                    ).delete(synchronize_session="fetch")

            for candidate in candidates:
                rel = TableRelationship(
                    source_dataset_id=candidate.source_dataset_id,
                    source_column=candidate.source_column,
                    target_dataset_id=candidate.target_dataset_id,
                    target_column=candidate.target_column,
                    relationship_type=candidate.relationship_type,
                    cardinality=candidate.cardinality,
                    confidence_score=candidate.confidence_score,
                )
                db_session.add(rel)
                saved.append(rel)

            db_session.commit()
            logger.info(
                "%d ilişki veritabanına kaydedildi.",
                len(saved),
            )

        except Exception as e:
            db_session.rollback()
            logger.error("İlişkiler DB'ye kaydedilemedi: %s", str(e))
            raise

        return saved

    def load_from_db(
        self,
        db_session: Any,
        dataset_ids: Optional[list[int]] = None,
    ) -> list[RelationshipCandidate]:
        """
        Veritabanından ilişkileri yükler ve RelationshipCandidate'e dönüştürür.

        Args:
            db_session: SQLAlchemy Session nesnesi
            dataset_ids: Filtrelenecek dataset ID'leri (None = tümü)

        Returns:
            RelationshipCandidate listesi
        """
        try:
            query = db_session.query(TableRelationship)

            if dataset_ids:
                query = query.filter(
                    (TableRelationship.source_dataset_id.in_(dataset_ids))
                    | (TableRelationship.target_dataset_id.in_(dataset_ids))
                )

            relationships = query.all()
            candidates: list[RelationshipCandidate] = []

            for rel in relationships:
                # Dataset isimlerini al
                source_name = self._dataset_names.get(
                    rel.source_dataset_id, str(rel.source_dataset_id)
                )
                target_name = self._dataset_names.get(
                    rel.target_dataset_id, str(rel.target_dataset_id)
                )

                candidate = RelationshipCandidate(
                    source_dataset_id=rel.source_dataset_id,
                    source_dataset_name=source_name,
                    source_column=rel.source_column,
                    target_dataset_id=rel.target_dataset_id,
                    target_dataset_name=target_name,
                    target_column=rel.target_column,
                    relationship_type=rel.relationship_type,
                    cardinality=rel.cardinality or Cardinality.ONE_TO_MANY,
                    confidence_score=rel.confidence_score,
                    reasoning="Veritabanından yüklendi",
                )
                candidates.append(candidate)

            logger.info(
                "%d ilişki veritabanından yüklendi.",
                len(candidates),
            )
            return candidates

        except Exception as e:
            logger.error("İlişkiler DB'den yüklenemedi: %s", str(e))
            raise

    # ── JSON Export / Import ──────────────────────────────────────────

    def export_relationships(
        self,
        candidates: list[RelationshipCandidate],
        output_path: str,
        include_graph: bool = True,
    ) -> dict[str, Any]:
        """
        İlişkileri JSON dosyasına export eder.

        Args:
            candidates: İlişki adayları
            output_path: Çıktı dosya yolu
            include_graph: İlişki grafiğini dahil et

        Returns:
            Export edilen veri dict'i
        """
        from datetime import datetime

        export_data: dict[str, Any] = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "dataset_count": len(self._datasets),
            "datasets": {
                str(ds_id): {
                    "name": name,
                    "column_count": len(self._datasets.get(ds_id, [])),
                }
                for ds_id, name in self._dataset_names.items()
            },
            "relationships": [c.to_dict() for c in candidates],
        }

        if include_graph:
            graph = self.build_relationship_graph(candidates)
            export_data["graph"] = graph.to_dict()

        # Dosyaya yaz
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        logger.info("İlişkiler export edildi: %s", output_path)
        return export_data

    def import_relationships(
        self, input_path: str
    ) -> list[RelationshipCandidate]:
        """
        JSON dosyasından ilişkileri import eder.

        Args:
            input_path: Girdi dosya yolu

        Returns:
            RelationshipCandidate listesi
        """
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        candidates: list[RelationshipCandidate] = []
        for rel_data in data.get("relationships", []):
            candidate = RelationshipCandidate(
                source_dataset_id=rel_data.get("source_dataset_id", 0),
                source_dataset_name=rel_data.get("source_dataset_name", ""),
                source_column=rel_data.get("source_column", ""),
                target_dataset_id=rel_data.get("target_dataset_id", 0),
                target_dataset_name=rel_data.get("target_dataset_name", ""),
                target_column=rel_data.get("target_column", ""),
                relationship_type=RelationshipType(
                    rel_data.get("relationship_type", "inferred")
                ),
                cardinality=Cardinality(
                    rel_data.get("cardinality", "1:N")
                ),
                confidence_score=rel_data.get("confidence_score", 0.0),
                name_match_score=rel_data.get("name_match_score", 0.0),
                semantic_match_score=rel_data.get("semantic_match_score", 0.0),
                value_overlap_score=rel_data.get("value_overlap_score", 0.0),
                referential_integrity_score=rel_data.get(
                    "referential_integrity_score", 0.0
                ),
                reasoning=rel_data.get("reasoning", "JSON'dan import edildi"),
                is_banking_domain=rel_data.get("is_banking_domain", False),
            )
            candidates.append(candidate)

        logger.info(
            "%d ilişki import edildi: %s",
            len(candidates), input_path,
        )
        return candidates

    # ── Çoklu Dataset İlişki Tespiti ──────────────────────────────────

    def infer_cross_dataset_relationships(
        self,
        dataset_groups: dict[str, list[int]],
    ) -> dict[str, list[RelationshipCandidate]]:
        """
        Cross-dataset ilişki tespiti — birden fazla veri kaynağı arasında.

        Farklı veri grupları (ör. farklı bankalar, farklı şubeler) arasındaki
        ilişkileri tespit eder.

        Args:
            dataset_groups: Grup adı → dataset ID'leri eşleştirmesi
                Örnek: {"banka_a": [1, 2, 3], "banka_b": [4, 5, 6]}

        Returns:
            Grup çifti → ilişki adayları eşleştirmesi
        """
        results: dict[str, list[RelationshipCandidate]] = {}
        group_names = list(dataset_groups.keys())

        for i, group_a in enumerate(group_names):
            for group_b in group_names[i + 1:]:
                key = f"{group_a}↔{group_b}"
                pair_candidates: list[RelationshipCandidate] = []

                for ds_a_id in dataset_groups[group_a]:
                    for ds_b_id in dataset_groups[group_b]:
                        candidates = self._infer_pair_relationships(ds_a_id, ds_b_id)
                        pair_candidates.extend(candidates)

                # Filtrele ve sırala
                pair_candidates.sort(key=lambda c: c.confidence_score, reverse=True)
                pair_candidates = self._filter_duplicate_relationships(pair_candidates)
                results[key] = pair_candidates

                logger.info(
                    "Cross-dataset ilişki: %s — %d ilişki tespit edildi",
                    key, len(pair_candidates),
                )

        return results

    # ── Rapor Üretimi ─────────────────────────────────────────────────

    def generate_report(
        self, candidates: list[RelationshipCandidate]
    ) -> InferenceReport:
        """
        İlişki çıkarım raporu üretir.

        Args:
            candidates: İlişki adayları

        Returns:
            InferenceReport nesnesi
        """
        report = InferenceReport(
            dataset_count=len(self._datasets),
            relationship_count=len(candidates),
        )

        if candidates:
            report.avg_confidence = sum(
                c.confidence_score for c in candidates
            ) / len(candidates)

            report.banking_domain_count = sum(
                1 for c in candidates if c.is_banking_domain
            )

            # Tip dağılımı
            for c in candidates:
                t = c.relationship_type.value
                report.type_distribution[t] = report.type_distribution.get(t, 0) + 1

            # Kardinalite dağılımı
            for c in candidates:
                card = c.cardinality.value
                report.cardinality_distribution[card] = (
                    report.cardinality_distribution.get(card, 0) + 1
                )

        # İlişki grafiği
        report.graph = self.build_relationship_graph(candidates)

        return report

    # ── Yardımcı Public Metodlar ──────────────────────────────────────

    def get_generation_order(
        self, candidates: list[RelationshipCandidate]
    ) -> list[dict[str, Any]]:
        """
        Veri üretim sırasını döndürür (topological sort).

        Parent tablolar önce, child tablolar sonra üretilmelidir.

        Args:
            candidates: İlişki adayları

        Returns:
            Sıralı dataset bilgileri listesi
        """
        graph = self.build_relationship_graph(candidates)
        result: list[dict[str, Any]] = []

        for i, node_id in enumerate(graph.generation_order):
            # Bu node'a bağımlı olan node'lar (parent'ları)
            depends_on = [
                c.source_dataset_id
                for c in candidates
                if c.target_dataset_id == node_id
            ]

            result.append({
                "order": i + 1,
                "dataset_id": node_id,
                "dataset_name": graph.node_names.get(node_id, str(node_id)),
                "depends_on": depends_on,
                "depends_on_names": [
                    graph.node_names.get(d, str(d)) for d in depends_on
                ],
            })

        return result

    def get_dataset_dependencies(
        self, dataset_id: int, candidates: list[RelationshipCandidate]
    ) -> dict[str, list[RelationshipCandidate]]:
        """
        Belirli bir dataset'in bağımlılıklarını döndürür.

        Args:
            dataset_id: Dataset ID
            candidates: İlişki adayları

        Returns:
            "parents" ve "children" anahtarlı dict
        """
        parents: list[RelationshipCandidate] = []
        children: list[RelationshipCandidate] = []

        for c in candidates:
            if c.target_dataset_id == dataset_id:
                parents.append(c)  # Bu dataset child, kaynak parent
            if c.source_dataset_id == dataset_id:
                children.append(c)  # Bu dataset parent, hedef child

        return {"parents": parents, "children": children}
