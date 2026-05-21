"""
Test Recorder API Route'ları
==============================
Kayıt oturumu yönetimi ve kod üretimi için REST endpoint'leri.
"""
import json
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file

from config.settings import settings

recorder_bp = Blueprint("recorder", __name__)

# Aktif oturumları bellekte tut (sunucu taraflı)
_active_sessions: dict[str, object] = {}


def _get_recorder(session_id: str):
    """Aktif kaydedici örneğini döner."""
    return _active_sessions.get(session_id)


# ──────────────────────────────────────────────────────────────────────────────
# Oturum Yönetimi
# ──────────────────────────────────────────────────────────────────────────────
@recorder_bp.route("/api/recorder/start", methods=["POST"])
def start_recording():
    """
    Yeni bir kayıt oturumu başlatır.

    JSON body:
      name     — Oturum adı (zorunlu)
      domain   — Domain adı (ark, ghz, girit, vs.)
      base_url — Başlangıç URL

    Returns:
      {ok, session_id, name}
    """
    try:
        from core.test_recorder import TestRecorder
        data     = request.get_json() or {}
        name     = data.get("name", "").strip()
        domain   = data.get("domain", "default")
        base_url = data.get("base_url", "")

        if not name:
            return jsonify({"ok": False, "error": "name gerekli"}), 400

        import uuid
        session_id = str(uuid.uuid4())[:8]
        recorder = TestRecorder(name=name, domain=domain, base_url=base_url)
        recorder.start()
        _active_sessions[session_id] = recorder

        return jsonify({
            "ok": True,
            "session_id": session_id,
            "name": name,
            "domain": domain,
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@recorder_bp.route("/api/recorder/<session_id>/stop", methods=["POST"])
def stop_recording(session_id: str):
    """
    Kayıt oturumunu durdurur ve JSON dosyasına kaydeder.

    Returns:
      {ok, session_id, saved_path, action_count}
    """
    try:
        recorder = _get_recorder(session_id)
        if not recorder:
            return jsonify({"ok": False, "error": "Oturum bulunamadı"}), 404

        session = recorder.stop()
        saved_path = recorder.save_session()
        _active_sessions.pop(session_id, None)

        return jsonify({
            "ok": True,
            "session_id": session_id,
            "saved_path": saved_path,
            "action_count": len(session.actions),
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@recorder_bp.route("/api/recorder/sessions", methods=["GET"])
def list_sessions():
    """
    Kaydedilmiş oturumları listeler.

    Query params:
      domain — Filtre için domain adı (opsiyonel)
    """
    try:
        records_dir = settings.BASE_DIR / "recordings"
        records_dir.mkdir(exist_ok=True)
        domain_filter = request.args.get("domain")

        sessions = []
        for f in sorted(records_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if domain_filter and data.get("domain") != domain_filter:
                    continue
                sessions.append({
                    "file": f.name,
                    "path": str(f),
                    "name": data.get("name", f.stem),
                    "domain": data.get("domain", ""),
                    "action_count": len(data.get("actions", [])),
                    "started_at": data.get("started_at", ""),
                })
            except Exception:
                continue

        return jsonify({"ok": True, "sessions": sessions, "count": len(sessions)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@recorder_bp.route("/api/recorder/sessions/<path:session_file>", methods=["DELETE"])
def delete_session(session_file: str):
    """Kaydedilmiş bir oturumu siler."""
    try:
        records_dir = settings.BASE_DIR / "recordings"
        # Güvenlik: sadece recordings dizinindeki dosyalar
        target = (records_dir / session_file).resolve()
        if not str(target).startswith(str(records_dir.resolve())):
            return jsonify({"ok": False, "error": "Geçersiz dosya yolu"}), 403

        if not target.exists():
            return jsonify({"ok": False, "error": "Dosya bulunamadı"}), 404

        target.unlink()
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# Aksiyon Ekleme (aktif oturuma)
# ──────────────────────────────────────────────────────────────────────────────
@recorder_bp.route("/api/recorder/<session_id>/action", methods=["POST"])
def add_action(session_id: str):
    """
    Aktif oturuma aksiyon ekler.

    JSON body:
      action_type   — click | type | navigate | scroll | wait | assert_text | vs.
      selector      — CSS seçici (navigate dışı için)
      value         — Değer (type için metin, navigate için URL)
      selector_type — css | xpath | text | testid
      element_name  — Element adı (opsiyonel)
      element_info  — {tag, id, aria-label, ...} (opsiyonel)
      metadata      — Ek bilgi dict
    """
    try:
        from core.test_recorder import RecordedAction
        recorder = _get_recorder(session_id)
        if not recorder:
            return jsonify({"ok": False, "error": "Aktif oturum bulunamadı"}), 404

        data = request.get_json() or {}
        action_type   = data.get("action_type", "")
        if not action_type:
            return jsonify({"ok": False, "error": "action_type gerekli"}), 400

        element_info  = data.get("element_info")
        selector      = data.get("selector", "")
        value         = data.get("value", "")
        selector_type = data.get("selector_type", "css")
        element_name  = data.get("element_name", "")
        metadata      = data.get("metadata", {})

        action = recorder._recorder.record(
            action_type=action_type,
            selector=selector,
            value=value,
            selector_type=selector_type,
            element_info=element_info,
            metadata=metadata,
        )
        if element_name:
            action.element_name = element_name

        return jsonify({
            "ok": True,
            "action": action.to_dict(),
            "total_actions": len(recorder.session.actions),
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@recorder_bp.route("/api/recorder/<session_id>/actions", methods=["GET"])
def get_actions(session_id: str):
    """Aktif oturumdaki tüm aksiyonları döner."""
    try:
        recorder = _get_recorder(session_id)
        if not recorder:
            return jsonify({"ok": False, "error": "Oturum bulunamadı"}), 404

        actions = [a.to_dict() for a in recorder.session.actions]
        return jsonify({"ok": True, "actions": actions, "count": len(actions)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# Kod Üretimi
# ──────────────────────────────────────────────────────────────────────────────
@recorder_bp.route("/api/recorder/generate", methods=["POST"])
def generate_code():
    """
    Kaydedilmiş oturumdan kod üretir.

    JSON body:
      session_path — Oturum JSON dosya yolu (zorunlu)
      format       — playwright | cucumber | pom_python | pom_java | locators | all
      class_name   — POM sınıf adı (opsiyonel)
      feature_title — Cucumber feature başlığı (opsiyonel)

    Returns:
      {ok, code, format} veya {ok, files} (format=all ise)
    """
    try:
        from core.test_recorder import TestRecorder
        data         = request.get_json() or {}
        session_path = data.get("session_path", "")
        fmt          = data.get("format", "playwright")
        class_name   = data.get("class_name", "")
        feature_title = data.get("feature_title", "")

        if not session_path:
            return jsonify({"ok": False, "error": "session_path gerekli"}), 400

        p = Path(session_path)
        if not p.exists():
            return jsonify({"ok": False, "error": "Oturum dosyası bulunamadı"}), 404

        recorder = TestRecorder.load_session(p)

        if fmt == "playwright":
            code = recorder.to_playwright()
            return jsonify({"ok": True, "code": code, "format": "playwright"})

        elif fmt == "cucumber":
            code = recorder.to_cucumber(feature_title=feature_title)
            return jsonify({"ok": True, "code": code, "format": "cucumber"})

        elif fmt == "pom_python":
            code = recorder.to_pom_python()
            return jsonify({"ok": True, "code": code, "format": "pom_python"})

        elif fmt == "pom_java":
            code = recorder.to_pom_java()
            return jsonify({"ok": True, "code": code, "format": "pom_java"})

        elif fmt == "locators":
            locators = recorder.to_locators()
            return jsonify({"ok": True, "locators": locators, "format": "locators"})

        elif fmt == "pom_typescript":
            from core.pom_ts_generator import POMTypeScriptGenerator
            gen = POMTypeScriptGenerator()
            code = gen.from_session(recorder.session.to_dict(), class_name=class_name)
            return jsonify({"ok": True, "code": code, "format": "pom_typescript"})

        elif fmt == "all":
            files = recorder.save_all()
            return jsonify({"ok": True, "files": files, "format": "all"})

        else:
            return jsonify({"ok": False, "error": f"Bilinmeyen format: {fmt}"}), 400

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@recorder_bp.route("/api/recorder/generate/download", methods=["POST"])
def generate_and_download():
    """
    Kod üretir ve doğrudan dosya olarak indirir.

    JSON body:
      session_path — Oturum JSON dosyası
      format       — playwright | cucumber | pom_python | pom_java
    """
    try:
        from core.test_recorder import TestRecorder
        import tempfile

        data         = request.get_json() or {}
        session_path = data.get("session_path", "")
        fmt          = data.get("format", "playwright")

        if not session_path:
            return jsonify({"ok": False, "error": "session_path gerekli"}), 400

        p = Path(session_path)
        if not p.exists():
            return jsonify({"ok": False, "error": "Oturum dosyası bulunamadı"}), 404

        recorder = TestRecorder.load_session(p)
        ext_map  = {
            "playwright": (".py",      "text/x-python"),
            "cucumber":   (".feature", "text/plain"),
            "pom_python": (".py",      "text/x-python"),
            "pom_java":   (".java",    "text/x-java"),
            "locators":   (".json",    "application/json"),
        }
        ext, mime = ext_map.get(fmt, (".txt", "text/plain"))

        if fmt == "playwright":
            content = recorder.to_playwright()
        elif fmt == "cucumber":
            content = recorder.to_cucumber()
        elif fmt == "pom_python":
            content = recorder.to_pom_python()
        elif fmt == "pom_java":
            content = recorder.to_pom_java()
        elif fmt == "locators":
            content = json.dumps(recorder.to_locators(), indent=2, ensure_ascii=False)
        else:
            return jsonify({"ok": False, "error": f"Bilinmeyen format: {fmt}"}), 400

        # Geçici dosyaya yaz
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=ext, delete=False, encoding="utf-8"
        )
        tmp.write(content)
        tmp.flush()
        tmp.close()

        fname = f"{recorder.name}_{fmt}{ext}"
        return send_file(
            tmp.name,
            mimetype=mime,
            as_attachment=True,
            download_name=fname,
        )
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# Locator Yönetimi
# ──────────────────────────────────────────────────────────────────────────────
@recorder_bp.route("/api/recorder/locators/<domain>", methods=["GET"])
def list_locators(domain: str):
    """Domain'e ait mevcut locator dosyalarını listeler."""
    try:
        loc_dir = settings.BASE_DIR / "locators" / domain
        if not loc_dir.exists():
            return jsonify({"ok": True, "locators": [], "count": 0})

        files = []
        for f in sorted(loc_dir.glob("*_locators.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                files.append({
                    "file": f.name,
                    "path": str(f),
                    "element_count": len(data),
                })
            except Exception:
                continue

        return jsonify({"ok": True, "locators": files, "count": len(files)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@recorder_bp.route("/api/recorder/locators/<domain>/<path:filename>", methods=["GET"])
def get_locators(domain: str, filename: str):
    """Belirli bir locator dosyasının içeriğini döner."""
    try:
        loc_dir = settings.BASE_DIR / "locators" / domain
        target = (loc_dir / filename).resolve()
        if not str(target).startswith(str(loc_dir.resolve())):
            return jsonify({"ok": False, "error": "Geçersiz dosya yolu"}), 403

        if not target.exists():
            return jsonify({"ok": False, "error": "Dosya bulunamadı"}), 404

        data = json.loads(target.read_text(encoding="utf-8"))
        return jsonify({"ok": True, "locators": data, "file": filename})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
