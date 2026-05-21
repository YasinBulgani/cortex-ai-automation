"""
Playback API Route'ları
========================
Kaydedilmiş oturumları oynatma ve rapor endpoint'leri.
"""
import json
from pathlib import Path
from flask import Blueprint, request, jsonify

from config.settings import settings

playback_bp = Blueprint("playback", __name__)


@playback_bp.route("/api/playback/replay", methods=["POST"])
def replay_session():
    """
    Kaydedilmiş oturumu Playwright ile oynatır.

    JSON body:
      session_path — Oturum JSON dosya yolu (zorunlu)
      headless     — Tarayıcı headless modu (default: true)
      timeout      — Element bekleme timeout ms (default: 10000)
      browser      — chromium | firefox | webkit (default: chromium)

    Returns:
      {ok, report: PlaybackReport}
    """
    try:
        data = request.get_json() or {}
        session_path = data.get("session_path", "")
        headless = data.get("headless", True)
        timeout = data.get("timeout", 10_000)
        browser_type = data.get("browser", "chromium")

        if not session_path:
            return jsonify({"ok": False, "error": "session_path gerekli"}), 400

        p = Path(session_path)
        if not p.exists():
            return jsonify({"ok": False, "error": "Oturum dosyası bulunamadı"}), 404

        from playwright.sync_api import sync_playwright
        from core.playback_engine import PlaybackEngine

        with sync_playwright() as pw:
            launcher = getattr(pw, browser_type, pw.chromium)
            browser = launcher.launch(headless=headless)
            page = browser.new_page()

            engine = PlaybackEngine(page, timeout=timeout)
            report = engine.replay_from_file(p)
            report_path = engine.save_report()

            browser.close()

        return jsonify({
            "ok": True,
            "report": report.to_dict(),
            "report_path": report_path,
            "summary": engine.summary(),
        })

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@playback_bp.route("/api/playback/replay-events", methods=["POST"])
def replay_events():
    """
    Doğrudan event listesi ile oynatma.

    JSON body:
      events       — RecordingEvent dict listesi (zorunlu)
      session_id   — Oturum ID (opsiyonel)
      base_url     — Başlangıç URL (opsiyonel)
      headless     — Tarayıcı headless modu (default: true)
      timeout      — Element bekleme timeout ms (default: 10000)

    Returns:
      {ok, report: PlaybackReport}
    """
    try:
        data = request.get_json() or {}
        events = data.get("events", [])
        session_id = data.get("session_id", "inline")
        base_url = data.get("base_url", "")
        headless = data.get("headless", True)
        timeout = data.get("timeout", 10_000)

        if not events:
            return jsonify({"ok": False, "error": "events gerekli"}), 400

        from playwright.sync_api import sync_playwright
        from core.playback_engine import PlaybackEngine

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless)
            page = browser.new_page()

            if base_url:
                page.goto(base_url, wait_until="domcontentloaded")

            engine = PlaybackEngine(page, timeout=timeout)
            report = engine.replay(events, session_id=session_id)
            report_path = engine.save_report()

            browser.close()

        return jsonify({
            "ok": True,
            "report": report.to_dict(),
            "report_path": report_path,
            "summary": engine.summary(),
        })

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@playback_bp.route("/api/playback/reports", methods=["GET"])
def list_reports():
    """Playback raporlarını listeler."""
    try:
        reports_dir = settings.BASE_DIR / "reports" / "playback"
        reports_dir.mkdir(parents=True, exist_ok=True)

        reports = []
        for f in sorted(reports_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                reports.append({
                    "file": f.name,
                    "path": str(f),
                    "session_id": data.get("session_id", ""),
                    "total": data.get("total", 0),
                    "passed": data.get("passed", 0),
                    "failed": data.get("failed", 0),
                    "healed": data.get("healed", 0),
                    "pass_rate": data.get("pass_rate", 0),
                    "started_at": data.get("started_at", ""),
                })
            except Exception:
                continue

        return jsonify({"ok": True, "reports": reports, "count": len(reports)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@playback_bp.route("/api/playback/reports/<path:filename>", methods=["GET"])
def get_report(filename: str):
    """Belirli bir playback raporunu döner."""
    try:
        reports_dir = settings.BASE_DIR / "reports" / "playback"
        target = (reports_dir / filename).resolve()
        if not str(target).startswith(str(reports_dir.resolve())):
            return jsonify({"ok": False, "error": "Geçersiz dosya yolu"}), 403

        if not target.exists():
            return jsonify({"ok": False, "error": "Rapor bulunamadı"}), 404

        data = json.loads(target.read_text(encoding="utf-8"))
        return jsonify({"ok": True, "report": data})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
