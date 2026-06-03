"""
Pipeline routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/pipeline_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/pipeline.py — APIRouter, port 8000 (consolidated)

Bu pattern her route file için takip edilir. Bir Python developer kopyala-yapıştır + dönüştür yapar.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/pipeline", tags=["engine", "pipeline"])

# Üretilen dosyaların kaydedileceği dizinler
_ENGINE_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent / "engine"
FEATURES_DIR = _ENGINE_ROOT / "features" / "generated"
TESTS_DIR    = _ENGINE_ROOT / "tests"    / "generated"
STEPS_DIR    = _ENGINE_ROOT / "steps"    / "generated"


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ManualToAutomationRequest(BaseModel):
    test_id: int
    target_url: str = ""
    framework: str = "playwright"
    auto_run: bool = False
    allow_mock: bool = True
    code_review: bool = True
    project_id: Optional[int] = None


class PreviewGherkinRequest(BaseModel):
    title: str = "Önizleme Testi"
    steps: list[dict] = Field(default_factory=list)
    allow_mock: bool = True


# ─── Yardımcılar ─────────────────────────────────────────────────────────────

def _slug(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_]+", "_", s)
    return s[:50]


def _get_test_by_id(test_id: int) -> dict | None:
    from core.db import get_manual_tests
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
    try:
        from config.settings import settings
        openai_key = getattr(settings, "OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
        anthropic_key = getattr(settings, "ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    except Exception:
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    placeholders = {"", "sk-...", "your-key-here", "changeme", "YOUR_KEY"}
    real_openai = openai_key not in placeholders and len(openai_key) > 10
    real_anthropic = anthropic_key not in placeholders and len(anthropic_key) > 10
    return real_openai or real_anthropic


def _resolve_provenance(*, simulated: bool = False, fallback: bool = False, stub: bool = False) -> str:
    if stub:
        return "stub"
    if fallback:
        return "fallback"
    if simulated:
        return "simulated"
    return "real"


def _mock_gherkin(title: str, steps: list[dict]) -> str:
    """AI anahtarı olmadığında şablon Gherkin döner."""
    lines = [
        "# language: tr",
        f"Feature: {title}",
        "  # [MOCK — AI anahtarı yapılandırılmamış]",
        "",
        "  @smoke @generated",
        f"  Scenario: {title} senaryosu",
    ]
    if steps:
        lines.append("    Given kullanıcı ana sayfadadır")
        for s in steps:
            action = s.get("action", "aksiyon").strip()
            expected = s.get("expected", "beklenen sonuç").strip()
            lines.append(f'    When kullanıcı "{action}" işlemini yapar')
            lines.append(f'    Then "{expected}" gerçekleşmeli')
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
        "import re",
        "import pytest",
        "from playwright.sync_api import Page, expect",
        "",
        "",
        f"def test_{slug}(page: Page):",
        f'    """Auto-generated stub for: {title}"""',
        f'    page.goto("{url}")',
    ]
    for i, s in enumerate(steps, 1):
        action = s.get("action", "").strip().replace('"', '\\"')
        expected = s.get("expected", "").strip().replace('"', '\\"')
        lines.append(f"    # Adım {i}: {action}")
        if expected:
            lines.append(f"    # Beklenen: {expected}")
        action_lc = action.lower()
        if any(w in action_lc for w in ("tıkla", "click", "bas", "button")):
            lines.append(f'    page.get_by_role("button").filter(has_text="{action[:40]}").click()')
        elif any(w in action_lc for w in ("yaz", "gir", "doldur", "fill", "type", "input")):
            lines.append(f'    page.get_by_label("{action[:40]}").fill("")  # değeri doldurun')
        elif any(w in action_lc for w in ("git", "navigate", "aç", "open", "url")):
            lines.append(f'    page.goto("{url}")')
        elif any(w in action_lc for w in ("bekle", "wait", "yüklen")):
            lines.append("    page.wait_for_load_state('networkidle')")
        elif any(w in action_lc for w in ("seç", "select", "dropdown")):
            lines.append(f'    page.get_by_label("{action[:40]}").select_option("")  # seçeneği belirtin')
        else:
            lines.append("    page.wait_for_load_state('domcontentloaded')  # ⚠ adım manuel implemente edilmeli")
        if expected:
            exp_lc = expected.lower()
            if any(w in exp_lc for w in ("görün", "visible", "gör", "göster")):
                lines.append(f'    expect(page.get_by_text("{expected[:50]}", exact=False)).to_be_visible()')
            elif any(w in exp_lc for w in ("url", "sayfa", "yönlen")):
                lines.append(f'    expect(page).to_have_url(re.compile(r"{_slug(expected)}"))')
            else:
                lines.append(f'    expect(page.get_by_text("{expected[:50]}", exact=False)).to_be_visible()')
    lines += [
        "",
        "    # Genel kontrol — her adımdan bağımsız sayfa sağlığı",
        "    expect(page).not_to_have_url(re.compile(r'error|404|500'))",
    ]
    return "\n".join(lines)


def _run_feature(feature_path: str) -> dict:
    """pytest-bdd ile feature dosyasını çalıştırır."""
    allure_dir = _ENGINE_ROOT / "allure-results"
    allure_dir.mkdir(parents=True, exist_ok=True)

    abs_path = _ENGINE_ROOT / feature_path if not Path(feature_path).is_absolute() else Path(feature_path)

    cmd = [
        sys.executable, "-m", "pytest",
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
            cwd=str(_ENGINE_ROOT),
        )
        passed = proc.returncode == 0
        output = (proc.stdout + proc.stderr).strip()
        return {
            "ok": passed,
            "exit_code": proc.returncode,
            "output": output[:4000],
            "allure_results_dir": str(allure_dir),
            "allure_report_url": "/api/reports/allure",
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "Test zaman aşımına uğradı (>120s)", "exit_code": -1}
    except Exception as exc:
        return {"ok": False, "output": str(exc), "exit_code": -1}


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/manual-to-automation")
def manual_to_automation(body: ManualToAutomationRequest):
    """
    Manuel test → Gherkin BDD + Playwright kodu tek seferde üretir.

    Girdi:
      test_id     (int, zorunlu)    — manual_tests tablosundaki kayıt ID'si
      target_url  (str, opsiyonel)  — Playwright locator tespiti için hedef URL
      framework   (str, opsiyonel)  — "playwright" (default) veya "selenium"
      auto_run    (bool, opsiyonel) — true ise kod üretilince otomatik çalıştırır
      allow_mock  (bool, opsiyonel) — false ise AI anahtarı yoksa 503 döner
      code_review (bool, opsiyonel) — üretilen kodu AI ile incele
      project_id  (int, opsiyonel)  — proje scope'u
    """
    use_mock = not _has_ai_key()

    if use_mock and not body.allow_mock:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "ok": False,
                "error": (
                    "AI anahtarı yapılandırılmamış ve `allow_mock=false` "
                    "geçildi. OPENAI_API_KEY ya da ANTHROPIC_API_KEY ekleyin "
                    "veya `allow_mock=true` ile placeholder üretimi kabul edin."
                ),
                "mock_mode": True,
                "simulated": True,
                "provenance": _resolve_provenance(simulated=True),
            },
        )

    test = _get_test_by_id(body.test_id)
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"test_id={body.test_id} bulunamadı")

    steps: list[dict] = test.get("steps", [])
    if not steps:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Bu test için henüz adım eklenmemiş")

    title: str = test.get("title", f"test_{body.test_id}")
    result: dict = {
        "ok": True,
        "mock_mode": use_mock,
        "simulated": use_mock,
        "provenance": _resolve_provenance(simulated=use_mock),
        "project_id": body.project_id,
        "test_title": title,
        "steps_count": len(steps),
        "gherkin": "",
        "playwright_code": "",
        "feature_path": "",
    }

    # ── Gherkin üret ──────────────────────────────────────────────────────────
    if use_mock:
        result["gherkin"] = _mock_gherkin(title, steps)
        result["playwright_code"] = _mock_playwright(title, steps, body.target_url)
    else:
        requirements = f"Test Başlığı: {title}\n\n{_steps_to_requirements(steps)}"
        try:
            from core.ai_engine import get_ai_engine
            ai = get_ai_engine()
            result["gherkin"] = ai.generate_gherkin(
                requirements=requirements,
                target_url=body.target_url or None,
            )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Gherkin üretimi başarısız: {exc}")

        try:
            task_line = next(
                (l.strip() for l in result["gherkin"].splitlines() if l.strip().startswith("Scenario")),
                title,
            )
            from core.ai_engine import get_ai_engine
            ai = get_ai_engine()
            result["playwright_code"] = ai.generate_test_file(
                url=body.target_url or "http://localhost",
                task=task_line,
                test_name=_slug(title),
            )
        except Exception as exc:
            result["playwright_code"] = f"# Kod üretimi başarısız: {exc}"

    result["gherkin"] = _normalize_gherkin_content(result.get("gherkin", ""), title)

    # ── AI Kod İncelemesi ─────────────────────────────────────────────────────
    result["code_review"] = None
    if body.code_review and result.get("playwright_code") and not result["playwright_code"].startswith("#"):
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
                result["code_review"] = json.loads(clean.strip())
        except Exception as rev_exc:
            result["code_review"] = {
                "score": None,
                "summary": f"İnceleme yapılamadı: {rev_exc}",
                "approved": True,
                "issues": [],
                "suggestions": [],
            }

    # ── .feature dosyasını kaydet ─────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slug(title)
    try:
        FEATURES_DIR.mkdir(parents=True, exist_ok=True)
        feature_abs = FEATURES_DIR / f"{slug}_{ts}.feature"
        feature_abs.write_text(result["gherkin"], encoding="utf-8")
        result["feature_path"] = str(feature_abs.relative_to(_ENGINE_ROOT))
    except Exception as exc:
        result["feature_path"] = f"(kayıt başarısız: {exc})"

    # ── Playwright .py dosyasını kaydet ──────────────────────────────────────
    try:
        TESTS_DIR.mkdir(parents=True, exist_ok=True)
        test_abs = TESTS_DIR / f"test_{slug}_{ts}.py"
        test_abs.write_text(result["playwright_code"], encoding="utf-8")
        result["test_path"] = str(test_abs.relative_to(_ENGINE_ROOT))
    except Exception as exc:
        result["test_path"] = f"(kayıt başarısız: {exc})"

    # ── StepDefinitionMapper ──────────────────────────────────────────────────
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
            result["step_definitions_path"] = str(step_file.relative_to(_ENGINE_ROOT))
            result["new_steps_count"] = len(new_steps)
        else:
            result["new_steps_count"] = 0
    except Exception as exc:
        result["step_definitions_path"] = f"(step mapper hatası: {exc})"

    # ── Locator tespiti ───────────────────────────────────────────────────────
    if body.target_url and not use_mock:
        try:
            from core.browser import BrowserEngine
            from core.page_inspector import PageInspector
            browser = BrowserEngine()
            browser.start()
            browser.page.goto(body.target_url, wait_until="domcontentloaded", timeout=15000)
            inspector = PageInspector(browser.page)
            result["locators"] = inspector.get_interactive_elements()
            browser.stop()
        except Exception as exc:
            result["locators"] = {"error": f"Locator tespiti başarısız: {exc}"}
    elif body.target_url and use_mock:
        result["locators"] = {"mock": True, "note": "AI anahtarı olmadan locator tespiti yapılmadı"}

    # ── Koşu kaydı ve otomatik çalıştır ──────────────────────────────────────
    if body.auto_run:
        from core.db import create_pipeline_run, complete_pipeline_run
        run_db_id = create_pipeline_run(
            project_id=body.project_id,
            test_id=body.test_id,
            test_title=title,
            feature_path=result["feature_path"],
            mock_mode=use_mock,
        )
        if result["feature_path"] and not result["feature_path"].startswith("("):
            run_result = _run_feature(result["feature_path"])
            result["run_result"] = run_result
            run_status = "passed" if run_result.get("ok") else "failed"
            complete_pipeline_run(run_db_id, run_status, run_result.get("allure_results_dir", ""))
        else:
            result["run_result"] = {"ok": False, "output": "Feature dosyası kaydedilemedi, çalıştırılamadı"}
            complete_pipeline_run(run_db_id, "error")
        result["run_id"] = run_db_id

    return result


@router.get("/manual-to-automation/runs")
def list_runs(
    project_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Son koşuları listeler.

    Query params:
      project_id (int, opsiyonel) — proje filtresi
      limit      (int, opsiyonel) — maks kayıt (default 50)
    """
    from core.db import list_pipeline_runs
    runs = list_pipeline_runs(project_id=project_id, limit=limit)
    for run in runs:
        run["provenance"] = _resolve_provenance(simulated=bool(run.get("mock_mode")))
    return {"runs": runs, "total": len(runs)}


