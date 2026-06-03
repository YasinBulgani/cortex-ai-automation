"""
Feature routes — Flask engine'den FastAPI'ye port edilmiştir.

ÖNCE (Flask):
  /engine/routes/feature_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/feature.py — APIRouter, port 8000 (consolidated)
"""

import shutil
from pathlib import Path
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/features", tags=["engine", "feature"])

# ─── Engine settings (path helpers) ──────────────────────────────────────────

def _features_dir() -> Path:
    """Returns the features directory; falls back to a safe default."""
    try:
        from app.config import settings as app_settings
        return Path(app_settings.ENGINE_FEATURES_DIR)
    except Exception:
        return Path(__file__).parents[4] / "engine" / "features"


def _tests_dir() -> Path:
    try:
        from app.config import settings as app_settings
        return Path(app_settings.ENGINE_TESTS_DIR)
    except Exception:
        return Path(__file__).parents[4] / "engine" / "tests"


def _steps_dir() -> Path:
    try:
        from app.config import settings as app_settings
        return Path(app_settings.ENGINE_STEPS_DIR)
    except Exception:
        return Path(__file__).parents[4] / "engine" / "steps"


# ─── Schemas ─────────────────────────────────────────────────────────────────

class FolderCreate(BaseModel):
    path: str = Field(..., min_length=1, description="Klasör yolu (features dizinine göreceli)")


class FolderDelete(BaseModel):
    path: str = Field(..., min_length=1, description="Silinecek klasör yolu")


class FeatureSave(BaseModel):
    content: str = Field(default="", description="Feature dosyası içeriği")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _step_import_lines() -> list[str]:
    imports: list[str] = []
    steps_dir = _steps_dir()
    for step_file in sorted(steps_dir.glob("*.py")):
        if step_file.name.startswith("_") or step_file.name in {"__init__.py", "conftest.py"}:
            continue
        imports.append(f"from steps.{step_file.stem} import *  # noqa: F401,F403")
    return imports


def _build_glue_content(feature_name: str) -> str:
    lines = [
        "from pytest_bdd import scenarios",
        *_step_import_lines(),
        "",
        f'scenarios("../features/{feature_name}")',
        "",
    ]
    return "\n".join(lines)


def _build_tree(directory: Path, base: Path) -> list:
    """Recursive helper: returns a tree of folders and .feature files under `directory`."""
    items: list = []
    try:
        entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except (PermissionError, FileNotFoundError):
        return items

    for entry in entries:
        rel = entry.relative_to(base)
        if entry.is_dir():
            items.append({
                "type": "folder",
                "name": entry.name,
                "path": str(rel),
                "children": _build_tree(entry, base),
            })
        elif entry.suffix == ".feature":
            try:
                content = entry.read_text(encoding="utf-8")
                items.append({
                    "type": "file",
                    "name": entry.name,
                    "stem": entry.stem,
                    "path": str(rel),
                    "scenarios": content.count("Scenario") or content.count("Senaryo"),
                    "size": entry.stat().st_size,
                    "modified": datetime.fromtimestamp(entry.stat().st_mtime).strftime("%d.%m.%Y %H:%M"),
                })
            except Exception:
                continue
    return items


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("", response_model=list[dict])
def list_features():
    """Tüm feature dosyalarını ağaç yapısında listeler."""
    features_dir = _features_dir()
    features_dir.mkdir(exist_ok=True)
    return _build_tree(features_dir, features_dir)


@router.post("/folder", status_code=status.HTTP_201_CREATED)
def create_folder(body: FolderCreate):
    """Yeni bir klasör oluşturur."""
    folder = _features_dir() / body.path
    folder.mkdir(parents=True, exist_ok=True)
    return {"ok": True}


@router.delete("/folder", status_code=status.HTTP_200_OK)
def delete_folder(body: FolderDelete):
    """Mevcut klasörü ve içeriğini siler."""
    folder = _features_dir() / body.path
    if folder.exists() and folder.is_dir():
        shutil.rmtree(folder)
    return {"ok": True}


@router.get("/{name:path}")
def get_feature(name: str):
    """Belirli bir feature dosyasının içeriğini döner."""
    path = _features_dir() / name
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bulunamadı")
    return {"name": name, "content": path.read_text(encoding="utf-8")}


@router.put("/{name:path}", status_code=status.HTTP_200_OK)
def save_feature(name: str, body: FeatureSave):
    """Feature dosyasını kaydeder; yoksa glue dosyası da oluşturur."""
    if not name.endswith(".feature"):
        name += ".feature"
    path = _features_dir() / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.content, encoding="utf-8")

    # Karşılık gelen glue dosyasını oluştur / güncelle
    safe_name = name.replace("/", "_").replace("\\", "_")
    stem = Path(safe_name).stem
    glue_path = _tests_dir() / f"test_{stem}.py"
    glue_path.write_text(_build_glue_content(name), encoding="utf-8")

    return {"ok": True}


@router.delete("/{name:path}", status_code=status.HTTP_200_OK)
def delete_feature(name: str):
    """Feature dosyasını ve ilişkili glue dosyasını siler."""
    path = _features_dir() / name
    if path.exists():
        path.unlink()

    safe_name = name.replace("/", "_").replace("\\", "_")
    glue = _tests_dir() / f"test_{Path(safe_name).stem}.py"
    if glue.exists():
        glue.unlink()

    return {"ok": True}
