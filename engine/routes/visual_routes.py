"""
Visual Regression API Route'ları
==================================
Baseline yönetimi ve görsel karşılaştırma için REST endpoint'leri.
"""
import json
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file, session

from config.settings import settings

visual_bp = Blueprint("visual", __name__)

# ── Lazy import: Pillow/numpy olmadan da çalışabilsin ──────────────────────
def _get_config() -> dict:
    """config/visual_config.json dosyasını okur."""
    cfg_path = settings.BASE_DIR / "config" / "visual_config.json"
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _make_tester(domain: str = "default"):
    """VisualRegressionTester örneği oluşturur."""
    from core.visual_regression import create_visual_tester
    cfg = _get_config()
    domain_cfg = cfg.get("domains", {}).get(domain, cfg)
    return create_visual_tester(domain=domain, config=domain_cfg)


# ──────────────────────────────────────────────────────────────────────────────
# Baseline Endpoints
# ──────────────────────────────────────────────────────────────────────────────
@visual_bp.route("/api/visual/baselines", methods=["GET"])
def list_baselines():
    """
    Tüm baseline'ları veya belirli domain'e ait olanları listeler.

    Query params:
      domain — Filtre için domain adı (opsiyonel)
    """
    try:
        from core.visual_regression import BaselineManager
        cfg = _get_config()
        mgr = BaselineManager(cfg.get("baselines_dir"))
        domain = request.args.get("domain")
        baselines = mgr.list_baselines(domain=domain)
        return jsonify({"ok": True, "baselines": baselines, "count": len(baselines)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@visual_bp.route("/api/visual/baselines/<domain>/<path:test_name>", methods=["GET"])
def get_baseline(domain: str, test_name: str):
    """Belirli bir baseline'ın meta verisini döner."""
    try:
        from core.visual_regression import BaselineManager
        cfg = _get_config()
        mgr = BaselineManager(cfg.get("baselines_dir"))
        entry = mgr.get_baseline(domain, test_name)
        if not entry:
            return jsonify({"ok": False, "error": "Baseline bulunamadı"}), 404
        return jsonify({"ok": True, "baseline": entry})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@visual_bp.route("/api/visual/baselines/<domain>/<path:test_name>", methods=["DELETE"])
def delete_baseline(domain: str, test_name: str):
    """Bir baseline'ı siler."""
    try:
        from core.visual_regression import BaselineManager
        cfg = _get_config()
        mgr = BaselineManager(cfg.get("baselines_dir"))
        deleted = mgr.delete_baseline(domain, test_name)
        if not deleted:
            return jsonify({"ok": False, "error": "Baseline bulunamadı"}), 404
        return jsonify({"ok": True, "message": "Baseline silindi"})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@visual_bp.route("/api/visual/baselines/upload", methods=["POST"])
def upload_baseline():
    """
    Screenshot dosyasını baseline olarak yükler.

    Form data:
      file   — PNG/JPEG dosyası
      domain — Domain adı
      test_name — Test adı
    """
    try:
        from core.visual_regression import BaselineManager
        if "file" not in request.files:
            return jsonify({"ok": False, "error": "Dosya gerekli (file field)"}), 400

        f = request.files["file"]
        domain    = request.form.get("domain", "default")
        test_name = request.form.get("test_name", "")

        if not test_name:
            return jsonify({"ok": False, "error": "test_name gerekli"}), 400

        # Geçici kayıt
        tmp_dir = settings.SCREENSHOTS_DIR / "uploads"
        tmp_dir.mkdir(exist_ok=True)
        tmp_path = tmp_dir / f"upload_{domain}_{test_name}.png"
        f.save(str(tmp_path))

        cfg = _get_config()
        mgr = BaselineManager(cfg.get("baselines_dir"))
        entry = mgr.save_baseline(tmp_path, domain, test_name)
        tmp_path.unlink(missing_ok=True)

        return jsonify({"ok": True, "baseline": entry})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# Karşılaştırma Endpoints
# ──────────────────────────────────────────────────────────────────────────────
@visual_bp.route("/api/visual/compare", methods=["POST"])
def compare_visual():
    """
    Görsel karşılaştırma yapar.

    JSON body:
      test_name      — Test adı (zorunlu)
      domain         — Domain adı
      url            — Screenshot alınacak URL (Playwright gerekir)
      update_baseline — True ise sonucu baseline olarak kaydeder
      threshold      — SSIM eşiği (0-1, default: 0.95)
      ignore_regions  — Maskelenecek bölgeler [{x,y,w,h}, ...]
    """
    try:
        data       = request.get_json() or {}
        test_name  = data.get("test_name")
        domain     = data.get("domain", "default")
        url        = data.get("url")
        update_bl  = data.get("update_baseline", False)
        threshold  = data.get("threshold")
        ignores    = data.get("ignore_regions", [])

        if not test_name:
            return jsonify({"ok": False, "error": "test_name gerekli"}), 400
        if not url and not update_bl:
            return jsonify({"ok": False, "error": "url gerekli (Playwright gerekir)"}), 400

        cfg = _get_config()
        if threshold is not None:
            cfg["threshold"] = threshold

        tester = _make_tester(domain)
        result = tester.compare(
            test_name=test_name,
            url=url,
            update_baseline=update_bl,
            ignore_regions=ignores,
        )
        return jsonify({"ok": True, "result": result})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@visual_bp.route("/api/visual/compare/upload", methods=["POST"])
def compare_with_upload():
    """
    Yüklenen screenshot ile baseline karşılaştırır.

    Form data:
      file       — PNG dosyası
      test_name  — Test adı
      domain     — Domain adı
      threshold  — SSIM eşiği (opsiyonel)
    """
    try:
        from core.visual_regression import BaselineManager, VisualRegressionTester, SSIMCalculator
        if "file" not in request.files:
            return jsonify({"ok": False, "error": "Dosya gerekli"}), 400

        f          = request.files["file"]
        test_name  = request.form.get("test_name", "")
        domain     = request.form.get("domain", "default")
        threshold  = float(request.form.get("threshold", 0.95))

        if not test_name:
            return jsonify({"ok": False, "error": "test_name gerekli"}), 400

        # Geçici kayıt
        tmp_dir = settings.SCREENSHOTS_DIR / "uploads"
        tmp_dir.mkdir(exist_ok=True)
        tmp_path = tmp_dir / f"cmp_{domain}_{test_name}.png"
        f.save(str(tmp_path))

        tester = _make_tester(domain)
        tester.threshold = threshold
        result = tester.compare(
            test_name=test_name,
            screenshot_path=tmp_path,
        )
        tmp_path.unlink(missing_ok=True)
        return jsonify({"ok": True, "result": result})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@visual_bp.route("/api/visual/batch", methods=["POST"])
def batch_compare():
    """
    Toplu görsel karşılaştırma.

    JSON body:
      domain      — Domain adı
      test_cases  — [{test_name, url, ...}, ...]
      threshold   — SSIM eşiği
    """
    try:
        data       = request.get_json() or {}
        domain     = data.get("domain", "default")
        test_cases = data.get("test_cases", [])
        threshold  = data.get("threshold")

        if not test_cases:
            return jsonify({"ok": False, "error": "test_cases listesi gerekli"}), 400

        cfg = _get_config()
        if threshold is not None:
            cfg["threshold"] = threshold

        tester = _make_tester(domain)
        batch_result = tester.batch_test(test_cases)

        # HTML rapor oluştur
        report_path = tester.generate_report(batch_result)
        batch_result["report_path"] = report_path

        return jsonify({"ok": True, "result": batch_result})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# Diff Görüntüsü
# ──────────────────────────────────────────────────────────────────────────────
@visual_bp.route("/api/visual/diff-image", methods=["POST"])
def create_diff_image():
    """
    İki yüklenen görüntü arasındaki fark görüntüsünü üretir.

    Form data:
      baseline — Baseline PNG
      current  — Güncel PNG
    """
    try:
        from core.visual_regression import PixelDiffVisualizer
        if "baseline" not in request.files or "current" not in request.files:
            return jsonify({"ok": False, "error": "baseline ve current dosyaları gerekli"}), 400

        tmp_dir = settings.SCREENSHOTS_DIR / "uploads"
        tmp_dir.mkdir(exist_ok=True)

        bl_path  = tmp_dir / "diff_baseline.png"
        cur_path = tmp_dir / "diff_current.png"
        out_path = tmp_dir / "diff_output.png"

        request.files["baseline"].save(str(bl_path))
        request.files["current"].save(str(cur_path))

        diff_info = PixelDiffVisualizer.create_diff_image(bl_path, cur_path, out_path)

        if Path(out_path).exists():
            return send_file(str(out_path), mimetype="image/png",
                             download_name="diff.png")
        return jsonify({"ok": False, "error": "Diff görüntüsü üretilemedi"}), 500
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
