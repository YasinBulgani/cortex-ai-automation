from __future__ import annotations

"""
Manuel Test → Otomasyon Pipeline Orchestration

Tek endpoint ile tüm zinciri çalıştırır:
  1. Manuel test adımlarını DB'den çeker
  2. AIEngine ile Gherkin feature üretir (AI yoksa mock döner)
  3. Playwright pytest kodu üretir
  4. .feature dosyasını diske kaydeder
  5. auto_run=true ise runner'ı tetikler, Allure linki döner
  6. Tüm çıktıları tek response'da döner

Endpointler:
  POST /api/pipeline/manual-to-automation         — tam zincir
  POST /api/pipeline/manual-to-automation/preview — kayıtsız Gherkin taslağı
"""

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request, jsonify

from core.db import get_manual_tests, create_pipeline_run, complete_pipeline_run, list_pipeline_runs
from config.settings import settings

pipeline_bp = Blueprint("pipeline", __name__, url_prefix="/api/pipeline")

# Üretilen dosyaların kaydedileceği dizinler
FEATURES_DIR = Path(__file__).parent.parent / "features" / "generated"
TESTS_DIR    = Path(__file__).parent.parent / "tests"   / "generated"
STEPS_DIR    = Path(__file__).parent.parent / "steps"   / "generated"
ENGINE_ROOT  = Path(__file__).parent.parent


# ── Yardımcılar ───────────────────────────────────────────────────────────────

def _slug(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_]+", "_", s)
    return s[:50]


def _get_test_by_id(test_id: int) -> dict | None:
    for t in get_manual_tests():
        if t["id"] == test_id:
            return t
    return None


def _steps_to_requirements(steps: list[dict]) -> str:
    lines = []
    for i, s in enumerate(steps, 1):
        lines.append(f"Adım {i}: {s.get('action', '')}")
        lines.append(f"  Beklenen sonuç: {s.get('expected', '')}")
    return "\n".join(lines)


