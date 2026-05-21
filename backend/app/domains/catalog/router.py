from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

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

router = APIRouter(prefix="/datasets", tags=["catalog"])


def _client_ip(request: Request) -> Optional[str]:
    if request.client:
        return request.client.host
    return None


@router.get("", response_model=list[DatasetOut])
def list_datasets(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[Dataset]:
    """Veri setlerini listeler."""
    return list(db.scalars(select(Dataset).order_by(Dataset.created_at.desc())).all())


@router.post("", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
def create_dataset(
    body: DatasetCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> Dataset:
    """Yeni veri seti olusturur."""
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
        ip=_client_ip(request),
    )
    db.commit()
    db.refresh(ds)
    return ds


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(
    dataset_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> Dataset:
    """Belirtilen veri seti detayini getirir."""
    ds = db.get(Dataset, dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Veri seti bulunamadı")
    return ds


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
    ds = db.get(Dataset, dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Veri seti bulunamadı")
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
        ip=_client_ip(request),
    )
    db.commit()
    db.refresh(ver)
    return ver


@router.get("/{dataset_id}/versions", response_model=list[DatasetVersionOut])
def list_versions(
    dataset_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[DatasetVersion]:
    """Veri seti surumlerini listeler."""
    if db.get(Dataset, dataset_id) is None:
        raise HTTPException(status_code=404, detail="Veri seti bulunamadı")
    return list(
        db.scalars(
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version.desc())
        ).all()
    )


@router.get(
    "/{dataset_id}/versions/{version_id}/schema",
    response_model=SchemaSnapshotOut,
)
def get_schema_for_version(
    dataset_id: str,
    version_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> SchemaSnapshot:
    """Belirtilen surume ait sema bilgisini getirir."""
    ver = db.get(DatasetVersion, version_id)
    if ver is None or ver.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Sürüm bulunamadı")
    snap = db.scalar(
        select(SchemaSnapshot).where(SchemaSnapshot.dataset_version_id == version_id)
    )
    if snap is None:
        raise HTTPException(status_code=404, detail="Şema bulunamadı")
    return snap
