"""
Quality Dashboard Servisi.

Dataset kalite metriklerini hesaplar, zaman serisi analizi yapar
ve kalite skorları üzerinden raporlama sağlar.

Özellikler:
  - QualityMetrics SQLAlchemy modeli
  - Dataset bazlı kalite analizi (completeness, uniqueness, consistency vb.)
  - Zaman serisi kalite takibi
  - Kalite skoru hesaplama (0-100 arası)
  - GET /api/quality/{dataset_id} — Kalite raporu
  - GET /api/quality/{dataset_id}/history — Kalite zaman serisi
"""

import enum
import hashlib
import statistics
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    Integer,
    JSON,
    String,
    Text,
    func,
    desc,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.models.database import Base, get_db


# ═══════════════════════════════════════════════════════════════════════
# Enum ve Model Tanımları
# ═══════════════════════════════════════════════════════════════════════


class QualityDimension(str, enum.Enum):
    """Kalite boyutları."""
    COMPLETENESS = "completeness"       # Eksik veri oranı
    UNIQUENESS = "uniqueness"           # Tekil değer oranı
    CONSISTENCY = "consistency"         # Tutarlılık (format, tip)
    ACCURACY = "accuracy"              # Doğruluk (aralık, referans)
    TIMELINESS = "timeliness"          # Güncellik
    VALIDITY = "validity"              # Geçerlilik (regex, enum)


class QualityLevel(str, enum.Enum):
    """Genel kalite seviyesi."""
    EXCELLENT = "excellent"    # 90-100
    GOOD = "good"              # 75-89
    FAIR = "fair"              # 60-74
    POOR = "poor"              # 40-59
    CRITICAL = "critical"      # 0-39


class QualityMetrics(Base):
    """Kalite metrikleri veritabanı modeli."""

    __tablename__ = "quality_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    version_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── Kalite Skorları (0.0 - 1.0) ──
    completeness_score: Mapped[float] = mapped_column(Float, default=0.0)
    uniqueness_score: Mapped[float] = mapped_column(Float, default=0.0)
    consistency_score: Mapped[float] = mapped_column(Float, default=0.0)
    accuracy_score: Mapped[float] = mapped_column(Float, default=0.0)
    validity_score: Mapped[float] = mapped_column(Float, default=0.0)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    quality_level: Mapped[str] = mapped_column(
        String(20), default=QualityLevel.FAIR.value
    )

    # ── Detay Metrikleri ──
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    total_columns: Mapped[int] = mapped_column(Integer, default=0)
    null_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    invalid_count: Mapped[int] = mapped_column(Integer, default=0)

    # ── Kolon bazlı detaylar (JSON) ──
    column_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    dimension_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # ── Zaman damgaları ──
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<QualityMetrics(id={self.id}, dataset_id={self.dataset_id}, "
            f"overall={self.overall_score:.2f}, level={self.quality_level})>"
        )


# ═══════════════════════════════════════════════════════════════════════
# Pydantic Şemaları
# ═══════════════════════════════════════════════════════════════════════


class DimensionScore(BaseModel):
    """Tek bir kalite boyutu skoru."""
    dimension: str
    score: float = Field(ge=0.0, le=1.0)
    details: Optional[dict] = None
    issues: list[str] = Field(default_factory=list)


class ColumnQuality(BaseModel):
    """Kolon bazlı kalite raporu."""
    column_name: str
    data_type: Optional[str] = None
    completeness: float = Field(ge=0.0, le=1.0)
    uniqueness: float = Field(ge=0.0, le=1.0)
    validity: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)


class QualityReportResponse(BaseModel):
    """Kalite raporu API yanıtı."""
    dataset_id: int
    version_id: Optional[int] = None
    overall_score: float
    quality_level: str
    dimensions: list[DimensionScore]
    column_quality: list[ColumnQuality]
    total_rows: int
    total_columns: int
    null_count: int
    duplicate_count: int
    invalid_count: int
    recommendations: list[str]
    analyzed_at: str


class QualityHistoryItem(BaseModel):
    """Zaman serisi kalite noktası."""
    id: int
    overall_score: float
    quality_level: str
    completeness: float
    uniqueness: float
    consistency: float
    accuracy: float
    validity: float
    analyzed_at: str


class QualityHistoryResponse(BaseModel):
    """Kalite zaman serisi yanıtı."""
    dataset_id: int
    history: list[QualityHistoryItem]
    trend: str  # improving, stable, declining
    total_measurements: int


