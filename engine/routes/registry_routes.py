"""
Locator Registry API Route'ları
================================
Selector chain destekli locator yönetimi.
Mevcut locators_routes.py'nin gelişmiş versiyonu.
"""
import json
from pathlib import Path
from flask import Blueprint, request, jsonify

from config.settings import settings

registry_bp = Blueprint("registry", __name__)

_registry = None


def _get_registry():
    """Singleton LocatorRegistry döner."""
    global _registry
    if _registry is None:
        from core.locator_registry import LocatorRegistry
        _registry = LocatorRegistry()
        default_locators = settings.BASE_DIR / "locators" / "default" / "bgts_locators.json"
        if default_locators.exists():
            _registry.load(default_locators)
        _registry.sync_from_db()
    return _registry


@registry_bp.route("/api/registry/entries", methods=["GET"])
def list_entries():
    """Tüm locator entry'lerini listeler. Opsiyonel screen filtresi."""
    try:
        reg = _get_registry()
        screen = request.args.get("screen")
        if screen:
            entries = reg.get_by_screen(screen)
        else:
            entries = reg.all_entries
        return jsonify({
            "ok": True,
            "entries": [e.to_dict() for e in entries],
            "count": len(entries),
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@registry_bp.route("/api/registry/entries/<name>", methods=["GET"])
def get_entry(name: str):
    """Belirli bir locator entry'sini döner."""
    try:
        reg = _get_registry()
        entry = reg.get(name)
        if not entry:
            return jsonify({"ok": False, "error": "Bulunamadı"}), 404
        return jsonify({"ok": True, "entry": entry.to_dict()})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@registry_bp.route("/api/registry/entries", methods=["POST"])
def create_entry():
    """
    Yeni locator entry oluşturur veya mevcut olanı günceller.

    JSON body:
      name        — Element adı (zorunlu)
      chain       — [{"type": "testid", "value": "...", "confidence": 1.0, "stable": true}, ...]
      page_url    — Sayfa URL (opsiyonel)
      screen      — Ekran adı (opsiyonel)
      element_type — button, input, link, etc. (opsiyonel)
    """
    try:
        from core.locator_registry import SelectorChain, SelectorCandidate
        reg = _get_registry()
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"ok": False, "error": "name gerekli"}), 400

        chain_data = data.get("chain", [])
        if not chain_data:
            return jsonify({"ok": False, "error": "chain gerekli (en az 1 aday)"}), 400

        chain = SelectorChain([SelectorCandidate.from_dict(c) for c in chain_data])
        reg.register(
            name=name,
            chain=chain,
            page_url=data.get("page_url", ""),
            screen=data.get("screen", ""),
            element_type=data.get("element_type", ""),
            metadata=data.get("metadata"),
        )

        return jsonify({"ok": True, "name": name})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@registry_bp.route("/api/registry/entries/<name>", methods=["DELETE"])
def delete_entry(name: str):
    """Locator entry siler."""
    try:
        reg = _get_registry()
        reg.unregister(name)
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@registry_bp.route("/api/registry/resolve/<name>", methods=["GET"])
def resolve_entry(name: str):
    """
    Entry'nin primary selector'ını döner.
    DOM canlı çözümleme (self-healing) sadece page context'te çalışır.
    """
    try:
        reg = _get_registry()
        selector = reg.resolve(name)
        entry = reg.get(name)
        return jsonify({
            "ok": True,
            "name": name,
            "resolved_selector": selector,
            "chain": entry.chain.to_list() if entry else [],
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@registry_bp.route("/api/registry/stats", methods=["GET"])
def registry_stats():
    """Registry istatistiklerini döner."""
    try:
        reg = _get_registry()
        return jsonify({"ok": True, "stats": reg.stats()})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@registry_bp.route("/api/registry/save", methods=["POST"])
def save_registry():
    """Registry'yi JSON dosyasına kaydeder."""
    try:
        reg = _get_registry()
        data = request.get_json() or {}
        path = data.get("path")
        if not path:
            path = settings.BASE_DIR / "locators" / "default" / "bgts_locators.json"
        reg.save(path)
        return jsonify({"ok": True, "path": str(path)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@registry_bp.route("/api/registry/sync-db", methods=["POST"])
def sync_db():
    """Registry <-> SQLite object_repository senkronizasyonu."""
    try:
        reg = _get_registry()
        direction = (request.get_json() or {}).get("direction", "from_db")
        if direction == "from_db":
            reg.sync_from_db()
        elif direction == "to_db":
            reg.sync_to_db()
        else:
            reg.sync_from_db()
            reg.sync_to_db()
        return jsonify({"ok": True, "direction": direction, "entry_count": len(reg.all_entries)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@registry_bp.route("/api/registry/heal-log", methods=["GET"])
def heal_log():
    """Self-healing loglarını döner."""
    try:
        reg = _get_registry()
        return jsonify({"ok": True, "log": reg.heal_log, "count": len(reg.heal_log)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@registry_bp.route("/api/registry/bulk-import", methods=["POST"])
def bulk_import():
    """
    JSON dosyasından toplu locator import eder.

    JSON body:
      entries — { "name": { "name": ..., "chain": [...], ... }, ... }
    """
    try:
        from core.locator_registry import SelectorChain, SelectorCandidate, LocatorEntry
        reg = _get_registry()
        data = request.get_json() or {}
        entries_data = data.get("entries", {})
        imported = 0
        for name, entry_dict in entries_data.items():
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
        return jsonify({"ok": True, "imported": imported})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
