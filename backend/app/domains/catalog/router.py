import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.utils import client_ip
from app.deps import get_current_user
from app.domains.audit.service import log_audit
from app.domains.catalog.schemas import (
    DatasetCreate,
    DatasetOut,
    DatasetVersionCreate,
    DatasetVersionOut,
    SchemaSnapshotOut,
)
from app.infra.database import get_db
from app.infra.models import Dataset, DatasetVersion, SchemaSnapshot, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["catalog"])


def _is_admin_user(user: User) -> bool:
    for role in (user.roles or []):
        for rp in (role.permissions or []):
            if getattr(rp, "permission", "") == "admin.*":
                return True
    return False


@router.get("", response_model=list[DatasetOut])
def list_datasets(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[Dataset]:
    """Veri setlerini listeler — sadece kendi veri setleri (admin hepsini görür)."""
    try:
        q = select(Dataset).order_by(Dataset.created_at.desc()).limit(limit).offset(offset)
        if not _is_admin_user(user):
            q = q.where(Dataset.created_by == user.id)
        return list(db.scalars(q).all())
    except Exception as e:
        logger.error("list_datasets failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
def create_dataset(
    body: DatasetCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> Dataset:
    """Yeni veri seti olusturur."""
    try:
        ds = Dataset(name=body.name, description=body.description, created_by=user.id)
        db.add(ds)
        db.flush()
        log_audit(
            db,
            actor_user_id=user.id,
            action="dataset.create",
            resource_type="dataset",
            resource_id=ds.id,
            payload={"name": body.name},
            ip=client_ip(request),
        )
        db.commit()
        db.refresh(ds)
        return ds
    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_dataset failed: %s", e, exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def _get_dataset_or_403(dataset_id: str, db: Session, user: User) -> Dataset:
    ds = db.get(Dataset, dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Veri seti bulunamadı")
    if not _is_admin_user(user) and ds.created_by != user.id:
        raise HTTPException(status_code=403, detail="Bu veri setine erişim yetkiniz yok")
    return ds


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(
    dataset_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> Dataset:
    """Belirtilen veri seti detayini getirir."""
    try:
        return _get_dataset_or_403(dataset_id, db, user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_dataset(%s) failed: %s", dataset_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{dataset_id}/versions",
    response_model=DatasetVersionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_dataset_version(
    dataset_id: str,
    body: DatasetVersionCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> DatasetVersion:
    """Veri seti icin yeni bir surum olusturur."""
    try:
        ds = _get_dataset_or_403(dataset_id, db, user)
        max_v = db.scalar(
            select(func.max(DatasetVersion.version)).where(DatasetVersion.dataset_id == dataset_id)
        )
        next_v = (max_v or 0) + 1
        ver = DatasetVersion(dataset_id=dataset_id, version=next_v, status="draft")
        db.add(ver)
        db.flush()
        snap = SchemaSnapshot(
            dataset_version_id=ver.id,
            snapshot=body.snapshot or {},
            profile=body.profile,
            pii_flags=body.pii_flags,
        )
        db.add(snap)
        log_audit(
            db,
            actor_user_id=user.id,
            action="dataset_version.create",
            resource_type="dataset_version",
            resource_id=ver.id,
            payload={"dataset_id": dataset_id, "version": next_v},
            ip=client_ip(request),
        )
        db.commit()
        db.refresh(ver)
        return ver
    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_dataset_version(%s) failed: %s", dataset_id, e, exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}/versions", response_model=list[DatasetVersionOut])
def list_versions(
    dataset_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(100, ge=1, le=500),
) -> list[DatasetVersion]:
    """Veri seti surumlerini listeler."""
    try:
        _get_dataset_or_403(dataset_id, db, user)
        return list(
            db.scalars(
                select(DatasetVersion)
                .where(DatasetVersion.dataset_id == dataset_id)
                .order_by(DatasetVersion.version.desc())
                .limit(limit)
            ).all()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_versions(%s) failed: %s", dataset_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{dataset_id}/versions/{version_id}/schema",
    response_model=SchemaSnapshotOut,
)
def get_schema_for_version(
    dataset_id: str,
    version_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> SchemaSnapshot:
    """Belirtilen surume ait sema bilgisini getirir."""
    try:
        _get_dataset_or_403(dataset_id, db, user)
        ver = db.get(DatasetVersion, version_id)
        if ver is None or ver.dataset_id != dataset_id:
            raise HTTPException(status_code=404, detail="Sürüm bulunamadı")
        snap = db.scalar(
            select(SchemaSnapshot).where(SchemaSnapshot.dataset_version_id == version_id)
        )
        if snap is None:
            raise HTTPException(status_code=404, detail="Şema bulunamadı")
        return snap
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_schema_for_version(%s, %s) failed: %s", dataset_id, version_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
