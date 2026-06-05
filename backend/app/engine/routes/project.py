"""
Project routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/project_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/project.py — APIRouter, port 8000 (consolidated)

Endpoints:
  DB-backed CRUD:
    GET  /api/projects              — proje listesi (DB)
    POST /api/projects              — proje oluştur (DB)
    GET  /api/projects/{project_id} — tek proje (DB, int id)

  Dosya sistemi (eski, uyumluluk):
    GET  /api/projects/fs                          — fs proje listesi
    POST /api/projects/create                      — fs proje oluştur + scaffold
    POST /api/projects/open                        — fs projeyi aktif yap
    GET  /api/projects/fs/{project_name}           — fs proje detayı
    DELETE /api/projects/fs/{project_name}/delete  — fs proje sil

Not: Flask session tabanlı "aktif proje" state'i, process-level in-memory dict ile
     simüle edilir. Wave-25'te DB-tabanlı kullanıcı context'ine taşınacak.
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["engine", "project"])

# Process-level active project state (Flask session yerine).
_active_project: Optional[str] = None


# ─── Schemas ─────────────────────────────────────────────────────────────────


class ProjectCreateDB(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""


class ProjectCreateFS(BaseModel):
    name: str = Field(..., min_length=1)


class ProjectOpenRequest(BaseModel):
    name: str = Field(..., min_length=1)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _get_settings():
    from config.settings import settings  # type: ignore
    return settings


def _get_active_project() -> Optional[str]:
    return _active_project


def _set_active_project(project_name: Optional[str]) -> None:
    global _active_project
    _active_project = project_name


def _get_project_path(project_name: Optional[str] = None) -> Path:
    settings = _get_settings()
    if project_name is None:
        return settings.BASE_DIR
    projects_dir = settings.BASE_DIR / "projects"
    return projects_dir / project_name


def _load_project_metadata(project_path: Path) -> dict:
    metadata_file = project_path / "PROJECT.json"
    if metadata_file.exists():
        try:
            return json.loads(metadata_file.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.debug("PROJECT.json okunamadı %s: %s", metadata_file, exc)
    return {
        "name": project_path.name,
        "created_at": datetime.now().isoformat(),
        "version": "1.0.0",
    }


def _get_db():
    from core.db import (  # type: ignore
        create_project as db_create_project,
    )
    from core.db import (
        get_project as db_get_project,
    )
    from core.db import (
        get_projects as db_get_projects,
    )
    return db_create_project, db_get_projects, db_get_project


def _get_scaffolder(project_name: str):
    import importlib.util as _ilu
    import sys as _sys

    scaffold_path = Path(__file__).resolve().parents[5] / "engine" / "scripts" / "scaffold_project.py"
    if "scripts.scaffold_project" not in _sys.modules:
        spec = _ilu.spec_from_file_location("scripts.scaffold_project", scaffold_path)
        mod = _ilu.module_from_spec(spec)
        _sys.modules["scripts.scaffold_project"] = mod
        spec.loader.exec_module(mod)
    from scripts.scaffold_project import ProjectScaffolder  # type: ignore
    return ProjectScaffolder(project_name)


# ─── DB-backed CRUD endpoints ────────────────────────────────────────────────


@router.get("", summary="Projeleri DB'den listeler")
def list_projects_db():
    """Projeleri SQLite DB'den listeler."""
    try:
        _, db_get_projects, _ = _get_db()
        rows = db_get_projects()
        projects = [dict(r) for r in rows]
        return {"projects": projects, "total": len(projects)}
    except Exception as exc:
        logger.error("DB proje listesi hatası: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("", status_code=status.HTTP_201_CREATED, summary="Yeni proje oluştur (DB)")
def create_project_db(body: ProjectCreateDB):
    """Yeni proje oluşturur (DB)."""
    try:
        db_create_project, _, _ = _get_db()
        project_id = db_create_project(name=body.name, description=body.description)
        return {"ok": True, "id": project_id, "name": body.name}
    except Exception as exc:
        logger.error("DB proje oluşturma hatası: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/{project_id:int}", summary="Tek proje kaydını döner (DB)")
def get_project_db(project_id: int):
    """Tek proje kaydını döner (DB)."""
    try:
        _, _, db_get_project = _get_db()
        row = db_get_project(project_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proje bulunamadı")
        return dict(row)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ─── Dosya sistemi tabanlı endpoints (uyumluluk) ────────────────────────────


@router.get("/fs", summary="Mevcut projeleri listele (dosya sistemi)")
def list_projects_fs():
    """Mevcut projeleri listele (dosya sistemi)."""
    settings = _get_settings()
    projects = []
    projects_dir = settings.BASE_DIR / "projects"

    projects.append({
        "name": "main",
        "path": str(settings.BASE_DIR),
        "is_active": _get_active_project() is None,
        "created_at": datetime.fromtimestamp(settings.BASE_DIR.stat().st_mtime).isoformat(),
        "type": "main",
    })

    if projects_dir.exists():
        for project_dir in sorted(projects_dir.iterdir()):
            if project_dir.is_dir():
                metadata = _load_project_metadata(project_dir)
                projects.append({
                    "name": project_dir.name,
                    "path": str(project_dir),
                    "is_active": _get_active_project() == project_dir.name,
                    "created_at": metadata.get("created_at"),
                    "type": "sub",
                })

    return {
        "projects": projects,
        "active": _get_active_project() or "main",
        "total": len(projects),
    }


@router.post("/create", status_code=status.HTTP_201_CREATED, summary="Yeni proje oluştur (dosya sistemi + scaffold)")
def create_project_fs(body: ProjectCreateFS):
    """Yeni proje oluştur (dosya sistemi + scaffold)."""
    try:
        scaffolder = _get_scaffolder(body.name)
        if not scaffolder.create():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Proje oluşturulamadı",
            )
        _set_active_project(body.name)
        return {
            "success": True,
            "message": f"Proje '{body.name}' başarıyla oluşturuldu",
            "project": {
                "name": body.name,
                "path": str(scaffolder.project_path),
                "is_active": True,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/open", summary="Mevcut projeyi aktif yap (dosya sistemi)")
def open_project_fs(body: ProjectOpenRequest):
    """Mevcut projeyi aktif yap (dosya sistemi)."""
    try:
        settings = _get_settings()
        if body.name == "main":
            _set_active_project(None)
            project_path = settings.BASE_DIR
        else:
            project_path = settings.BASE_DIR / "projects" / body.name
            if not project_path.exists():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proje bulunamadı")
            _set_active_project(body.name)

        metadata = _load_project_metadata(project_path)
        return {
            "success": True,
            "message": f"Proje '{body.name}' açıldı",
            "project": {
                "name": body.name,
                "path": str(project_path),
                "is_active": True,
                "metadata": metadata,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/fs/{project_name}", summary="Belirli bir projenin bilgisini al (dosya sistemi)")
def get_project_fs(project_name: str):
    """Belirli bir projenin bilgisini al (dosya sistemi)."""
    try:
        settings = _get_settings()
        if project_name == "main":
            project_path = settings.BASE_DIR
        else:
            project_path = settings.BASE_DIR / "projects" / project_name

        if not project_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proje bulunamadı")

        metadata = _load_project_metadata(project_path)
        test_count = (
            len(list((project_path / "tests").glob("**/*.py")))
            if (project_path / "tests").exists()
            else 0
        )
        feature_count = (
            len(list((project_path / "features").glob("**/*.feature")))
            if (project_path / "features").exists()
            else 0
        )

        return {
            "name": project_name,
            "path": str(project_path),
            "is_active": (
                project_name == _get_active_project()
                or (project_name == "main" and _get_active_project() is None)
            ),
            "metadata": metadata,
            "stats": {"test_files": test_count, "feature_files": feature_count},
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.delete(
    "/fs/{project_name}/delete",
    status_code=status.HTTP_200_OK,
    summary="Proje sil (sadece sub-project'ler, dosya sistemi)",
)
def delete_project_fs(project_name: str):
    """Proje sil (sadece sub-project'ler, dosya sistemi)."""
    if project_name == "main":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Main project silemezsin",
        )

    try:
        settings = _get_settings()
        project_path = settings.BASE_DIR / "projects" / project_name

        if not project_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proje bulunamadı")

        if _get_active_project() == project_name:
            _set_active_project(None)

        shutil.rmtree(project_path)
        return {"success": True, "message": f"Proje '{project_name}' silindi"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
