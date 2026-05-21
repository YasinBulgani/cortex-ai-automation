from __future__ import annotations

"""
Accessibility (Erişilebilirlik) Test API Route'ları
=====================================================
WCAG 2.1 testleri için REST endpoint'leri.
"""
import json
import logging
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file

from config.settings import settings

logger = logging.getLogger(__name__)

a11y_bp = Blueprint("accessibility", __name__)


def _get_config() -> dict:
    """config/a11y_config.json dosyasını okur."""
    cfg_path = settings.BASE_DIR / "config" / "a11y_config.json"
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeError) as exc:
            logger.debug("a11y_config.json okunamadı: %s", exc)
    return {}


def _make_tester(config: dict | None = None):
    """AccessibilityTester örneği oluşturur."""
    from core.accessibility_tester import AccessibilityTester
    cfg = config or _get_config()
    return AccessibilityTester(
        wcag_level=cfg.get("wcag_level", "AA"),
        browser_type=cfg.get("browser_type", "chromium"),
        headless=cfg.get("headless", True),
        ignore_rules=cfg.get("ignore_rules", []),
        timeout=cfg.get("timeout", 30_000),
        use_axe=cfg.get("use_axe", False),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Test Endpoints
# ──────────────────────────────────────────────────────────────────────────────
@a11y_bp.route("/api/a11y/test", methods=["POST"])
def test_url():
    """
    Bir URL'yi erişilebilirlik açısından test eder.

    JSON body:
      url         — Test edilecek URL (zorunlu)
      wcag_level  — "AA" veya "AAA" (default: "AA")
      ignore_rules — Atlanacak kural ID'leri listesi
      use_axe     — axe-core kullan (bool, default: false)
      wait_for    — Bekleme CSS seçicisi
      wait_ms     — Ekstra bekleme süresi (default: 1000)

    Returns:
      {ok, result: {url, score, violations, warnings, passes, ...}}
    """
    try:
        data     = request.get_json() or {}
        url      = data.get("url", "").strip()
        if not url:
            return jsonify({"ok": False, "error": "url gerekli"}), 400

        wcag_level   = data.get("wcag_level", "AA").upper()
        ignore_rules = data.get("ignore_rules", [])
        use_axe      = data.get("use_axe", False)
        wait_for     = data.get("wait_for")
        wait_ms      = int(data.get("wait_ms", 1000))

        tester = _make_tester({
            "wcag_level":   wcag_level,
            "ignore_rules": ignore_rules,
            "use_axe":      use_axe,
        })
        result = tester.test_url(url, wait_for=wait_for, wait_ms=wait_ms)

        if result.error:
            return jsonify({"ok": False, "error": result.error, "result": tester.to_dict(result)}), 500

        return jsonify({"ok": True, "result": tester.to_dict(result)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@a11y_bp.route("/api/a11y/test/batch", methods=["POST"])
def test_batch():
    """
    Birden fazla URL'yi erişilebilirlik açısından test eder.

    JSON body:
      urls        — URL listesi (zorunlu)
      wcag_level  — "AA" veya "AAA"
      ignore_rules — Atlanacak kural ID'leri
    """
    try:
        data         = request.get_json() or {}
        urls         = data.get("urls", [])
        wcag_level   = data.get("wcag_level", "AA").upper()
        ignore_rules = data.get("ignore_rules", [])

        if not urls:
            return jsonify({"ok": False, "error": "urls listesi gerekli"}), 400

        tester = _make_tester({"wcag_level": wcag_level, "ignore_rules": ignore_rules})
        results = []
        for url in urls:
            r = tester.test_url(url.strip())
            results.append(tester.to_dict(r))

        avg_score = sum(r["score"] for r in results) / len(results) if results else 0
        total_violations = sum(r["violation_count"] for r in results)

        return jsonify({
            "ok": True,
            "summary": {
                "tested": len(results),
                "avg_score": round(avg_score, 2),
                "total_violations": total_violations,
            },
            "results": results,
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# Rapor Endpoints
# ──────────────────────────────────────────────────────────────────────────────
@a11y_bp.route("/api/a11y/report", methods=["POST"])
def generate_report():
    """
    Bir URL için erişilebilirlik testi yapar ve HTML rapor üretir.

    JSON body:
      url         — Test edilecek URL (zorunlu)
      wcag_level  — "AA" veya "AAA"
      include_warnings — Uyarıları rapora dahil et (bool)

    Returns:
      {ok, report_path, result_summary}
    """
    try:
        data     = request.get_json() or {}
        url      = data.get("url", "").strip()
        if not url:
            return jsonify({"ok": False, "error": "url gerekli"}), 400

        wcag_level       = data.get("wcag_level", "AA").upper()
        include_warnings = data.get("include_warnings", True)

        tester = _make_tester({"wcag_level": wcag_level})
        result = tester.test_url(url)
        report_path = tester.generate_report(result, include_warnings=include_warnings)

        return jsonify({
            "ok": True,
            "report_path": report_path,
            "result": tester.to_dict(result),
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@a11y_bp.route("/api/a11y/report/download", methods=["GET"])
def download_report():
    """
    Önceden oluşturulmuş raporu indirir.

    Query params:
      path — Rapor dosyasının mutlak yolu
    """
    try:
        report_path = request.args.get("path", "")
        if not report_path:
            return jsonify({"ok": False, "error": "path parametresi gerekli"}), 400

        p = Path(report_path)
        if not p.exists() or not p.is_file():
            return jsonify({"ok": False, "error": "Rapor dosyası bulunamadı"}), 404

        # Güvenlik: sadece reports dizini altındaki dosyalara izin ver
        try:
            p.relative_to(settings.BASE_DIR)
        except ValueError:
            return jsonify({"ok": False, "error": "Geçersiz dosya yolu"}), 403

        return send_file(str(p), mimetype="text/html", download_name=p.name)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# Kural Bilgisi
# ──────────────────────────────────────────────────────────────────────────────
@a11y_bp.route("/api/a11y/rules", methods=["GET"])
def list_rules():
    """Desteklenen WCAG kurallarını listeler."""
    try:
        from core.accessibility_tester import WCAG_RULES
        rules = [
            {
                "id": rule_id,
                "description": info["description"],
                "wcag_criteria": info["wcag"],
                "severity": info["severity"],
                "weight": info["weight"],
                "help_url": info["help_url"],
            }
            for rule_id, info in WCAG_RULES.items()
        ]
        return jsonify({"ok": True, "rules": rules, "count": len(rules)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@a11y_bp.route("/api/a11y/config", methods=["GET"])
def get_config():
    """Mevcut erişilebilirlik konfigürasyonunu döner."""
    return jsonify({"ok": True, "config": _get_config()})


@a11y_bp.route("/api/a11y/config", methods=["PUT"])
def update_config():
    """
    Erişilebilirlik konfigürasyonunu günceller.

    JSON body: konfigürasyon alanları
    """
    try:
        new_cfg = request.get_json() or {}
        cfg_path = settings.BASE_DIR / "config" / "a11y_config.json"
        cfg_path.parent.mkdir(exist_ok=True)

        # Mevcut config ile birleştir
        current = _get_config()
        current.update(new_cfg)
        cfg_path.write_text(
            json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return jsonify({"ok": True, "config": current})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
