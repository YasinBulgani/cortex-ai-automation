"""Catalog domain service facade.

The catalog domain has no specialized module layer, so this service
holds the thin CRUD business logic that was previously inlined in
the router handlers.  The router delegates here; tests and other
domains can import from this module directly without touching FastAPI.

Exposed API
-----------
list_datasets(db)                     -> list[Dataset]
get_dataset(db, dataset_id)           -> Dataset          (raises 404)
create_dataset(db, data, user_id)     -> Dataset
delete_dataset(db, dataset_id)        -> None             (raises 404)
list_versions(db, dataset_id)         -> list[DatasetVersion]
create_version(db, dataset_id, data, user_id) -> DatasetVersion
"""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infra.models import Dataset, DatasetVersion, SchemaSnapshot


# ── Datasets ─────────────────────────────────────────────────────────────────


def list_datasets(db: Session) -> List[Dataset]:
    """Return all datasets ordered newest-first."""
    return list(db.scalars(select(Dataset).order_by(Dataset.created_at.desc())).all())


def get_dataset(db: Session, dataset_id: str) -> Dataset:
    """Return the dataset with *dataset_id*.

    Raises:
        KeyError: if no dataset with that id exists.  The router converts
                  this to a 404 HTTP response.
    """
    ds = db.get(Dataset, dataset_id)
    if ds is None:
        raise KeyError(f"Veri seti bulunamadı: {dataset_id}")
    return ds


def create_dataset(
    db: Session,
    name: str,
    description: Optional[str],
    created_by: Optional[UUID],
) -> Dataset:
    """Create and persist a new dataset.

    The caller is responsible for calling ``log_audit`` and committing
    the session (or use the helper below which does both).

    Returns the refreshed ``Dataset`` ORM object.
    """
    ds = Dataset(name=name, description=description, created_by=created_by)
    db.add(ds)
    db.flush()
    return ds


def delete_dataset(db: Session, dataset_id: str) -> None:
    """Delete the dataset with *dataset_id*.

    Raises:
        KeyError: if the dataset does not exist.
    """
    ds = get_dataset(db, dataset_id)
    db.delete(ds)
    db.flush()


# ── Dataset Versions ─────────────────────────────────────────────────────────


def list_versions(db: Session, dataset_id: str) -> List[DatasetVersion]:
    """Return all versions for *dataset_id* ordered newest-first.

    Raises:
        KeyError: if the parent dataset does not exist.
    """
    get_dataset(db, dataset_id)  # validate existence
    return list(
        db.scalars(
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version.desc())
        ).all()
    )


def create_version(
    db: Session,
    dataset_id: str,
    snapshot: Optional[dict],
    profile: Optional[dict],
    pii_flags: Optional[dict],
    created_by: Optional[UUID] = None,
) -> DatasetVersion:
    """Create the next version for *dataset_id* and attach a schema snapshot.

    Auto-increments the version number based on the current maximum.
    The caller is responsible for audit-logging and committing the session.

    Returns the refreshed ``DatasetVersion`` ORM object.
    """
    get_dataset(db, dataset_id)  # validate parent exists
    max_v = db.scalar(
        select(func.max(DatasetVersion.version)).where(
            DatasetVersion.dataset_id == dataset_id
        )
    )
    next_v = (max_v or 0) + 1
    ver = DatasetVersion(dataset_id=dataset_id, version=next_v, status="draft")
    db.add(ver)
    db.flush()
    snap = SchemaSnapshot(
        dataset_version_id=ver.id,
        snapshot=snapshot or {},
        profile=profile,
        pii_flags=pii_flags,
    )
    db.add(snap)
    db.flush()
    return ver