def _has_ai_key() -> bool:
    """Geçerli bir AI API anahtarı tanımlı mı?"""
    openai_key = getattr(settings, "OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    anthropic_key = getattr(settings, "ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    # Placeholder değerleri dışla
    placeholders = {"", "sk-...", "your-key-here", "changeme", "YOUR_KEY"}
    real_openai = openai_key not in placeholders and len(openai_key) > 10
    real_anthropic = anthropic_key not in placeholders and len(anthropic_key) > 10
    return real_openai or real_anthropic


def _mock_gherkin(title: str, steps: list[dict]) -> str:
    """AI anahtarı olmadığında şablon Gherkin döner."""
    lines = [
        "# language: tr",
        f"Feature: {title}",
        f"  # [MOCK — AI anahtarı yapılandırılmamış]",
        "",
        f"  @smoke @generated",
        f"  Scenario: {title} senaryosu",
    ]
    if steps:
        action0 = steps[0].get("action", "İlk adım")
        lines.append(f"    Given kullanıcı ana sayfadadır")
        for s in steps:
            action = s.get("action", "aksiyon").strip()
            expected = s.get("expected", "beklenen sonuç").strip()
            lines.append(f"    When kullanıcı \"{action}\" işlemini yapar")
            lines.append(f"    Then \"{expected}\" gerçekleşmeli")
    else:
        lines += [
            "    Given kullanıcı ana sayfadadır",
            "    When kullanıcı gerekli adımı yapar",
            "    Then beklenen sonuç gerçekleşir",
        ]
    return "\n".join(lines)


def _normalize_gherkin_content(raw_content: str, title: str) -> str:
    content = (raw_content or "").replace("\r\n", "\n").strip()
    if not content:
        return _mock_gherkin(title, [])

    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    feature_match = re.search(r"(?im)^(feature:.*)$", content)
    if feature_match:
        content = content[feature_match.start():].strip()

    lines = [line.rstrip() for line in content.splitlines()]
    normalized: list[str] = []
    feature_seen = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if normalized and normalized[-1] != "":
                normalized.append("")
            continue

        lowered = line.lower()
        if lowered.startswith("feature:"):
            if feature_seen:
                continue
            feature_seen = True
            normalized.append(f"Feature: {line.split(':', 1)[1].strip() or title}")
            continue
        if lowered.startswith("scenario:"):
            normalized.append(f"  Scenario: {line.split(':', 1)[1].strip() or title}")
            continue
        if re.match(r"^(given|when|then|and|but)\b", line, re.IGNORECASE):
            keyword, rest = line.split(maxsplit=1)
            normalized.append(f"    {keyword.title()} {rest.strip()}")
            continue
        if line.startswith("@"):
            normalized.append(f"  {line}")
            continue
        if line.startswith("#"):
            normalized.append(line)
            continue

    if not any(line.lower().startswith("feature:") for line in normalized):
        normalized.insert(0, f"Feature: {title}")
    if not any(line.lstrip().lower().startswith("scenario:") for line in normalized):
        normalized.extend(["", f"  Scenario: {title}", "    Given kullanıcı ana sayfadadır"])
    if not any(line.startswith("# language:") for line in normalized):
        normalized.insert(0, "# language: tr")

    cleaned: list[str] = []
    previous_blank = False
    for line in normalized:
        is_blank = line == ""
        if is_blank and previous_blank:
            continue
        cleaned.append(line)
        previous_blank = is_blank

    return "\n".join(cleaned).strip() + "\n"


def _mock_playwright(title: str, steps: list[dict], target_url: str = "") -> str:
    """AI anahtarı olmadığında şablon Playwright kodu döner."""
    slug = _slug(title)
    url = target_url or "http://localhost"
    lines = [
        "# [MOCK — AI anahtarı yapılandırılmamış]",
        "# Gerçek kod üretimi için OPENAI_API_KEY veya ANTHROPIC_API_KEY ekleyin.",
        "import pytest",
        "from playwright.sync_api import Page",
        "",
        "",
        f"def test_{slug}(page: Page):",
        f'    """Auto-generated stub for: {title}"""',
        f"    page.goto(\"{url}\")",
    ]
    for i, s in enumerate(steps, 1):
        action = s.get("action", "").strip().replace('"', '\\"')
        expected = s.get("expected", "").strip().replace('"', '\\"')
        lines.append(f"    # Adım {i}: {action}")
        lines.append(f"    # Beklenen: {expected}")
        lines.append(f"    page.wait_for_timeout(500)  # TODO: gerçek selector ekle")
    lines += [
        "",
        "    # TODO: Assertions buraya",
        "    assert page.url is not None",
    ]
    return "\n".join(lines)


def _run_feature(feature_path: str) -> dict:
    """
    pytest-bdd ile feature dosyasını çalıştırır.
    Allure raporu /engine/reports/allure-results/ altına yazar.
    """
    allure_dir = ENGINE_ROOT / "allure-results"
    allure_dir.mkdir(parents=True, exist_ok=True)

    abs_path = ENGINE_ROOT / feature_path if not Path(feature_path).is_absolute() else Path(feature_path)

    python_exe = sys.executable
    cmd = [
        python_exe, "-m", "pytest",
        str(abs_path),
        "--alluredir", str(allure_dir),
        "--tb=short",
        "-q",
        "--timeout=60",
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(ENGINE_ROOT),
        )
        passed = proc.returncode == 0
        output = (proc.stdout + proc.stderr).strip()
        return {
            "ok": passed,
            "exit_code": proc.returncode,
            "output": output[:4000],  # limit
            "allure_results_dir": str(allure_dir),
            "allure_report_url": "/api/reports/allure",
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "Test zaman aşımına uğradı (>120s)", "exit_code": -1}
    except Exception as exc:
        return {"ok": False, "output": str(exc), "exit_code": -1}


# ── Ana Pipeline Endpoint ─────────────────────────────────────────────────────

@pipeline_bp.route("/manual-to-automation", methods=["POST"])
def manual_to_automation():
    """
    Manuel test → Gherkin BDD + Playwright kodu tek seferde üretir.

    Girdi (JSON):
      test_id     (int, zorunlu)   — manual_tests tablosundaki kayıt ID'si
      target_url  (str, opsiyonel) — Playwright locator tespiti için hedef URL
      framework   (str, opsiyonel) — "playwright" (default) veya "selenium"
      auto_run    (bool, opsiyonel)— true ise kod üretilince otomatik çalıştırır

    Çıktı (JSON):
      ok            bool
      mock_mode     bool   — AI anahtarı yoksa true, çıktılar placeholder
      test_title    str
      steps_count   int
      gherkin       str
      playwright_code str
      feature_path  str
      locators      dict   (opsiyonel)
      run_result    dict   (auto_run=true ise)
      error         str    (sadece ok=false)
    """
    data = request.get_json(silent=True) or {}

    # Girdi doğrulama
    test_id = data.get("test_id")
    if not test_id:
        return jsonify({"ok": False, "error": "test_id zorunludur"}), 400
    try:
        test_id = int(test_id)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "test_id geçerli bir tam sayı olmalıdır"}), 400

    target_url: str = (data.get("target_url") or "").strip()
    auto_run: bool = bool(data.get("auto_run", False))
    project_id = data.get("project_id")  # opsiyonel — gelecekte proje scope'u için
    use_mock = not _has_ai_key()

    # DB'den manuel test kaydını çek
    test = _get_test_by_id(test_id)
    if not test:
        return jsonify({"ok": False, "error": f"test_id={test_id} bulunamadı"}), 404

    steps: list[dict] = test.get("steps", [])
    if not steps:
        return jsonify({"ok": False, "error": "Bu test için henüz adım eklenmemiş"}), 422

    title: str = test.get("title", f"test_{test_id}")
    result: dict = {
        "ok": True,
        "mock_mode": use_mock,
        "project_id": project_id,
        "test_title": title,
        "steps_count": len(steps),
        "gherkin": "",
        "playwright_code": "",
        "feature_path": "",
    }

    # ── Gherkin üret ──────────────────────────────────────────────────────────
    if use_mock:
        result["gherkin"] = _mock_gherkin(title, steps)
        result["playwright_code"] = _mock_playwright(title, steps, target_url)
    else:
        requirements = f"Test Başlığı: {title}\n\n{_steps_to_requirements(steps)}"
        try:
            from core.ai_engine import AIEngine
            ai = AIEngine()
            result["gherkin"] = ai.generate_gherkin(
                requirements=requirements,
                target_url=target_url or None,
            )
        except Exception as exc:
            return jsonify({"ok": False, "error": f"Gherkin üretimi başarısız: {exc}"}), 500

        try:
            task_line = next(
                (l.strip() for l in result["gherkin"].splitlines() if l.strip().startswith("Scenario")),
                title,
            )
            from core.ai_engine import AIEngine
            ai = AIEngine()
            result["playwright_code"] = ai.generate_test_file(
                url=target_url or "http://localhost",
                task=task_line,
                test_name=_slug(title),
            )
        except Exception as exc:
            result["playwright_code"] = f"# Kod üretimi başarısız: {exc}"

    result["gherkin"] = _normalize_gherkin_content(result.get("gherkin", ""), title)

    # ── AI Kod İncelemesi ─────────────────────────────────────────────────────
    result["code_review"] = None
    code_review_requested = data.get("code_review", True)
    if code_review_requested and result.get("playwright_code") and not result["playwright_code"].startswith("#"):
        try:
            from services import get_llm_gateway
            gw = get_llm_gateway()
            if gw.available:
                review_prompt = f"""You are an expert Playwright test reviewer. Review this generated test code for correctness, completeness, and potential issues.

Test Title: {title}
Gherkin Feature:
{result.get("gherkin", "")[:500]}

Playwright Code:
{result["playwright_code"][:1500]}

Respond ONLY with valid JSON (no markdown):
{{
  "score": 0-100,
  "issues": [
    {{"severity": "error|warning|info", "message": "description", "line_hint": "optional"}}
  ],
  "suggestions": ["improvement 1", "improvement 2"],
  "approved": true or false,
  "summary": "one sentence review summary"
}}"""
                raw = gw.complete(review_prompt, max_tokens=600)
                clean = raw.strip()
                if clean.startswith("```"):
                    clean = "\n".join(clean.split("\n")[1:])
                if clean.endswith("```"):
                    clean = "\n".join(clean.split("\n")[:-1])
                import json as _json
                result["code_review"] = _json.loads(clean.strip())
        except Exception as rev_exc:
            result["code_review"] = {"score": None, "summary": f"İnceleme yapılamadı: {rev_exc}", "approved": True, "issues": [], "suggestions": []}

    # ── .feature dosyasını kaydet ─────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slug(title)
    try:
        FEATURES_DIR.mkdir(parents=True, exist_ok=True)
        feature_abs = FEATURES_DIR / f"{slug}_{ts}.feature"
        feature_abs.write_text(result["gherkin"], encoding="utf-8")
        result["feature_path"] = str(feature_abs.relative_to(ENGINE_ROOT))
    except Exception as exc:
        result["feature_path"] = f"(kayıt başarısız: {exc})"

    # ── Playwright .py dosyasını kaydet ──────────────────────────────────────
    try:
        TESTS_DIR.mkdir(parents=True, exist_ok=True)
        test_abs = TESTS_DIR / f"test_{slug}_{ts}.py"
        test_abs.write_text(result["playwright_code"], encoding="utf-8")
        result["test_path"] = str(test_abs.relative_to(ENGINE_ROOT))
    except Exception as exc:
        result["test_path"] = f"(kayıt başarısız: {exc})"

    # ── StepDefinitionMapper — yeni adımlar için step dosyası üret ────────────
    try:
        from core.ai_bdd.step_mapper import StepDefinitionMapper
        mapper = StepDefinitionMapper()
        mappings = mapper.map_feature(result["gherkin"])
        new_steps = [m for m in mappings if m.is_new]
        if new_steps:
            STEPS_DIR.mkdir(parents=True, exist_ok=True)
            step_file = STEPS_DIR / f"steps_{slug}_{ts}.py"
            lines = [
                "# Auto-generated step definitions",
                "# Implement the stubs below before running the feature file.",
                "from pytest_bdd import given, when, then",
                "",
            ]
            for m in new_steps:
                lines.append(m.suggested_code)
            step_file.write_text("\n".join(lines), encoding="utf-8")
            result["step_definitions_path"] = str(step_file.relative_to(ENGINE_ROOT))
            result["new_steps_count"] = len(new_steps)
        else:
            result["new_steps_count"] = 0
    except Exception as exc:
        result["step_definitions_path"] = f"(step mapper hatası: {exc})"

    # ── Locator tespiti (target_url varsa, sadece gerçek AI modunda) ──────────
    if target_url and not use_mock:
        try:
            from core.browser import BrowserEngine
            from core.page_inspector import PageInspector
            browser = BrowserEngine()
            browser.start()
            browser.page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
            inspector = PageInspector(browser.page)
            result["locators"] = inspector.get_interactive_elements()
            browser.stop()
        except Exception as exc:
            result["locators"] = {"error": f"Locator tespiti başarısız: {exc}"}
    elif target_url and use_mock:
        result["locators"] = {"mock": True, "note": "AI anahtarı olmadan locator tespiti yapılmadı"}

    # ── Koşu kaydı oluştur ve otomatik çalıştır ──────────────────────────────
    if auto_run:
        run_db_id = create_pipeline_run(
            project_id=int(project_id) if project_id else None,
            test_id=test_id,
            test_title=title,
            feature_path=result["feature_path"],
            mock_mode=use_mock,
        )
        if result["feature_path"] and not result["feature_path"].startswith("("):
            run_result = _run_feature(result["feature_path"])
            result["run_result"] = run_result
            status = "passed" if run_result.get("ok") else "failed"
            complete_pipeline_run(run_db_id, status, run_result.get("allure_results_dir", ""))
        else:
            result["run_result"] = {"ok": False, "output": "Feature dosyası kaydedilemedi, çalıştırılamadı"}
            complete_pipeline_run(run_db_id, "error")
        result["run_id"] = run_db_id

    return jsonify(result)