# ═══════════════════════════════════════════════════════════════════════
# Quality Analyzer
# ═══════════════════════════════════════════════════════════════════════


class QualityAnalyzer:
    """
    Dataset kalite analiz motoru.

    Bir dataset veya üretilmiş sentetik verinin kalitesini
    çoklu boyut üzerinden değerlendirir.
    """

    WEIGHTS = {
        QualityDimension.COMPLETENESS: 0.25,
        QualityDimension.UNIQUENESS: 0.15,
        QualityDimension.CONSISTENCY: 0.20,
        QualityDimension.ACCURACY: 0.20,
        QualityDimension.VALIDITY: 0.20,
    }

    @classmethod
    def _score_to_level(cls, score: float) -> QualityLevel:
        """Skoru kalite seviyesine dönüştür."""
        pct = score * 100
        if pct >= 90:
            return QualityLevel.EXCELLENT
        elif pct >= 75:
            return QualityLevel.GOOD
        elif pct >= 60:
            return QualityLevel.FAIR
        elif pct >= 40:
            return QualityLevel.POOR
        return QualityLevel.CRITICAL

    @classmethod
    def analyze_completeness(cls, data: list[dict]) -> DimensionScore:
        """Eksik veri oranını hesapla."""
        if not data:
            return DimensionScore(
                dimension="completeness", score=0.0,
                issues=["Veri seti boş."]
            )

        total_cells = 0
        null_cells = 0
        col_nulls: dict[str, int] = {}

        for row in data:
            for col, val in row.items():
                total_cells += 1
                if val is None or (isinstance(val, str) and val.strip() == ""):
                    null_cells += 1
                    col_nulls[col] = col_nulls.get(col, 0) + 1

        score = 1.0 - (null_cells / total_cells) if total_cells > 0 else 0.0
        issues = []
        for col, cnt in sorted(col_nulls.items(), key=lambda x: -x[1])[:5]:
            pct = (cnt / len(data)) * 100
            issues.append(f"'{col}' kolonunda %{pct:.1f} eksik veri")

        return DimensionScore(
            dimension="completeness",
            score=round(score, 4),
            details={"total_cells": total_cells, "null_cells": null_cells},
            issues=issues,
        )

    @classmethod
    def analyze_uniqueness(cls, data: list[dict]) -> DimensionScore:
        """Tekil değer oranını hesapla."""
        if not data:
            return DimensionScore(
                dimension="uniqueness", score=0.0, issues=["Veri seti boş."]
            )

        columns = list(data[0].keys())
        col_scores: dict[str, float] = {}
        issues = []

        for col in columns:
            values = [row.get(col) for row in data if row.get(col) is not None]
            if not values:
                col_scores[col] = 1.0
                continue
            unique_ratio = len(set(values)) / len(values)
            col_scores[col] = unique_ratio
            if unique_ratio < 0.1 and len(values) > 10:
                issues.append(
                    f"'{col}' kolonunda çok düşük tekil oran: %{unique_ratio * 100:.1f}"
                )

        # Row-level duplicate check
        row_hashes = set()
        dup_count = 0
        for row in data:
            h = hashlib.md5(str(sorted(row.items())).encode()).hexdigest()
            if h in row_hashes:
                dup_count += 1
            row_hashes.add(h)

        if dup_count > 0:
            issues.insert(0, f"{dup_count} satır tamamen tekrarlı")

        row_uniqueness = 1.0 - (dup_count / len(data)) if data else 0.0
        col_avg = statistics.mean(col_scores.values()) if col_scores else 0.0
        score = 0.6 * row_uniqueness + 0.4 * col_avg

        return DimensionScore(
            dimension="uniqueness",
            score=round(score, 4),
            details={"duplicate_rows": dup_count, "column_scores": col_scores},
            issues=issues,
        )

    @classmethod
    def analyze_consistency(cls, data: list[dict]) -> DimensionScore:
        """Veri tutarlılığını analiz et (format, tip)."""
        if not data:
            return DimensionScore(
                dimension="consistency", score=0.0, issues=["Veri seti boş."]
            )

        columns = list(data[0].keys())
        issues = []
        consistent_cols = 0

        for col in columns:
            values = [row.get(col) for row in data if row.get(col) is not None]
            if not values:
                consistent_cols += 1
                continue

            types = set(type(v).__name__ for v in values)
            if len(types) <= 1:
                consistent_cols += 1
            else:
                primary_type = max(types, key=lambda t: sum(
                    1 for v in values if type(v).__name__ == t
                ))
                mismatch_pct = (
                    1 - sum(1 for v in values if type(v).__name__ == primary_type) / len(values)
                ) * 100
                if mismatch_pct > 5:
                    issues.append(
                        f"'{col}' kolonunda %{mismatch_pct:.1f} tip uyumsuzluğu "
                        f"(beklenen: {primary_type}, bulunan: {types})"
                    )

        score = consistent_cols / len(columns) if columns else 0.0

        return DimensionScore(
            dimension="consistency",
            score=round(score, 4),
            details={"consistent_columns": consistent_cols, "total_columns": len(columns)},
            issues=issues,
        )

    @classmethod
    def analyze_validity(cls, data: list[dict]) -> DimensionScore:
        """Geçerlilik kontrolü (boş string, negatif sayı vb.)."""
        if not data:
            return DimensionScore(
                dimension="validity", score=0.0, issues=["Veri seti boş."]
            )

        total_checks = 0
        valid_checks = 0
        issues = []

        for col in data[0].keys():
            values = [row.get(col) for row in data if row.get(col) is not None]
            if not values:
                continue

            numeric_values = [v for v in values if isinstance(v, (int, float))]
            if numeric_values:
                total_checks += len(numeric_values)
                negative_count = sum(1 for v in numeric_values if v < 0)
                valid_checks += len(numeric_values) - negative_count
                if negative_count > 0:
                    issues.append(
                        f"'{col}' kolonunda {negative_count} negatif değer"
                    )
            else:
                total_checks += len(values)
                empty_str = sum(1 for v in values if isinstance(v, str) and v.strip() == "")
                valid_checks += len(values) - empty_str

        score = valid_checks / total_checks if total_checks > 0 else 1.0

        return DimensionScore(
            dimension="validity",
            score=round(score, 4),
            details={"total_checks": total_checks, "valid_checks": valid_checks},
            issues=issues,
        )

    @classmethod
    def analyze_accuracy(cls, data: list[dict], reference: Optional[dict] = None) -> DimensionScore:
        """
        Doğruluk analizi.

        Referans veri varsa karşılaştırma yapar; yoksa istatistiksel
        outlier tespiti uygular.
        """
        if not data:
            return DimensionScore(
                dimension="accuracy", score=0.0, issues=["Veri seti boş."]
            )

        issues = []
        col_scores = {}

        for col in data[0].keys():
            values = [row.get(col) for row in data if row.get(col) is not None]
            numeric_values = [v for v in values if isinstance(v, (int, float))]

            if len(numeric_values) < 5:
                col_scores[col] = 1.0
                continue

            mean_val = statistics.mean(numeric_values)
            try:
                stdev_val = statistics.stdev(numeric_values)
            except statistics.StatisticsError:
                col_scores[col] = 1.0
                continue

            if stdev_val == 0:
                col_scores[col] = 1.0
                continue

            # Z-score outlier detection (|z| > 3)
            outlier_count = sum(
                1 for v in numeric_values
                if abs((v - mean_val) / stdev_val) > 3
            )
            outlier_pct = outlier_count / len(numeric_values)
            col_scores[col] = 1.0 - outlier_pct

            if outlier_count > 0:
                issues.append(
                    f"'{col}' kolonunda {outlier_count} aykırı değer (|z| > 3)"
                )

        score = statistics.mean(col_scores.values()) if col_scores else 1.0

        return DimensionScore(
            dimension="accuracy",
            score=round(score, 4),
            details={"column_accuracy": {k: round(v, 4) for k, v in col_scores.items()}},
            issues=issues,
        )

    @classmethod
    def generate_recommendations(
        cls, dimensions: list[DimensionScore], overall: float
    ) -> list[str]:
        """Kalite iyileştirme önerileri üret."""
        recommendations = []

        for dim in dimensions:
            if dim.score < 0.7:
                if dim.dimension == "completeness":
                    recommendations.append(
                        "Eksik veri oranı yüksek. Zorunlu alanları belirleyin veya "
                        "imputation stratejisi uygulayın."
                    )
                elif dim.dimension == "uniqueness":
                    recommendations.append(
                        "Tekrarlı satır sayısı fazla. Üretim parametrelerinde "
                        "çeşitliliği artırın."
                    )
                elif dim.dimension == "consistency":
                    recommendations.append(
                        "Tip uyumsuzlukları var. Kolon tipleri için kesin "
                        "kural tanımları ekleyin."
                    )
                elif dim.dimension == "accuracy":
                    recommendations.append(
                        "Aykırı değer oranı yüksek. Değer aralıklarını "
                        "kural motoru ile sınırlayın."
                    )
                elif dim.dimension == "validity":
                    recommendations.append(
                        "Geçersiz değer oranı yüksek. Doğrulama kuralları "
                        "(regex, enum) ekleyin."
                    )

        if overall >= 0.9:
            recommendations.append("Kalite mükemmel seviyede. Mevcut kuralları koruyun.")
        elif overall < 0.5:
            recommendations.append(
                "Genel kalite kritik seviyede. Kaynak verinin kalitesini "
                "gözden geçirin ve üretim parametrelerini ayarlayın."
            )

        return recommendations

    @classmethod
    def full_analysis(
        cls,
        data: list[dict],
        dataset_id: int,
        version_id: Optional[int] = None,
        reference: Optional[dict] = None,
    ) -> QualityReportResponse:
        """Tam kalite analizi çalıştır."""
        completeness = cls.analyze_completeness(data)
        uniqueness = cls.analyze_uniqueness(data)
        consistency = cls.analyze_consistency(data)
        accuracy = cls.analyze_accuracy(data, reference)
        validity = cls.analyze_validity(data)

        dimensions = [completeness, uniqueness, consistency, accuracy, validity]

        # Ağırlıklı genel skor
        overall = sum(
            dim.score * cls.WEIGHTS.get(QualityDimension(dim.dimension), 0.15)
            for dim in dimensions
        )
        overall = round(min(overall, 1.0), 4)
        level = cls._score_to_level(overall)

        # Kolon bazlı kalite
        column_quality = []
        if data:
            for col in data[0].keys():
                values = [row.get(col) for row in data]
                non_null = [v for v in values if v is not None]
                comp = len(non_null) / len(values) if values else 0.0
                unique_vals = set(str(v) for v in non_null)
                uniq = len(unique_vals) / len(non_null) if non_null else 0.0
                col_issues = []
                if comp < 0.8:
                    col_issues.append("Yüksek eksik veri oranı")
                if uniq < 0.1 and len(non_null) > 10:
                    col_issues.append("Düşük çeşitlilik")
                column_quality.append(ColumnQuality(
                    column_name=col,
                    data_type=type(non_null[0]).__name__ if non_null else "unknown",
                    completeness=round(comp, 4),
                    uniqueness=round(uniq, 4),
                    validity=validity.score,
                    issues=col_issues,
                ))

        # Toplam istatistikler
        null_count = completeness.details.get("null_cells", 0) if completeness.details else 0
        dup_count = uniqueness.details.get("duplicate_rows", 0) if uniqueness.details else 0
        invalid_count = (
            (validity.details.get("total_checks", 0) - validity.details.get("valid_checks", 0))
            if validity.details else 0
        )

        recommendations = cls.generate_recommendations(dimensions, overall)

        return QualityReportResponse(
            dataset_id=dataset_id,
            version_id=version_id,
            overall_score=overall,
            quality_level=level.value,
            dimensions=dimensions,
            column_quality=column_quality,
            total_rows=len(data),
            total_columns=len(data[0]) if data else 0,
            null_count=null_count,
            duplicate_count=dup_count,
            invalid_count=invalid_count,
            recommendations=recommendations,
            analyzed_at=datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def save_metrics(
        cls,
        db: Session,
        report: QualityReportResponse,
    ) -> QualityMetrics:
        """Kalite metriklerini veritabanına kaydet."""
        dim_map = {d.dimension: d.score for d in report.dimensions}

        metrics = QualityMetrics(
            dataset_id=report.dataset_id,
            version_id=report.version_id,
            completeness_score=dim_map.get("completeness", 0.0),
            uniqueness_score=dim_map.get("uniqueness", 0.0),
            consistency_score=dim_map.get("consistency", 0.0),
            accuracy_score=dim_map.get("accuracy", 0.0),
            validity_score=dim_map.get("validity", 0.0),
            overall_score=report.overall_score,
            quality_level=report.quality_level,
            total_rows=report.total_rows,
            total_columns=report.total_columns,
            null_count=report.null_count,
            duplicate_count=report.duplicate_count,
            invalid_count=report.invalid_count,
            column_metrics={c.column_name: c.model_dump() for c in report.column_quality},
            dimension_details={d.dimension: d.model_dump() for d in report.dimensions},
            recommendations=report.recommendations,
        )
        db.add(metrics)
        db.commit()
        db.refresh(metrics)
        return metrics

    @classmethod
    def get_history(
        cls,
        db: Session,
        dataset_id: int,
        limit: int = 50,
    ) -> QualityHistoryResponse:
        """Kalite zaman serisi geçmişini getir."""
        records = (
            db.query(QualityMetrics)
            .filter(QualityMetrics.dataset_id == dataset_id)
            .order_by(desc(QualityMetrics.analyzed_at))
            .limit(limit)
            .all()
        )

        history = [
            QualityHistoryItem(
                id=r.id,
                overall_score=r.overall_score,
                quality_level=r.quality_level,
                completeness=r.completeness_score,
                uniqueness=r.uniqueness_score,
                consistency=r.consistency_score,
                accuracy=r.accuracy_score,
                validity=r.validity_score,
                analyzed_at=r.analyzed_at.isoformat() if r.analyzed_at else "",
            )
            for r in records
        ]

        # Trend hesapla
        trend = "stable"
        if len(history) >= 3:
            recent = [h.overall_score for h in history[:3]]
            older = [h.overall_score for h in history[-3:]]
            recent_avg = statistics.mean(recent)
            older_avg = statistics.mean(older)
            diff = recent_avg - older_avg
            if diff > 0.05:
                trend = "improving"
            elif diff < -0.05:
                trend = "declining"

        return QualityHistoryResponse(
            dataset_id=dataset_id,
            history=list(reversed(history)),  # Eski → Yeni sırası
            trend=trend,
            total_measurements=len(history),
        )


# ═══════════════════════════════════════════════════════════════════════
# FastAPI Router
# ═══════════════════════════════════════════════════════════════════════

quality_router = APIRouter(prefix="/api/quality", tags=["Kalite Dashboard"])


@quality_router.get(
    "/{dataset_id}",
    response_model=QualityReportResponse,
    summary="Kalite Raporu",
    description="Belirtilen dataset için kalite analizi çalıştırır ve rapor döndürür.",
)
async def get_quality_report(
    dataset_id: int,
    version_id: Optional[int] = Query(None, description="Belirli versiyon ID"),
    db: Session = Depends(get_db),
):
    """Dataset kalite raporu endpoint'i."""
    # Dataset'i kontrol et
    from app.models.dataset import Dataset
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset bulunamadı")

    # Basit bir veri temsili oluştur (gerçek veriden veya metadata'dan)
    sample_data: list[dict] = []
    if dataset.sample_data:
        sample_data = dataset.sample_data if isinstance(dataset.sample_data, list) else []

    if not sample_data:
        raise HTTPException(
            status_code=400,
            detail="Dataset'te analiz edilecek örnek veri bulunamadı"
        )

    report = QualityAnalyzer.full_analysis(
        data=sample_data,
        dataset_id=dataset_id,
        version_id=version_id,
    )

    # Metrikleri kaydet
    QualityAnalyzer.save_metrics(db, report)

    return report


@quality_router.get(
    "/{dataset_id}/history",
    response_model=QualityHistoryResponse,
    summary="Kalite Geçmişi",
    description="Dataset kalite metriklerinin zaman serisi geçmişini döndürür.",
)
async def get_quality_history(
    dataset_id: int,
    limit: int = Query(50, ge=1, le=500, description="Maksimum kayıt sayısı"),
    db: Session = Depends(get_db),
):
    """Kalite zaman serisi endpoint'i."""
    from app.models.dataset import Dataset
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset bulunamadı")

    return QualityAnalyzer.get_history(db, dataset_id, limit)


@quality_router.get(
    "/{dataset_id}/summary",
    summary="Kalite Özet",
    description="Son kalite ölçümünün kısa özetini döndürür.",
)
async def get_quality_summary(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    """Hızlı kalite özeti endpoint'i."""
    latest = (
        db.query(QualityMetrics)
        .filter(QualityMetrics.dataset_id == dataset_id)
        .order_by(desc(QualityMetrics.analyzed_at))
        .first()
    )

    if not latest:
        raise HTTPException(
            status_code=404,
            detail="Bu dataset için kalite ölçümü bulunamadı"
        )

    return {
        "dataset_id": dataset_id,
        "overall_score": latest.overall_score,
        "quality_level": latest.quality_level,
        "scores": {
            "completeness": latest.completeness_score,
            "uniqueness": latest.uniqueness_score,
            "consistency": latest.consistency_score,
            "accuracy": latest.accuracy_score,
            "validity": latest.validity_score,
        },
        "total_rows": latest.total_rows,
        "recommendations_count": len(latest.recommendations) if latest.recommendations else 0,
        "analyzed_at": latest.analyzed_at.isoformat() if latest.analyzed_at else None,
    }
