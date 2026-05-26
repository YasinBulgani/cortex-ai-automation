"""
Proje yönetimi için API endpoints.
- DB-backed proje CRUD (/api/projects — GET, POST, GET/:id)
- Dosya sistemi tabanlı proje yönetimi (eski, uyumluluk için korundu)
- Aktif proje değiştirme

DB endpoints backward compatible: project_id opsiyonel parametrelere geçirilir.
"""

from flask import Blueprint, request, jsonify, session
from pathlib import Path
import json
import logging
from datetime import datetime
from config.settings import settings
import importlib.util as _ilu
import sys as _sys
# Load scaffold_project by absolute path to avoid 'scripts' namespace shadowing.
_scaffold_path = Path(__file__).resolve().parent.parent / "scripts" / "scaffold_project.py"
if "scripts.scaffold_project" not in _sys.modules:
    _spec = _ilu.spec_from_file_location("scripts.scaffold_project", _scaffold_path)
    _mod = _ilu.module_from_spec(_spec)
    _sys.modules["scripts.scaffold_project"] = _mod
    _spec.loader.exec_module(_mod)
from scripts.scaffold_project import ProjectScaffolder
from core.db import create_project as db_create_project, get_projects as db_get_projects, get_project as db_get_project

logger = logging.getLogger(__name__)

project_bp = Blueprint('project', __name__)


def get_active_project():
    """Session'dan aktif proje adını al."""
    return session.get('active_project', None)


def set_active_project(project_name):
    """Session'da aktif projeyi ayarla."""
    session['active_project'] = project_name
    session.modified = True


def get_project_path(project_name=None):
    """Proje dizinini al."""
    if project_name is None:
        project_name = get_active_project()

    if project_name is None:
        return settings.BASE_DIR

    projects_dir = settings.BASE_DIR / "projects"
    return projects_dir / project_name


