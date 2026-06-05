from __future__ import annotations

"""
Registry routes — Flask engine'den FastAPI'ye port edilmiştir.

ÖNCE (Flask):
  /engine/routes/registry_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/registry.py — APIRouter, port 8000 (consolidated)

Locator Registry API: selector chain destekli locator yönetimi.
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/registry", tags=["engine", "registry"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class SelectorCandidateIn(BaseModel):
    type: str = Field(..., description="Selector tipi: testid, css, xpath, text, …")
    value: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    stable: bool = True


class EntryCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Element adı")
    chain: list[SelectorCandidateIn] = Field(..., min_length=1, description="En az 1 aday gerekli")
    page_url: str = Field(default="")
    screen: str = Field(default="")
    element_type: str = Field(default="")
    metadata: dict[str, Any] | None = None


class SaveRegistryBody(BaseModel):
    path: str | None = Field(default=None, description="Kayıt dosyası yolu (opsiyonel)")


class SyncDbBody(BaseModel):
    direction: str = Field(
        default="from_db",
        description="Senkronizasyon yönü: from_db | to_db | both",
    )


class BulkImportBody(BaseModel):
    entries: dict[str, dict] = Field(default_factory=dict)


# ─── Singleton store dependency ───────────────────────────────────────────────

_registry_instance = None


def _get_default_locators_path() -> Path:
    try:
        from app.config import settings as app_settings
        return Path(app_settings.ENGINE_BASE_DIR) / "locators" / "default" / "bgts_locators.json"
    except Exception:
        return Path(__file__).parents[4] / "engine" / "locators" / "default" / "bgts_locators.json"


def get_registry():
    """Singleton LocatorRegistry döner. Geçici in-memory store; gerçek DB sonra."""
    global _registry_instance
    if _registry_instance is None:
        from core.locator_registry import LocatorRegistry  # engine-side import
        _registry_instance = LocatorRegistry()
        default_locators = _get_default_locators_path()
        if default_locators.exists():
            _registry_instance.load(default_locators)
        _registry_instance.sync_from_db()
    return _registry_instance


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/entries", response_model=dict)
def list_entries(screen: str | None = None):
    """Tüm locator entry'lerini listeler. Opsiyonel screen filtresi."""
    try:
        reg = get_registry()
        entries = reg.get_by_screen(screen) if screen else reg.all_entries
        return {
            "ok": True,
            "entries": [e.to_dict() for e in entries],
            "count": len(entries),
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/entries/{name}", response_model=dict)
def get_entry(name: str):
    """Belirli bir locator entry'sini döner."""
    try:
        reg = get_registry()
        entry = reg.get(name)
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bulunamadı")
        return {"ok": True, "entry": entry.to_dict()}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/entries", status_code=status.HTTP_201_CREATED, response_model=dict)
def create_entry(body: EntryCreate):
    """Yeni locator entry oluşturur veya mevcut olanı günceller."""
    try:
        from core.locator_registry import SelectorCandidate, SelectorChain

        reg = get_registry()
        chain = SelectorChain(
            [SelectorCandidate.from_dict(c.model_dump()) for c in body.chain]
        )
        reg.register(
            name=body.name,
            chain=chain,
            page_url=body.page_url,
            screen=body.screen,
            element_type=body.element_type,
            metadata=body.metadata,
        )
        return {"ok": True, "name": body.name}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.delete("/entries/{name}", status_code=status.HTTP_200_OK)
def delete_entry(name: str):
    """Locator entry siler."""
    try:
        reg = get_registry()
        reg.unregister(name)
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/resolve/{name}", response_model=dict)
def resolve_entry(name: str):
    """
    Entry'nin primary selector'ını döner.
    DOM canlı çözümleme (self-healing) sadece page context'te çalışır.
    """
    try:
        reg = get_registry()
        selector = reg.resolve(name)
        entry = reg.get(name)
        return {
            "ok": True,
            "name": name,
            "resolved_selector": selector,
            "chain": entry.chain.to_list() if entry else [],
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/stats", response_model=dict)
def registry_stats():
    """Registry istatistiklerini döner."""
    try:
        reg = get_registry()
        return {"ok": True, "stats": reg.stats()}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/save", response_model=dict)
def save_registry(body: SaveRegistryBody):
    """Registry'yi JSON dosyasına kaydeder."""
    try:
        reg = get_registry()
        path = body.path or str(_get_default_locators_path())
        reg.save(path)
        return {"ok": True, "path": str(path)}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/sync-db", response_model=dict)
def sync_db(body: SyncDbBody):
    """Registry <-> SQLite object_repository senkronizasyonu."""
    try:
        reg = get_registry()
        if body.direction == "from_db":
            reg.sync_from_db()
        elif body.direction == "to_db":
            reg.sync_to_db()
        else:
            reg.sync_from_db()
            reg.sync_to_db()
        return {"ok": True, "direction": body.direction, "entry_count": len(reg.all_entries)}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/heal-log", response_model=dict)
def heal_log():
    """Self-healing loglarını döner."""
    try:
        reg = get_registry()
        return {"ok": True, "log": reg.heal_log, "count": len(reg.heal_log)}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/bulk-import", response_model=dict)
def bulk_import(body: BulkImportBody):
    """JSON verisinden toplu locator import eder."""
    try:
        from core.locator_registry import LocatorEntry

        reg = get_registry()
        imported = 0
        for _name, entry_dict in body.entries.items():
            entry = LocatorEntry.from_dict(entry_dict)
            reg.register(
                name=entry.name,
                chain=entry.chain,
                page_url=entry.page_url,
                screen=entry.screen,
                element_type=entry.element_type,
                metadata=entry.metadata,
            )
            imported += 1
        return {"ok": True, "imported": imported}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