# ── Koşu Geçmişi Endpoint ─────────────────────────────────────────────────────

@pipeline_bp.route("/manual-to-automation/runs", methods=["GET"])
def list_runs():
    """
    Son koşuları listeler.

    Query params:
      project_id (int, opsiyonel) — proje filtresi
      limit      (int, opsiyonel) — maks kayıt (default 50)
    """
    project_id = request.args.get("project_id")
    limit = min(int(request.args.get("limit", 50)), 200)
    try:
        project_id_int = int(project_id) if project_id else None
    except (TypeError, ValueError):
        project_id_int = None
    runs = list_pipeline_runs(project_id=project_id_int, limit=limit)
    return jsonify({"runs": runs, "total": len(runs)})


# ── Önizleme Endpoint ─────────────────────────────────────────────────────────

@pipeline_bp.route("/manual-to-automation/preview", methods=["POST"])
def preview_gherkin():
    """
    Adımları kaydetmeden önce Gherkin önizleme üretir.

    Girdi (JSON):
      title  (str)        — Test başlığı
      steps  (list[dict]) — [{"action": "...", "expected": "..."}]
    """
    data = request.get_json(silent=True) or {}
    title = data.get("title", "Önizleme Testi")
    steps = data.get("steps", [])

    if not steps:
        return jsonify({"ok": False, "error": "steps listesi boş olamaz"}), 400

    use_mock = not _has_ai_key()

    if use_mock:
        gherkin = _mock_gherkin(title, steps)
        return jsonify({"ok": True, "gherkin": gherkin, "mock_mode": True})

    requirements = f"Test Başlığı: {title}\n\n{_steps_to_requirements(steps)}"
    try:
        from core.ai_engine import AIEngine
        ai = AIEngine()
        gherkin = ai.generate_gherkin(requirements=requirements)
        return jsonify({"ok": True, "gherkin": gherkin, "mock_mode": False})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
