"""
Regression routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/regression_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/regression.py — APIRouter, port 8000 (consolidated)

Bu pattern her route file için takip edilir. Bir Python developer kopyala-yapıştır + dönüştür yapar.
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/regression-sets", tags=["engine", "regression"])


# ─── Schemas ─────────────────────────────────────────────────────────────

class RegressionSetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class FeatureAdd(BaseModel):
    feature_name: str = Field(..., min_length=1)


class RegressionSetOut(BaseModel):
    id: int
    name: str
    feature_count: int = 0


# ─── Database dependency (placeholder — gerçek db.py'den import) ─────────

class RegressionStore:
    """Geçici in-memory store. Migration tamamlanınca SQLAlchemy repository kullanılacak."""

    def __init__(self):
        self._sets: dict[int, dict] = {}
        self._next_id = 1

    def list_sets(self) -> list[dict]:
        return list(self._sets.values())

    def create_set(self, name: str) -> dict:
        if any(s["name"] == name for s in self._sets.values()):
            raise ValueError("Aynı isimli set zaten var")
        s = {"id": self._next_id, "name": name, "features": []}
        self._sets[self._next_id] = s
        self._next_id += 1
        return s

    def delete_set(self, set_id: int) -> None:
        self._sets.pop(set_id, None)

    def add_feature(self, set_id: int, feature: str) -> None:
        if set_id in self._sets and feature not in self._sets[set_id]["features"]:
            self._sets[set_id]["features"].append(feature)

    def remove_feature(self, set_id: int, feature: str) -> None:
        if set_id in self._sets and feature in self._sets[set_id]["features"]:
            self._sets[set_id]["features"].remove(feature)


_store = RegressionStore()


def get_store() -> RegressionStore:
    return _store


# ─── Routes ──────────────────────────────────────────────────────────────

@router.get("", response_model=list[dict])
def list_regression_sets(store: Annotated[RegressionStore, Depends(get_store)]):
    return store.list_sets()


@router.post("", status_code=status.HTTP_201_CREATED)
def new_regression_set(
    body: RegressionSetCreate,
    store: Annotated[RegressionStore, Depends(get_store)],
):
    try:
        return store.create_set(body.name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_regression_set(
    set_id: int,
    store: Annotated[RegressionStore, Depends(get_store)],
):
    store.delete_set(set_id)


@router.post("/{set_id}/features", status_code=status.HTTP_201_CREATED)
def add_feature_to_set(
    set_id: int,
    body: FeatureAdd,
    store: Annotated[RegressionStore, Depends(get_store)],
):
    store.add_feature(set_id, body.feature_name)
    return {"ok": True}


@router.delete("/{set_id}/features/{feature_name}", status_code=status.HTTP_204_NO_CONTENT)
def remove_feature_from_set(
    set_id: int,
    feature_name: str,
    store: Annotated[RegressionStore, Depends(get_store)],
):
    store.remove_feature(set_id, feature_name)
