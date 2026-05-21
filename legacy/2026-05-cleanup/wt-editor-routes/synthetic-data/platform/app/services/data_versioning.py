"""
Data Versioning Servisi.

Her sentetik veri üretim işleminde otomatik versiyon oluşturur,
versiyonlar arası karşılaştırma ve geri yükleme imkanı sağlar.

Özellikler:
  - DataVersion SQLAlchemy modeli
  - Her generate işleminde otomatik versiyon oluşturma
  - Versiyon karşılaştırma (diff)
  - Versiyon geri yükleme
  - GET /api/versions/{dataset_id} — Versiyon geçmişi
"""

import enum
import hashlib
import json
from datetime import datetime, timezone
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


class VersionStatus(str, enum.Enum):
    """Versiyon durumu."""
    ACTIVE = "active"       # Geçerli versiyon
    ARCHIVED = "archived"   # Arşivlenmiş
    RESTORED = "restored"   # Geri yüklenmiş
    DELETED = "deleted"     # Silinmiş (soft delete)


class DataVersion(Base):
    """
    Veri seti versiyon modeli.

    Her sentetik veri üretim işlemi için bir versiyon kaydı oluşturulur.
    """

    __tablename__ = "data_versions"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    dataset_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True,
        comment="Ait olduğu veri seti",
    )
    version_number: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Versiyon numarası (1, 2, 3, ...)",
    )
    job_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="İlişkili üretim görevi ID'si",
    )
    row_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Üretilen satır sayısı",
    )
    column_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="Kolon sayısı",
    )
    checksum: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="Veri bütünlüğü kontrolü (SHA-256)",
    )
    file_path: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True,
        comment="Versiyon dosya yolu",
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="Dosya boyutu (byte)",
    )
    status: Mapped[VersionStatus] = mapped_column(
        Enum(VersionStatus),
        nullable=False,
        default=VersionStatus.ACTIVE,
        comment="Versiyon durumu",
    )
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True,
        comment="Ek meta veriler (parametreler, kurallar, senaryo bilgisi)",
    )
    column_schema: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True,
        comment="Kolon şeması (isim, tip, istatistikler)",
    )
    statistics: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True,
        comment="Versiyon istatistikleri (ortalama, std, dağılım)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Versiyon açıklaması",
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
        comment="Oluşturan kullanıcı",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Oluşturulma zamanı",
    )

    def __repr__(self) -> str:
        return (
            f"<DataVersion(id={self.id}, dataset={self.dataset_id}, "
            f"v{self.version_number}, rows={self.row_count})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """JSON serializable dict döndür."""
        return {
            "id": self.id,
            "dataset_id": self.dataset_id,
            "version_number": self.version_number,
            "job_id": self.job_id,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "checksum": self.checksum,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "status": self.status.value if self.status else None,
            "metadata": self.metadata_json,
            "column_schema": self.column_schema,
            "statistics": self.statistics,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ═══════════════════════════════════════════════════════════════════════
# Versioning Service
# ═══════════════════════════════════════════════════════════════════════


class DataVersioningService:
    """
    Veri versiyonlama servisi.

    Sentetik veri üretimlerinin versiyonlarını yönetir.
    """

    @staticmethod
    def compute_checksum(data: Any) -> str:
        """
        Veri için SHA-256 checksum hesapla.

        Args:
            data: DataFrame, dict veya string olabilir.

        Returns:
            SHA-256 hash string.
        """
        if hasattr(data, "to_csv"):
            # pandas DataFrame
            content = data.to_csv(index=False).encode("utf-8")
        elif isinstance(data, dict):
            content = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        elif isinstance(data, str):
            content = data.encode("utf-8")
        elif isinstance(data, bytes):
            content = data
        else:
            content = str(data).encode("utf-8")

        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def create_version(
        db: Session,
        dataset_id: int,
        row_count: int,
        checksum: str,
        job_id: Optional[int] = None,
        column_count: Optional[int] = None,
        file_path: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        metadata: Optional[dict] = None,
        column_schema: Optional[dict] = None,
        statistics: Optional[dict] = None,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> DataVersion:
        """
        Yeni versiyon oluştur.

        Versiyon numarasını otomatik olarak artırır.
        """
        # Mevcut en yüksek versiyon numarasını bul
        max_version = (
            db.query(func.max(DataVersion.version_number))
            .filter(DataVersion.dataset_id == dataset_id)
            .scalar()
        )
        next_version = (max_version or 0) + 1

        version = DataVersion(
            dataset_id=dataset_id,
            version_number=next_version,
            job_id=job_id,
            row_count=row_count,
            column_count=column_count,
            checksum=checksum,
            file_path=file_path,
            file_size_bytes=file_size_bytes,
            status=VersionStatus.ACTIVE,
            metadata_json=metadata,
            column_schema=column_schema,
            statistics=statistics,
            description=description or f"v{next_version} — Otomatik versiyon",
            created_by=created_by,
            created_at=datetime.now(timezone.utc),
        )

        db.add(version)
        db.commit()
        db.refresh(version)

        return version

    @staticmethod
    def get_versions(
        db: Session,
        dataset_id: int,
        include_deleted: bool = False,
    ) -> list[DataVersion]:
        """Dataset için tüm versiyonları getir."""
        query = db.query(DataVersion).filter(
            DataVersion.dataset_id == dataset_id
        )

        if not include_deleted:
            query = query.filter(DataVersion.status != VersionStatus.DELETED)

        return query.order_by(desc(DataVersion.version_number)).all()

    @staticmethod
    def get_version(
        db: Session,
        dataset_id: int,
        version_number: int,
    ) -> Optional[DataVersion]:
        """Belirli bir versiyonu getir."""
        return (
            db.query(DataVersion)
            .filter(
                DataVersion.dataset_id == dataset_id,
                DataVersion.version_number == version_number,
            )
            .first()
        )

    @staticmethod
    def get_latest_version(
        db: Session,
        dataset_id: int,
    ) -> Optional[DataVersion]:
        """En son aktif versiyonu getir."""
        return (
            db.query(DataVersion)
            .filter(
                DataVersion.dataset_id == dataset_id,
                DataVersion.status == VersionStatus.ACTIVE,
            )
            .order_by(desc(DataVersion.version_number))
            .first()
        )

    @staticmethod
    def compare_versions(
        db: Session,
        dataset_id: int,
        version_a: int,
        version_b: int,
    ) -> dict[str, Any]:
        """
        İki versiyon arasındaki farkları karşılaştır.

        Returns:
            Karşılaştırma sonucu dict.
        """
        va = (
            db.query(DataVersion)
            .filter(
                DataVersion.dataset_id == dataset_id,
                DataVersion.version_number == version_a,
            )
            .first()
        )
        vb = (
            db.query(DataVersion)
            .filter(
                DataVersion.dataset_id == dataset_id,
                DataVersion.version_number == version_b,
            )
            .first()
        )

        if not va or not vb:
            return {"error": "Bir veya her iki versiyon bulunamadı."}

        diff = {
            "dataset_id": dataset_id,
            "version_a": version_a,
            "version_b": version_b,
            "changes": {},
        }

        # Satır sayısı değişimi
        row_diff = vb.row_count - va.row_count
        diff["changes"]["row_count"] = {
            "before": va.row_count,
            "after": vb.row_count,
            "change": row_diff,
            "change_pct": round(row_diff / va.row_count * 100, 2) if va.row_count else 0,
        }

        # Kolon sayısı değişimi
        if va.column_count and vb.column_count:
            col_diff = vb.column_count - va.column_count
            diff["changes"]["column_count"] = {
                "before": va.column_count,
                "after": vb.column_count,
                "change": col_diff,
            }

        # Checksum değişimi
        diff["changes"]["checksum"] = {
            "before": va.checksum[:12] + "...",
            "after": vb.checksum[:12] + "...",
            "changed": va.checksum != vb.checksum,
        }

        # Kolon şeması karşılaştırması
        if va.column_schema and vb.column_schema:
            cols_a = set(va.column_schema.get("columns", {}).keys())
            cols_b = set(vb.column_schema.get("columns", {}).keys())

            diff["changes"]["columns"] = {
                "added": list(cols_b - cols_a),
                "removed": list(cols_a - cols_b),
                "unchanged": list(cols_a & cols_b),
            }

        # İstatistik karşılaştırması
        if va.statistics and vb.statistics:
            stat_changes = {}
            for key in set(list(va.statistics.keys()) + list(vb.statistics.keys())):
                val_a = va.statistics.get(key)
                val_b = vb.statistics.get(key)
                if val_a != val_b:
                    stat_changes[key] = {
                        "before": val_a,
                        "after": val_b,
                    }
            if stat_changes:
                diff["changes"]["statistics"] = stat_changes

        # Zaman farkı
        if va.created_at and vb.created_at:
            time_diff = (vb.created_at - va.created_at).total_seconds()
            diff["time_between_versions_seconds"] = time_diff

        return diff

    @staticmethod
    def restore_version(
        db: Session,
        dataset_id: int,
        version_number: int,
    ) -> Optional[DataVersion]:
        """
        Belirtilen versiyonu geri yükle.

        Geri yüklenen versiyonun bir kopyasını yeni versiyon olarak oluşturur.
        """
        source = (
            db.query(DataVersion)
            .filter(
                DataVersion.dataset_id == dataset_id,
                DataVersion.version_number == version_number,
            )
            .first()
        )

        if not source:
            return None

        # Yeni versiyon numarası
        max_version = (
            db.query(func.max(DataVersion.version_number))
            .filter(DataVersion.dataset_id == dataset_id)
            .scalar()
        )
        next_version = (max_version or 0) + 1

        # Kaynak versiyonu kopyala
        restored = DataVersion(
            dataset_id=dataset_id,
            version_number=next_version,
            job_id=source.job_id,
            row_count=source.row_count,
            column_count=source.column_count,
            checksum=source.checksum,
            file_path=source.file_path,
            file_size_bytes=source.file_size_bytes,
            status=VersionStatus.RESTORED,
            metadata_json={
                **(source.metadata_json or {}),
                "restored_from": version_number,
                "restored_at": datetime.now(timezone.utc).isoformat(),
            },
            column_schema=source.column_schema,
            statistics=source.statistics,
            description=f"v{next_version} — v{version_number}'den geri yüklendi",
            created_by="system",
            created_at=datetime.now(timezone.utc),
        )

        db.add(restored)
        db.commit()
        db.refresh(restored)

        return restored

    @staticmethod
    def delete_version(
        db: Session,
        dataset_id: int,
        version_number: int,
    ) -> bool:
        """Versiyonu soft-delete yap."""
        version = (
            db.query(DataVersion)
            .filter(
                DataVersion.dataset_id == dataset_id,
                DataVersion.version_number == version_number,
            )
            .first()
        )

        if not version:
            return False

        version.status = VersionStatus.DELETED
        db.commit()
        return True


# ═══════════════════════════════════════════════════════════════════════
# Pydantic Şemaları
# ═══════════════════════════════════════════════════════════════════════


class VersionResponse(BaseModel):
    """Versiyon yanıt şeması."""
    id: int
    dataset_id: int
    version_number: int
    job_id: Optional[int] = None
    row_count: int
    column_count: Optional[int] = None
    checksum: str
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    status: str
    metadata: Optional[dict[str, Any]] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None


class VersionListResponse(BaseModel):
    """Versiyon listesi yanıtı."""
    dataset_id: int
    versions: list[VersionResponse]
    total: int
    latest_version: Optional[int] = None


class VersionDiffResponse(BaseModel):
    """Versiyon karşılaştırma yanıtı."""
    dataset_id: int
    version_a: int
    version_b: int
    changes: dict[str, Any]
    time_between_versions_seconds: Optional[float] = None


# ═══════════════════════════════════════════════════════════════════════
# API Router — /api/v1/versions/*
# ═══════════════════════════════════════════════════════════════════════

version_router = APIRouter(prefix="/api/v1/versions", tags=["Veri Versiyonlama"])


@version_router.get(
    "/{dataset_id}",
    response_model=VersionListResponse,
    summary="Versiyon Geçmişi",
    description="Bir veri seti için tüm versiyonları listeler.",
)
async def list_versions(
    dataset_id: int,
    include_deleted: bool = Query(False, description="Silinen versiyonları da göster"),
    db: Session = Depends(get_db),
) -> VersionListResponse:
    """Dataset versiyon geçmişi."""
    versions = DataVersioningService.get_versions(
        db, dataset_id, include_deleted=include_deleted
    )

    latest = DataVersioningService.get_latest_version(db, dataset_id)

    return VersionListResponse(
        dataset_id=dataset_id,
        versions=[
            VersionResponse(
                id=v.id,
                dataset_id=v.dataset_id,
                version_number=v.version_number,
                job_id=v.job_id,
                row_count=v.row_count,
                column_count=v.column_count,
                checksum=v.checksum,
                file_path=v.file_path,
                file_size_bytes=v.file_size_bytes,
                status=v.status.value if v.status else "unknown",
                metadata=v.metadata_json,
                description=v.description,
                created_by=v.created_by,
                created_at=v.created_at.isoformat() if v.created_at else None,
            )
            for v in versions
        ],
        total=len(versions),
        latest_version=latest.version_number if latest else None,
    )


@version_router.get(
    "/{dataset_id}/compare",
    response_model=VersionDiffResponse,
    summary="Versiyon Karşılaştırma",
    description="İki versiyon arasındaki farkları gösterir.",
)
async def compare_versions(
    dataset_id: int,
    version_a: int = Query(..., description="İlk versiyon numarası"),
    version_b: int = Query(..., description="İkinci versiyon numarası"),
    db: Session = Depends(get_db),
) -> VersionDiffResponse:
    """İki versiyonu karşılaştır."""
    diff = DataVersioningService.compare_versions(
        db, dataset_id, version_a, version_b
    )

    if "error" in diff:
        raise HTTPException(status_code=404, detail=diff["error"])

    return VersionDiffResponse(**diff)


@version_router.post(
    "/{dataset_id}/restore/{version_number}",
    response_model=VersionResponse,
    summary="Versiyon Geri Yükleme",
    description="Belirtilen versiyonu geri yükler (yeni versiyon olarak).",
)
async def restore_version(
    dataset_id: int,
    version_number: int,
    db: Session = Depends(get_db),
) -> VersionResponse:
    """Versiyonu geri yükle."""
    restored = DataVersioningService.restore_version(
        db, dataset_id, version_number
    )

    if not restored:
        raise HTTPException(
            status_code=404,
            detail=f"Versiyon bulunamadı: dataset={dataset_id}, v{version_number}",
        )

    return VersionResponse(
        id=restored.id,
        dataset_id=restored.dataset_id,
        version_number=restored.version_number,
        job_id=restored.job_id,
        row_count=restored.row_count,
        column_count=restored.column_count,
        checksum=restored.checksum,
        file_path=restored.file_path,
        file_size_bytes=restored.file_size_bytes,
        status=restored.status.value if restored.status else "unknown",
        metadata=restored.metadata_json,
        description=restored.description,
        created_by=restored.created_by,
        created_at=restored.created_at.isoformat() if restored.created_at else None,
    )


@version_router.delete(
    "/{dataset_id}/{version_number}",
    summary="Versiyon Sil",
    description="Belirtilen versiyonu soft-delete yapar.",
)
async def delete_version(
    dataset_id: int,
    version_number: int,
    db: Session = Depends(get_db),
) -> dict:
    """Versiyonu sil."""
    success = DataVersioningService.delete_version(
        db, dataset_id, version_number
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Versiyon bulunamadı: dataset={dataset_id}, v{version_number}",
        )

    return {
        "message": f"v{version_number} başarıyla silindi.",
        "dataset_id": dataset_id,
        "version_number": version_number,
    }
