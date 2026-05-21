from flask import Blueprint, request, jsonify, current_app
from pathlib import Path
from datetime import datetime
import shutil
from config.settings import settings

feature_bp = Blueprint('feature', __name__)


def _step_import_lines() -> list[str]:
    imports: list[str] = []
    steps_dir = settings.BASE_DIR / "steps"
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
    """Recursive helper: returns a tree of folders and files under `directory`."""
    items = []
    try:
        entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return items
    except FileNotFoundError:
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

@feature_bp.route("/api/features", methods=["GET"])
def list_features():
    settings.FEATURES_DIR.mkdir(exist_ok=True)
    return jsonify(_build_tree(settings.FEATURES_DIR, settings.FEATURES_DIR))

@feature_bp.route("/api/features/folder", methods=["POST"])
def create_folder():
    path_str = (request.json or {}).get("path", "")
    if not path_str:
        return jsonify({"error": "Geçersiz klasör yolu"}), 400
    folder = settings.FEATURES_DIR / path_str
    folder.mkdir(parents=True, exist_ok=True)
    return jsonify({"ok": True})

@feature_bp.route("/api/features/folder", methods=["DELETE"])
def delete_folder():
    path_str = (request.json or {}).get("path", "")
    if not path_str:
        return jsonify({"error": "Geçersiz klasör yolu"}), 400
    folder = settings.FEATURES_DIR / path_str
    if folder.exists() and folder.is_dir():
        shutil.rmtree(folder)
    return jsonify({"ok": True})

@feature_bp.route("/api/features/<path:name>", methods=["GET"])
def get_feature(name):
    path = settings.FEATURES_DIR / name
    if not path.exists():
        return jsonify({"error": "Bulunamadı"}), 404
    return jsonify({"name": name, "content": path.read_text(encoding="utf-8")})

@feature_bp.route("/api/features/<path:name>", methods=["PUT"])
def save_feature(name):
    if not name.endswith(".feature"):
        name += ".feature"
    path = settings.FEATURES_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (request.json or {}).get("content", "")
    path.write_text(content, encoding="utf-8")

    # Karşılık gelen glue dosyası yoksa oluştur
    # Çakışmaları önlemek için dosya adını path'e göre belirle (örn: auth_login.py)
    safe_name = name.replace("/", "_").replace("\\", "_")
    stem = Path(safe_name).stem
    glue_path = settings.TESTS_DIR / f"test_{stem}.py"
    
    # Her zaman güncelle veya yoksa oluştur
    glue_path.write_text(_build_glue_content(name), encoding="utf-8")
    return jsonify({"ok": True})

@feature_bp.route("/api/features/<path:name>", methods=["DELETE"])
def delete_feature(name):
    path = settings.FEATURES_DIR / name
    if path.exists():
        path.unlink()
    
    safe_name = name.replace("/", "_").replace("\\", "_")
    glue = settings.TESTS_DIR / f"test_{Path(safe_name).stem}.py"
    if glue.exists():
        glue.unlink()
    return jsonify({"ok": True})
