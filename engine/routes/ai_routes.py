
from flask import Blueprint, request, jsonify, current_app
from pathlib import Path
import subprocess
import shutil
import uuid
import os
import json
from config.settings import settings
from core.ai_engine import AIEngine, get_ai_engine

ai_bp = Blueprint('ai', __name__)

@ai_bp.route("/api/generate-feature", methods=["POST"])
def generate_feature():
    """BDD Gherkin üretimi — legacy endpoint.

    Önce yeni AI servisini (services.bdd_generator) dener;
    başarısızsa eski AIEngine'e fallback yapar.
    """
    data = request.json or {}
    requirements = data.get("requirements") or data.get("requirement") or ""
    requirements = requirements.strip()
    target_url = data.get("url") or data.get("target_url")
    tech = data.get("tech", "").strip() or None
    if not requirements:
        return jsonify({"error": "Gereksinim metni eksik"}), 400

    try:
        from services import get_llm_gateway
        gw = get_llm_gateway()
        if gw.available:
            from services.bdd_generator import BDDGenerator
            gen = BDDGenerator(gateway=gw)
            result = gen.generate(requirements)
            return jsonify({"content": result.feature_content})
    except Exception:
        pass

    try:
        engine = get_ai_engine()
        content = engine.generate_gherkin(requirements, target_url=target_url, tech=tech)
        return jsonify({"content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@ai_bp.route("/api/analyze-api-request", methods=["POST"])
def analyze_api_request():
    data = request.json or {}
    req_info = data.get("request", {})
    res_info = data.get("response", {})
    if not req_info or not res_info: return jsonify({"error": "Veri eksik"}), 400
    try:
        engine = get_ai_engine()
        analysis = engine.analyze_api_response(req_info, res_info)
        return jsonify({"analysis": analysis})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@ai_bp.route("/api/security-scan", methods=["POST"])
def api_security_scan():
    data = request.json or {}
    url = data.get("url")
    if not url: return jsonify({"error": "URL girin"}), 400
    try:
        engine = get_ai_engine()
        report = engine.run_security_audit(url)
        return jsonify({"status": "success", "report": report})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@ai_bp.route("/api/inspect", methods=["POST"])
def launch_inspector():
    data = request.json or {}
    url = data.get("url", settings.BASE_URL)
    job_id = str(uuid.uuid4())[:8]
    # Use BASE_DIR for temp files
    tmp_file = settings.BASE_DIR / f"tmp_recording_{job_id}.py"
    try:
        # Use playwright CLI from path or shutil.which
        pw_bin = shutil.which("playwright") or "playwright"
        subprocess.run([pw_bin, "codegen", "--target", "python-pytest", "-o", str(tmp_file), url], check=False)
        
        if not tmp_file.exists(): return jsonify({"error": "Kayıt bulunamadı"}), 400
        
        raw_code = tmp_file.read_text(encoding="utf-8")
        engine = get_ai_engine()
        gherkin_content = engine.convert_code_to_gherkin(raw_code)
        return jsonify({"status": "success", "gherkin": gherkin_content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if tmp_file.exists(): tmp_file.unlink()


# ─────────────────────────────────────────────────────────────────────────────
# AI CASE ÜRETİMİ — Doküman → Test Case'ler
# ─────────────────────────────────────────────────────────────────────────────

def _parse_file_content(file) -> str:
    """Yüklenen dosyadan metin içeriği çıkarır (PDF, DOCX, XLSX, TXT)."""
    filename = file.filename.lower()

    if filename.endswith('.pdf'):
        try:
            import pypdf
            import io
            reader = pypdf.PdfReader(io.BytesIO(file.read()))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            try:
                import pdfplumber, io
                with pdfplumber.open(io.BytesIO(file.read())) as pdf:
                    return "\n".join(p.extract_text() or "" for p in pdf.pages)
            except ImportError:
                return file.stream.read().decode('utf-8', errors='ignore')

    elif filename.endswith('.docx'):
        try:
            import docx, io
            doc = docx.Document(io.BytesIO(file.read()))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except ImportError:
            return file.stream.read().decode('utf-8', errors='ignore')

    elif filename.endswith(('.xlsx', '.xls')):
        try:
            import openpyxl, io
            wb = openpyxl.load_workbook(io.BytesIO(file.read()), data_only=True)
            lines = []
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    line = "\t".join(str(c) if c is not None else "" for c in row)
                    if line.strip():
                        lines.append(line)
            return "\n".join(lines)
        except ImportError:
            return file.stream.read().decode('utf-8', errors='ignore')

    else:
        return file.stream.read().decode('utf-8', errors='ignore')


@ai_bp.route("/api/ai/save-test-cases", methods=["POST"])
def ai_save_test_cases():
    """
    Onaylanan AI test case'lerini engine SQLite manual_tests tablosuna kaydeder.

    Body (JSON):
      cases: [
        {
          title: str,
          steps: [{ action: str, expected: str }]
        }
      ]

    Döndürür:
      { ok: true, saved_count: int, test_ids: [int] }
    """
    from core.db import create_manual_test, add_manual_step

    data = request.get_json(silent=True) or {}
    cases = data.get("cases", [])

    if not cases:
        return jsonify({"error": "cases listesi boş"}), 400

    test_ids = []
    for case in cases:
        title = (case.get("title") or "").strip()
        if not title:
            continue
        try:
            test_id = create_manual_test(title)
            steps = case.get("steps") or []
            for step in steps:
                action   = (step.get("action")   or "").strip()
                expected = (step.get("expected") or "").strip()
                if action:
                    add_manual_step(test_id, action, expected)
            test_ids.append(test_id)
        except Exception as exc:
            return jsonify({"error": f"Kayıt hatası ({title}): {exc}"}), 500

    return jsonify({"ok": True, "saved_count": len(test_ids), "test_ids": test_ids})


@ai_bp.route("/api/ai/extract-testcases", methods=["POST"])
def ai_extract_testcases():
    """
    Doküman yükle → AI test case'leri çıkar → önizleme için döndür.
    Form-data: file (PDF/DOCX/XLSX/TXT), module_id (opsiyonel)
    """
    if 'file' not in request.files:
        return jsonify({"error": "Dosya yüklenmedi"}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({"error": "Dosya adı boş"}), 400

    try:
        content = _parse_file_content(file)
        if not content.strip():
            return jsonify({"error": "Dosya içeriği okunamadı veya boş"}), 400

        engine = get_ai_engine()
        cases = engine.extract_test_cases_from_document(content)
        return jsonify({"cases": cases, "count": len(cases)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# AI SERVİS TEST ÜRETİMİ — Spec/Kod → Test Senaryoları
# ─────────────────────────────────────────────────────────────────────────────

@ai_bp.route("/api/ai/extract-service-tests", methods=["POST"])
def ai_extract_service_tests():
    """
    Swagger/OpenAPI/Kaynak Kod/Postman → AI servis test senaryoları üret.
    Form-data veya JSON:
      - file: dosya yükleme (YAML, JSON, .py, .java, .js vb.)
      - content: direkt metin içeriği
      - spec_type: openapi | source_code | postman (varsayılan: openapi)
    """
    spec_type = "openapi"
    content = ""

    if 'file' in request.files:
        file = request.files['file']
        fname = file.filename.lower()
        content = file.stream.read().decode('utf-8', errors='ignore')
        if fname.endswith(('.py', '.java', '.js', '.ts', '.go')):
            spec_type = "source_code"
        elif 'postman' in fname or fname.endswith('.postman_collection.json'):
            spec_type = "postman"
        elif fname.endswith(('.yaml', '.yml', '.json')):
            spec_type = "openapi"
    else:
        data = request.json or {}
        content = data.get("content", "").strip()
        spec_type = data.get("spec_type", "openapi")

    if not content:
        return jsonify({"error": "İçerik boş"}), 400

    try:
        engine = get_ai_engine()
        tests = engine.extract_service_tests_from_spec(content, spec_type)
        return jsonify({"tests": tests, "count": len(tests), "spec_type": spec_type})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/api/ai/save-service-tests", methods=["POST"])
def ai_save_service_tests():
    """
    Onaylanan servis testlerini dosya sistemine kaydeder.
    Body: { tests: [...], formats: ["pytest", "gherkin", "postman"] }
    """
    data = request.json or {}
    tests = data.get("tests", [])
    formats = data.get("formats", ["pytest"])

    if not tests:
        return jsonify({"error": "Kaydedilecek test yok"}), 400

    saved = []
    base_dir = settings.BASE_DIR

    for fmt in formats:
        try:
            if fmt == "pytest":
                content = _generate_pytest_service_tests(tests)
                path = base_dir / "tests" / "api" / "test_ai_generated.py"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding='utf-8')
                saved.append({"format": "pytest", "path": str(path)})

            elif fmt == "gherkin":
                content = _generate_gherkin_service_tests(tests)
                path = base_dir / "features" / "api" / "ai_generated.feature"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding='utf-8')
                saved.append({"format": "gherkin", "path": str(path)})

            elif fmt == "postman":
                collection = _generate_postman_collection(tests)
                path = base_dir / "api_collections" / "ai_generated.postman_collection.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(collection, indent=2, ensure_ascii=False), encoding='utf-8')
                saved.append({"format": "postman", "path": str(path)})

        except Exception as e:
            saved.append({"format": fmt, "error": str(e)})

    return jsonify({"ok": True, "saved": saved})


def _generate_pytest_service_tests(tests: list) -> str:
    lines = [
        "\"\"\"AI tarafından üretilmiş servis testleri\"\"\"",
        "import pytest", "import requests", "",
        "BASE_URL = \"http://localhost:8000\"", ""
    ]
    for t in tests:
        fn_name = t['title'].lower().replace(' ', '_').replace('-', '_')[:50]
        fn_name = ''.join(c for c in fn_name if c.isalnum() or c == '_')
        req = t.get('request', {})
        exp = t.get('expected_response', {})
        lines += [
            f"def test_{fn_name}():",
            f"    \"\"\"{ t.get('description', t['title']) }\"\"\"",
            f"    response = requests.{req.get('method','GET').lower()}(",
            f"        BASE_URL + \"{req.get('path', '/')}\",",
        ]
        if req.get('headers'):
            lines.append(f"        headers={req['headers']},")
        if req.get('body'):
            lines.append(f"        json={req['body']},")
        lines += [
            "    )",
            f"    assert response.status_code == {exp.get('status_code', 200)}",
        ]
        for contains in exp.get('body_contains', []):
            lines.append(f"    assert \"{contains}\" in response.text")
        lines.append("")
    return "\n".join(lines)


def _generate_gherkin_service_tests(tests: list) -> str:
    lines = ["Feature: AI Üretimi Servis Testleri", ""]
    for t in tests:
        req = t.get('request', {})
        exp = t.get('expected_response', {})
        tags = "@" + " @".join(t.get('tags', '').split(',')) if t.get('tags') else ""
        lines += [
            f"  {tags}".strip(),
            f"  Scenario: {t['title']}",
            f"    Given servis endpoint \"{req.get('path', '/')}\" hazır",
            f"    When {req.get('method','GET')} isteği gönderilir",
            f"    Then yanıt kodu {exp.get('status_code', 200)} olmalıdır",
            ""
        ]
    return "\n".join(lines)


def _generate_postman_collection(tests: list) -> dict:
    items = []
    for t in tests:
        req = t.get('request', {})
        items.append({
            "name": t['title'],
            "request": {
                "method": req.get('method', 'GET'),
                "url": {"raw": "{{BASE_URL}}" + req.get('path', '/'), "host": ["{{BASE_URL}}"], "path": req.get('path', '/').split('/')},
                "header": [{"key": k, "value": v} for k, v in req.get('headers', {}).items()],
                "body": {"mode": "raw", "raw": json.dumps(req.get('body', {}), ensure_ascii=False), "options": {"raw": {"language": "json"}}} if req.get('body') else None
            },
            "response": []
        })
    return {
        "info": {"name": "AI Üretimi Servis Testleri", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
        "item": items
    }


# ═══════════════════════════════════════════════════════════════════════════════
# AI FAILURE ANALYZER
# POST /api/ai/analyze-failure
# ═══════════════════════════════════════════════════════════════════════════════

@ai_bp.route("/api/ai/analyze-failure", methods=["POST"])
def analyze_failure():
    """Başarısız test çıktısını analiz eder, kategori ve düzeltme önerisi döner."""
    data = request.json or {}
    test_title = data.get("test_title", "")
    feature_path = data.get("feature_path", "")
    error_hint = data.get("error_hint", "")
    status = data.get("status", "failed")

    if status == "passed":
        return jsonify({"reason": "Test geçti", "category": "none", "fix_suggestion": "", "auto_fixable": False})

    prompt = f"""You are a test automation expert. A Playwright/pytest test failed.

Test: {test_title}
Feature file: {feature_path}
Error output (if any): {error_hint[:2000] if error_hint else "No error details provided"}

Analyze the failure and respond ONLY with valid JSON (no markdown, no extra text):
{{
  "reason": "one sentence explaining why the test failed",
  "category": "locator|logic|data|timeout|network|environment|unknown",
  "fix_suggestion": "specific code or config change to fix it",
  "auto_fixable": true or false
}}"""

    try:
        from services import get_llm_gateway
        gw = get_llm_gateway()
        if not gw.available:
            raise RuntimeError("LLM not available")
        response = gw.complete(
            [{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        clean = response.content.strip()
        if clean.startswith("```"):
            clean = "\n".join(clean.split("\n")[1:])
        if clean.endswith("```"):
            clean = "\n".join(clean.split("\n")[:-1])
        result = json.loads(clean.strip())
        return jsonify(result)
    except Exception as e:
        # Heuristic fallback if LLM unavailable
        category = "unknown"
        reason = "LLM erişilemiyor — hata detayı için log çıktısını inceleyin"
        fix = ""
        auto_fixable = False
        if error_hint:
            if "NoSuchElementException" in error_hint or "locator" in error_hint.lower() or "selector" in error_hint.lower():
                category = "locator"
                reason = "Locator hatalı veya element DOM'da bulunamadı"
                fix = "Locator'ı kontrol edin: page.locator() veya getByRole() kullanın"
                auto_fixable = True
            elif "TimeoutError" in error_hint or "timeout" in error_hint.lower():
                category = "timeout"
                reason = "Test bekleme süresi aşıldı"
                fix = "page.wait_for_selector() veya timeout değerini artırın"
            elif "AssertionError" in error_hint or "assert" in error_hint.lower():
                category = "logic"
                reason = "Assertion başarısız — beklenen değer ile gerçek değer uyuşmuyor"
                fix = "Test assertion'larını ve test verisini kontrol edin"
        return jsonify({"reason": reason, "category": category, "fix_suggestion": fix, "auto_fixable": auto_fixable})


# ═══════════════════════════════════════════════════════════════════════════════
# NATURAL LANGUAGE TEST TRIGGER
# POST /api/ai/nl-test
# ═══════════════════════════════════════════════════════════════════════════════

@ai_bp.route("/api/ai/nl-test", methods=["POST"])
def natural_language_test():
    """Doğal dil isteğinden test senaryosu üretir ve pipeline'a gönderir."""
    data = request.json or {}
    prompt_text = data.get("prompt", "").strip()
    project_id = data.get("project_id")
    auto_run = data.get("auto_run", False)

    if not prompt_text:
        return jsonify({"ok": False, "error": "prompt zorunludur"}), 400

    system_prompt = f"""You are a test automation expert. Convert this natural language test description into a structured test case.

Input: "{prompt_text}"

Respond ONLY with valid JSON (no markdown):
{{
  "title": "short test title",
  "description": "what this test verifies",
  "steps": [
    {{"action": "navigate to login page", "expected": "login form is visible"}},
    {{"action": "enter username testuser", "expected": "username field is filled"}}
  ],
  "tags": ["smoke", "login"],
  "url_hint": "optional URL hint if mentioned"
}}"""

    try:
        from services import get_llm_gateway
        gw = get_llm_gateway()
        if not gw.available:
            raise RuntimeError("LLM not available")
        raw = gw.complete(
            [{"role": "user", "content": system_prompt}],
            max_tokens=800,
        )
        clean = raw.content.strip()
        if clean.startswith("```"):
            clean = "\n".join(clean.split("\n")[1:])
        if clean.endswith("```"):
            clean = "\n".join(clean.split("\n")[:-1])
        case = json.loads(clean.strip())
    except Exception as e:
        return jsonify({"ok": False, "error": f"LLM hatası: {e}"}), 500

    result = {"ok": True, "case": case}

    # Pipeline'a otomatik gönder
    if auto_run and project_id:
        try:
            from core.db import create_manual_test, add_manual_step
            test_id = create_manual_test(
                project_id=str(project_id),
                title=case["title"],
                description=case.get("description", ""),
                tags=",".join(case.get("tags", [])),
            )
            for step in case.get("steps", []):
                add_manual_step(test_id, step.get("action", ""), step.get("expected", ""))
            result["test_id"] = test_id
            result["message"] = "Test DB'ye kaydedildi. Pipeline'ı manuel-to-automation sayfasından tetikleyebilirsiniz."
        except Exception as e:
            result["db_error"] = str(e)

    return jsonify(result)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST IMPACT ANALYSIS
# POST /api/ai/impact-analysis
# ═══════════════════════════════════════════════════════════════════════════════

@ai_bp.route("/api/ai/impact-analysis", methods=["POST"])
def impact_analysis():
    """Commit diff'i analiz ederek etkilenen test dosyalarını döner."""
    data = request.json or {}
    diff = data.get("diff", "").strip()
    changed_files = data.get("changed_files", [])
    project_id = data.get("project_id")

    # Önce dosya bazlı kural tabanlı eşleştirme
    matched_tests: list[str] = []
    keywords: list[str] = []

    for f in changed_files:
        f_lower = f.lower()
        # Dosya adından anahtar kelime çıkar
        stem = Path(f_lower).stem.replace("-", "_").replace(".", "_")
        keywords.append(stem)
        # Direkt test dosyası eşleştirmesi
        test_candidates = [
            settings.TESTS_DIR / f"test_{stem}.py",
            settings.BASE_DIR / "tests" / f"test_{stem}.py",
        ]
        for tc in test_candidates:
            if tc.exists():
                matched_tests.append(str(tc.relative_to(settings.BASE_DIR)))

    # Özellik dizininde fuzzy arama
    if settings.BASE_DIR.exists():
        for kw in keywords[:5]:
            for test_file in (settings.TESTS_DIR or Path("tests")).glob("test_*.py"):
                if kw in test_file.stem and str(test_file.relative_to(settings.BASE_DIR)) not in matched_tests:
                    matched_tests.append(str(test_file.relative_to(settings.BASE_DIR)))

    matched_tests = list(dict.fromkeys(matched_tests))[:20]

    # LLM ile zenginleştir
    ai_suggestions = []
    if diff:
        try:
            from services import get_llm_gateway
            gw = get_llm_gateway()
            if gw.available:
                ai_prompt = f"""Analyze this git diff and suggest which test areas are most likely affected.

Changed files: {json.dumps(changed_files[:10])}
Diff preview: {diff[:1500]}

Respond ONLY with JSON:
{{
  "affected_areas": ["authentication", "checkout", ...],
  "risk_level": "low|medium|high",
  "suggested_test_tags": ["smoke", "regression", ...],
  "reasoning": "brief explanation"
}}"""
                raw = gw.complete(
                    [{"role": "user", "content": ai_prompt}],
                    max_tokens=400,
                )
                clean = raw.content.strip()
                if clean.startswith("```"):
                    clean = "\n".join(clean.split("\n")[1:])
                if clean.endswith("```"):
                    clean = "\n".join(clean.split("\n")[:-1])
                ai_suggestions = json.loads(clean.strip())
        except Exception:
            pass

    return jsonify({
        "ok": True,
        "matched_tests": matched_tests,
        "total_matched": len(matched_tests),
        "ai_analysis": ai_suggestions,
        "keywords_used": keywords[:10],
    })