@router.post("/manual-to-automation/preview")
def preview_gherkin(body: PreviewGherkinRequest):
    """
    Adımları kaydetmeden önce Gherkin önizleme üretir.

    Girdi:
      title  (str)        — Test başlığı
      steps  (list[dict]) — [{"action": "...", "expected": "..."}]
    """
    if not body.steps:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="steps listesi boş olamaz")

    use_mock = not _has_ai_key()

    if use_mock and not body.allow_mock:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "ok": False,
                "error": "AI anahtarı yok ve `allow_mock=false`. Preview üretilemiyor.",
                "mock_mode": True,
                "simulated": True,
                "provenance": _resolve_provenance(simulated=True),
            },
        )

    if use_mock:
        return {
            "ok": True,
            "gherkin": _mock_gherkin(body.title, body.steps),
            "mock_mode": True,
            "simulated": True,
            "provenance": _resolve_provenance(simulated=True),
        }

    requirements = f"Test Başlığı: {body.title}\n\n{_steps_to_requirements(body.steps)}"
    try:
        from core.ai_engine import get_ai_engine
        ai = get_ai_engine()
        gherkin = ai.generate_gherkin(requirements=requirements)
        return {
            "ok": True,
            "gherkin": gherkin,
            "mock_mode": False,
            "simulated": False,
            "provenance": _resolve_provenance(simulated=False),
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