def load_project_metadata(project_path: Path):
    """PROJECT.json dosyasından proje metadata'sını yükle."""
    metadata_file = project_path / "PROJECT.json"

    if metadata_file.exists():
        try:
            return json.loads(metadata_file.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.debug("PROJECT.json okunamadı %s: %s", metadata_file, exc)

    return {
        "name": project_path.name,
        "created_at": datetime.now().isoformat(),
        "version": "1.0.0"
    }


# ── DB-backed CRUD endpoints ─────────────────────────────────────────────────

@project_bp.route("/api/projects", methods=["GET"])
def list_projects_db():
    """
    Projeleri SQLite DB'den listeler.
    Yanıt: { projects: [{id, name, description, created_at}], total }
    """
    try:
        rows = db_get_projects()
        projects = [dict(r) for r in rows]
        return jsonify({"projects": projects, "total": len(projects)})
    except Exception as exc:
        logger.error("DB proje listesi hatası: %s", exc)
        return jsonify({"error": str(exc)}), 500


@project_bp.route("/api/projects", methods=["POST"])
def create_project_db():
    """
    Yeni proje oluşturur (DB).
    Body: { name, description?, target_url?, llm_provider?, llm_model? }
    Yanıt: { id, name, ok: true }
    """
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name zorunludur"}), 400
    description = data.get("description", "")
    try:
        project_id = db_create_project(name=name, description=description)
        return jsonify({"ok": True, "id": project_id, "name": name}), 201
    except Exception as exc:
        logger.error("DB proje oluşturma hatası: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 500


@project_bp.route("/api/projects/<int:project_id>", methods=["GET"])
def get_project_db(project_id: int):
    """Tek proje kaydını döner."""
    try:
        row = db_get_project(project_id)
        if not row:
            return jsonify({"error": "Proje bulunamadı"}), 404
        return jsonify(dict(row))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── Eski dosya sistemi tabanlı endpoints (uyumluluk) ─────────────────────────

@project_bp.route("/api/projects/fs", methods=["GET"])
def list_projects():
    """
    Mevcut projeleri listele.
    """
    projects = []
    projects_dir = settings.BASE_DIR / "projects"

    # Main project
    projects.append({
        "name": "main",
        "path": str(settings.BASE_DIR),
        "is_active": get_active_project() is None,
        "created_at": datetime.fromtimestamp(settings.BASE_DIR.stat().st_mtime).isoformat(),
        "type": "main"
    })

    # Alt projeler
    if projects_dir.exists():
        for project_dir in sorted(projects_dir.iterdir()):
            if project_dir.is_dir():
                metadata = load_project_metadata(project_dir)
                projects.append({
                    "name": project_dir.name,
                    "path": str(project_dir),
                    "is_active": get_active_project() == project_dir.name,
                    "created_at": metadata.get("created_at"),
                    "type": "sub"
                })

    return jsonify({
        "projects": projects,
        "active": get_active_project() or "main",
        "total": len(projects)
    })


@project_bp.route("/api/projects/create", methods=["POST"])
def create_project():
    """
    Yeni proje oluştur.

    POST body:
    {
        "name": "project-name"
    }
    """
    try:
        data = request.get_json()
        project_name = data.get("name", "").strip()

        if not project_name:
            return jsonify({"error": "Proje adı gerekli"}), 400

        # Scaffolding işlemini başlat
        scaffolder = ProjectScaffolder(project_name)

        if not scaffolder.create():
            return jsonify({"error": "Proje oluşturulamadı"}), 500

        # Yeni projeyi aktif yap
        set_active_project(project_name)

        return jsonify({
            "success": True,
            "message": f"Proje '{project_name}' başarıyla oluşturuldu",
            "project": {
                "name": project_name,
                "path": str(scaffolder.project_path),
                "is_active": True
            }
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@project_bp.route("/api/projects/open", methods=["POST"])
def open_project():
    """
    Mevcut proje açmak ve aktif yapmak.

    POST body:
    {
        "name": "project-name"
    }
    """
    try:
        data = request.get_json()
        project_name = data.get("name", "").strip()

        if not project_name:
            return jsonify({"error": "Proje adı gerekli"}), 400

        if project_name == "main":
            set_active_project(None)
            project_path = settings.BASE_DIR
        else:
            projects_dir = settings.BASE_DIR / "projects"
            project_path = projects_dir / project_name

            if not project_path.exists():
                return jsonify({"error": "Proje bulunamadı"}), 404

            set_active_project(project_name)

        metadata = load_project_metadata(project_path)

        return jsonify({
            "success": True,
            "message": f"Proje '{project_name}' açıldı",
            "project": {
                "name": project_name if project_name != "main" else "main",
                "path": str(project_path),
                "is_active": True,
                "metadata": metadata
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@project_bp.route("/api/projects/<project_name>", methods=["GET"])
def get_project(project_name):
    """
    Belirli bir projenin bilgisini al.
    """
    try:
        if project_name == "main":
            project_path = settings.BASE_DIR
        else:
            projects_dir = settings.BASE_DIR / "projects"
            project_path = projects_dir / project_name

        if not project_path.exists():
            return jsonify({"error": "Proje bulunamadı"}), 404

        metadata = load_project_metadata(project_path)

        # Proje istatistikleri
        test_count = len(list((project_path / "tests").glob("**/*.py"))) if (project_path / "tests").exists() else 0
        feature_count = len(list((project_path / "features").glob("**/*.feature"))) if (project_path / "features").exists() else 0

        return jsonify({
            "name": project_name,
            "path": str(project_path),
            "is_active": (project_name == get_active_project() or (project_name == "main" and get_active_project() is None)),
            "metadata": metadata,
            "stats": {
                "test_files": test_count,
                "feature_files": feature_count
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@project_bp.route("/api/projects/<project_name>/delete", methods=["DELETE"])
def delete_project(project_name):
    """
    Proje sil (sadece sub-project'ler).
    """
    try:
        if project_name == "main":
            return jsonify({"error": "Main project silemezsin"}), 403

        projects_dir = settings.BASE_DIR / "projects"
        project_path = projects_dir / project_name

        if not project_path.exists():
            return jsonify({"error": "Proje bulunamadı"}), 404

        # Silinecek proje aktif ise, main projeye döndür
        if get_active_project() == project_name:
            set_active_project(None)

        # Proje dizinini sil
        import shutil
        shutil.rmtree(project_path)

        return jsonify({
            "success": True,
            "message": f"Proje '{project_name}' silindi"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
