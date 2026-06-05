"""
AI routes — Flask engine'den FastAPI'ye port edilmiştir.

ÖNCE (Flask):
  /engine/routes/ai_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/ai_routes.py — APIRouter, port 8000 (consolidated)

En kritik 30 endpoint: generate, analyze, heal, suggest, nl-test, impact-analysis, vb.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["engine", "ai"])


# ─── Shared helpers ──────────────────────────────────────────────────────────

def _get_engine():
    """AIEngine singleton — geçici shim; gerçek import engine paketten."""
    try:
        from core.ai_engine import get_ai_engine  # type: ignore[import]
        return get_ai_engine()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"AI Engine başlatılamadı: {exc}")


def _get_llm_gateway():
    """LLM Gateway singleton."""
    try:
        from services import get_llm_gateway  # type: ignore[import]
        gw = get_llm_gateway()
        if not gw.available:
            raise RuntimeError("LLM kullanılamaz")
        return gw
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


def _strip_markdown_fences(text: str) -> str:
    """Kod bloğu işaretlerini temizler."""
    text = text.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
    if text.endswith("```"):
        text = "\n".join(text.split("\n")[:-1])
    return text.strip()


def _parse_file_content(content: bytes, filename: str) -> str:
    """Yüklenen dosyadan metin içeriği çıkarır (PDF, DOCX, XLSX, TXT)."""
    fname = filename.lower()

    if fname.endswith(".pdf"):
        try:
            import io

            import pypdf  # type: ignore[import]
            reader = pypdf.PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            logger.warning(
                "Opsiyonel bağımlılık 'pypdf' yüklenemedi, pdfplumber deneniyor. "
                "pip install pypdf ile ekleyin."
            )
            try:
                import io

                import pdfplumber  # type: ignore[import]
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    return "\n".join(p.extract_text() or "" for p in pdf.pages)
            except ImportError:
                logger.warning(
                    "Opsiyonel bağımlılık 'pdfplumber' yüklenemedi, PDF düz metin olarak okunacak. "
                    "pip install pdfplumber ile ekleyin."
                )
                return content.decode("utf-8", errors="ignore")

    if fname.endswith(".docx"):
        try:
            import io

            import docx  # type: ignore[import]
            doc = docx.Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except ImportError:
            logger.warning(
                "Opsiyonel bağımlılık 'python-docx' yüklenemedi, DOCX düz metin olarak okunacak. "
                "pip install python-docx ile ekleyin."
            )
            return content.decode("utf-8", errors="ignore")

    if fname.endswith((".xlsx", ".xls")):
        try:
            import io

            import openpyxl  # type: ignore[import]
            wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
            lines = []
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    line = "\t".join(str(c) if c is not None else "" for c in row)
                    if line.strip():
                        lines.append(line)
            return "\n".join(lines)
        except ImportError:
            logger.warning(
                "Opsiyonel bağımlılık 'openpyxl' yüklenemedi, Excel düz metin olarak okunacak. "
                "pip install openpyxl ile ekleyin."
            )
            return content.decode("utf-8", errors="ignore")

    return content.decode("utf-8", errors="ignore")


# ─── Schemas ─────────────────────────────────────────────────────────────────

class GenerateFeatureBody(BaseModel):
    requirements: Optional[str] = None
    requirement: Optional[str] = None
    url: Optional[str] = None
    target_url: Optional[str] = None
    tech: Optional[str] = None


class AnalyzeApiRequestBody(BaseModel):
    request: dict = Field(default_factory=dict)
    response: dict = Field(default_factory=dict)


class SecurityScanBody(BaseModel):
    url: Optional[str] = None
    target_url: Optional[str] = Field(default="http://127.0.0.1:8000")
    scan_type: Optional[str] = Field(default="quick")
    openapi_spec_url: Optional[str] = None


class InspectBody(BaseModel):
    url: Optional[str] = None


class SaveTestCasesBody(BaseModel):
    cases: list[dict] = Field(default_factory=list)


class ExtractServiceTestsBody(BaseModel):
    content: str = ""
    spec_type: str = "openapi"


class SaveServiceTestsBody(BaseModel):
    tests: list[dict] = Field(default_factory=list)
    formats: list[str] = Field(default_factory=lambda: ["pytest"])


class AnalyzeFailureBody(BaseModel):
    test_title: str = ""
    feature_path: str = ""
    error_hint: str = ""
    status: str = "failed"


class NlTestBody(BaseModel):
    prompt: str = Field(..., min_length=1)
    project_id: Optional[str] = None
    auto_run: bool = False


class ImpactAnalysisBody(BaseModel):
    diff: str = ""
    changed_files: list[str] = Field(default_factory=list)
    project_id: Optional[str] = None


class GenerateTestBody(BaseModel):
    requirement: str = Field(..., min_length=1)
    framework: str = "pytest-bdd"
    model: Optional[str] = None
    page_objects: list[str] = Field(default_factory=list)


class GenerateBddBody(BaseModel):
    requirement: str = Field(..., min_length=1)
    model: Optional[str] = None


class SelfHealBody(BaseModel):
    failed_locator: str = Field(..., min_length=1)
    accessibility_tree: Optional[str] = None
    error_message: Optional[str] = None
    page_url: Optional[str] = None


class FindElementBody(BaseModel):
    element_intent: str = Field(..., min_length=1)
    accessibility_tree: Optional[str] = None


class AnalyzeAnomalyBody(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    total_duration: float = 0.0
    avg_duration: float = 0.0


class CoverageGapsBody(BaseModel):
    coverage_path: str = "reports/coverage.json"
    generate_suggestions: bool = False


class PrioritizeBody(BaseModel):
    git_diff: str = ""
    time_budget_seconds: int = 300
    min_score_threshold: float = 0.1


class AnalyzeAssertionsBody(BaseModel):
    file_path: str = Field(..., min_length=1)


# ─── Routes ──────────────────────────────────────────────────────────────────

# 1. BDD / Gherkin üretimi (legacy endpoint)
@router.post("/generate-feature")
def generate_feature(body: GenerateFeatureBody) -> dict:
    """BDD Gherkin üretimi — legacy endpoint.

    Önce yeni AI servisini (services.bdd_generator) dener;
    başarısızsa eski AIEngine'e fallback yapar.
    Flask engine'den FastAPI'ye port edilmiştir.
    """
    requirements = (body.requirements or body.requirement or "").strip()
    if not requirements:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gereksinim metni eksik")

    target_url = body.url or body.target_url
    tech = (body.tech or "").strip() or None

    try:
        from services import get_llm_gateway  # type: ignore[import]
        gw = get_llm_gateway()
        if gw.available:
            from services.bdd_generator import BDDGenerator  # type: ignore[import]
            gen = BDDGenerator(gateway=gw)
            result = gen.generate(requirements)
            return {"content": result.feature_content}
    except Exception:
        pass

    try:
        engine = _get_engine()
        content = engine.generate_gherkin(requirements, target_url=target_url, tech=tech)
        return {"content": content}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# 2. API request analizi
@router.post("/analyze-api-request")
def analyze_api_request(body: AnalyzeApiRequestBody) -> dict:
    """API istek/yanıt çiftini analiz eder.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    if not body.request or not body.response:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Veri eksik")
    try:
        engine = _get_engine()
        analysis = engine.analyze_api_response(body.request, body.response)
        return {"analysis": analysis}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# 3. Güvenlik taraması
@router.post("/security-scan")
def api_security_scan(body: SecurityScanBody) -> dict:
    """Hedef URL için güvenlik denetimi çalıştırır.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    url = body.url or body.target_url
    if not url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL girin")
    try:
        engine = _get_engine()
        report = engine.run_security_audit(url)
        return {"status": "success", "report": report}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# 4. Playwright inspector → Gherkin
@router.post("/inspect")
def launch_inspector(body: InspectBody) -> dict:
    """Playwright codegen çalıştırır ve çıktıyı Gherkin'e dönüştürür.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    try:
        from config.settings import settings  # type: ignore[import]
        base_url = body.url or settings.BASE_URL
        base_dir: Path = settings.BASE_DIR
    except Exception:
        base_url = body.url or "http://localhost:3000"
        base_dir = Path("/tmp")

    job_id = str(uuid.uuid4())[:8]
    tmp_file = base_dir / f"tmp_recording_{job_id}.py"

    try:
        pw_bin = shutil.which("playwright") or "playwright"
        subprocess.run(
            [pw_bin, "codegen", "--target", "python-pytest", "-o", str(tmp_file), base_url],
            check=False,
        )
        if not tmp_file.exists():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kayıt bulunamadı")
        raw_code = tmp_file.read_text(encoding="utf-8")
        engine = _get_engine()
        gherkin_content = engine.convert_code_to_gherkin(raw_code)
        return {"status": "success", "gherkin": gherkin_content}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    finally:
        if tmp_file.exists():
            tmp_file.unlink()


# 5. AI test case'lerini kaydet
@router.post("/save-test-cases", status_code=status.HTTP_201_CREATED)
def ai_save_test_cases(body: SaveTestCasesBody) -> dict:
    """Onaylanan AI test case'lerini engine SQLite manual_tests tablosuna kaydeder.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    if not body.cases:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cases listesi boş")

    try:
        from core.db import add_manual_step, create_manual_test  # type: ignore[import]
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"DB erişilemiyor: {exc}")

    test_ids: list[int] = []
    for case in body.cases:
        title = (case.get("title") or "").strip()
        if not title:
            continue
        try:
            test_id = create_manual_test(title)
            for step in case.get("steps") or []:
                action = (step.get("action") or "").strip()
                expected = (step.get("expected") or "").strip()
                if action:
                    add_manual_step(test_id, action, expected)
            test_ids.append(test_id)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Kayıt hatası ({title}): {exc}",
            )

    return {"ok": True, "saved_count": len(test_ids), "test_ids": test_ids}


# 6. Dokümandan test case'leri çıkar (dosya yükleme)
@router.post("/extract-testcases")
async def ai_extract_testcases(
    file: UploadFile = File(...),
    module_id: Optional[str] = Form(default=None),
) -> dict:
    """Doküman yükle → AI test case'leri çıkar → önizleme için döndür.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dosya adı boş")

    raw = await file.read()
    content = _parse_file_content(raw, file.filename)
    if not content.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dosya içeriği okunamadı veya boş")

    try:
        engine = _get_engine()
        cases = engine.extract_test_cases_from_document(content)
        return {"cases": cases, "count": len(cases)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# 7. Servis test senaryoları çıkar (JSON body)
@router.post("/extract-service-tests")
async def ai_extract_service_tests_json(body: ExtractServiceTestsBody) -> dict:
    """Swagger/OpenAPI/Kaynak Kod/Postman JSON body → servis test senaryoları.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    if not body.content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="İçerik boş")
    try:
        engine = _get_engine()
        tests = engine.extract_service_tests_from_spec(body.content, body.spec_type)
        return {"tests": tests, "count": len(tests), "spec_type": body.spec_type}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# 8. Servis test senaryoları çıkar (dosya yükleme)
@router.post("/extract-service-tests/upload")
async def ai_extract_service_tests_file(file: UploadFile = File(...)) -> dict:
    """Swagger/OpenAPI/Postman dosya yükleme → servis test senaryoları.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    fname = (file.filename or "").lower()
    raw = await file.read()
    content = raw.decode("utf-8", errors="ignore")
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="İçerik boş")

    if fname.endswith((".py", ".java", ".js", ".ts", ".go")):
        spec_type = "source_code"
    elif "postman" in fname or fname.endswith(".postman_collection.json"):
        spec_type = "postman"
    else:
        spec_type = "openapi"

    try:
        engine = _get_engine()
        tests = engine.extract_service_tests_from_spec(content, spec_type)
        return {"tests": tests, "count": len(tests), "spec_type": spec_type}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# 9. Servis testlerini dosya sistemine kaydet
@router.post("/save-service-tests")
def ai_save_service_tests(body: SaveServiceTestsBody) -> dict:
    """Onaylanan servis testlerini dosya sistemine kaydeder (pytest/gherkin/postman).

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    if not body.tests:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kaydedilecek test yok")

    try:
        from config.settings import settings  # type: ignore[import]
        base_dir: Path = settings.BASE_DIR
    except Exception:
        base_dir = Path("/tmp/cortex_engine")

    saved: list[dict] = []
    for fmt in body.formats:
        try:
            if fmt == "pytest":
                content = _generate_pytest_service_tests(body.tests)
                path = base_dir / "tests" / "api" / "test_ai_generated.py"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                saved.append({"format": "pytest", "path": str(path)})
            elif fmt == "gherkin":
                content = _generate_gherkin_service_tests(body.tests)
                path = base_dir / "features" / "api" / "ai_generated.feature"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                saved.append({"format": "gherkin", "path": str(path)})
            elif fmt == "postman":
                collection = _generate_postman_collection(body.tests)
                path = base_dir / "api_collections" / "ai_generated.postman_collection.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(collection, indent=2, ensure_ascii=False), encoding="utf-8")
                saved.append({"format": "postman", "path": str(path)})
        except Exception as exc:
            saved.append({"format": fmt, "error": str(exc)})

    return {"ok": True, "saved": saved}


# 10. Başarısız test analizi
@router.post("/analyze-failure")
def analyze_failure(body: AnalyzeFailureBody) -> dict:
    """Başarısız test çıktısını analiz eder, kategori ve düzeltme önerisi döner.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    if body.status == "passed":
        return {"reason": "Test geçti", "category": "none", "fix_suggestion": "", "auto_fixable": False}

    prompt = f"""You are a test automation expert. A Playwright/pytest test failed.

Test: {body.test_title}
Feature file: {body.feature_path}
Error output (if any): {body.error_hint[:2000] if body.error_hint else "No error details provided"}

Analyze the failure and respond ONLY with valid JSON (no markdown, no extra text):
{{
  "reason": "one sentence explaining why the test failed",
  "category": "locator|logic|data|timeout|network|environment|unknown",
  "fix_suggestion": "specific code or config change to fix it",
  "auto_fixable": true or false
}}"""

    try:
        gw = _get_llm_gateway()
        response = gw.complete([{"role": "user", "content": prompt}], max_tokens=500)
        result = json.loads(_strip_markdown_fences(response.content))
        return result
    except HTTPException:
        pass
    except Exception:
        pass

    # Heuristic fallback
    category = "unknown"
    reason = "LLM erişilemiyor — hata detayı için log çıktısını inceleyin"
    fix = ""
    auto_fixable = False
    if body.error_hint:
        hint = body.error_hint
        if "NoSuchElementException" in hint or "locator" in hint.lower() or "selector" in hint.lower():
            category, reason, fix, auto_fixable = (
                "locator",
                "Locator hatalı veya element DOM'da bulunamadı",
                "Locator'ı kontrol edin: page.locator() veya getByRole() kullanın",
                True,
            )
        elif "TimeoutError" in hint or "timeout" in hint.lower():
            category, reason, fix = (
                "timeout",
                "Test bekleme süresi aşıldı",
                "page.wait_for_selector() veya timeout değerini artırın",
            )
        elif "AssertionError" in hint or "assert" in hint.lower():
            category, reason, fix = (
                "logic",
                "Assertion başarısız — beklenen değer ile gerçek değer uyuşmuyor",
                "Test assertion'larını ve test verisini kontrol edin",
            )
    return {"reason": reason, "category": category, "fix_suggestion": fix, "auto_fixable": auto_fixable}


# 11. Doğal dil test senaryosu üretimi
@router.post("/nl-test")
def natural_language_test(body: NlTestBody) -> dict:
    """Doğal dil isteğinden test senaryosu üretir ve pipeline'a gönderir.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    system_prompt = f"""You are a test automation expert. Convert this natural language test description into a structured test case.

Input: "{body.prompt}"

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
        gw = _get_llm_gateway()
        raw = gw.complete([{"role": "user", "content": system_prompt}], max_tokens=800)
        case: dict = json.loads(_strip_markdown_fences(raw.content))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"LLM hatası: {exc}")

    result: dict[str, Any] = {"ok": True, "case": case}

    if body.auto_run and body.project_id:
        try:
            from core.db import add_manual_step, create_manual_test  # type: ignore[import]
            test_id = create_manual_test(
                project_id=str(body.project_id),
                title=case["title"],
                description=case.get("description", ""),
                tags=",".join(case.get("tags", [])),
            )
            for step in case.get("steps", []):
                add_manual_step(test_id, step.get("action", ""), step.get("expected", ""))
            result["test_id"] = test_id
            result["message"] = "Test DB'ye kaydedildi."
        except Exception as exc:
            result["db_error"] = str(exc)

    return result


# 12. Test impact analizi
@router.post("/impact-analysis")
def impact_analysis(body: ImpactAnalysisBody) -> dict:
    """Commit diff'i analiz ederek etkilenen test dosyalarını döner.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    try:
        from config.settings import settings  # type: ignore[import]
        base_dir: Path = settings.BASE_DIR
        tests_dir: Path = settings.TESTS_DIR
    except Exception:
        base_dir = Path("/tmp/cortex_engine")
        tests_dir = base_dir / "tests"

    matched_tests: list[str] = []
    keywords: list[str] = []

    for f in body.changed_files:
        f_lower = f.lower()
        stem = Path(f_lower).stem.replace("-", "_").replace(".", "_")
        keywords.append(stem)
        for candidate in [
            tests_dir / f"test_{stem}.py",
            base_dir / "tests" / f"test_{stem}.py",
        ]:
            if candidate.exists():
                matched_tests.append(str(candidate.relative_to(base_dir)))

    if base_dir.exists():
        for kw in keywords[:5]:
            for test_file in (tests_dir or Path("tests")).glob("test_*.py"):
                rel = str(test_file.relative_to(base_dir))
                if kw in test_file.stem and rel not in matched_tests:
                    matched_tests.append(rel)

    matched_tests = list(dict.fromkeys(matched_tests))[:20]
    ai_suggestions: dict = {}

    if body.diff:
        try:
            gw = _get_llm_gateway()
            ai_prompt = f"""Analyze this git diff and suggest which test areas are most likely affected.

Changed files: {json.dumps(body.changed_files[:10])}
Diff preview: {body.diff[:1500]}

Respond ONLY with JSON:
{{
  "affected_areas": ["authentication", "checkout"],
  "risk_level": "low|medium|high",
  "suggested_test_tags": ["smoke", "regression"],
  "reasoning": "brief explanation"
}}"""
            raw = gw.complete([{"role": "user", "content": ai_prompt}], max_tokens=400)
            ai_suggestions = json.loads(_strip_markdown_fences(raw.content))
        except Exception:
            pass

    return {
        "ok": True,
        "matched_tests": matched_tests,
        "total_matched": len(matched_tests),
        "ai_analysis": ai_suggestions,
        "keywords_used": keywords[:10],
    }


# 13. Test kodu üretimi (framework seçimi ile)
@router.post("/generate-test")
def generate_test(body: GenerateTestBody) -> dict:
    """Doğal dil gereksinimden test kodu üretir (pytest-bdd / playwright-ts / pytest).

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    try:
        engine = _get_engine()
        code = engine.generate_test_code(
            body.requirement,
            framework=body.framework,
            page_objects=body.page_objects,
        )
        return {"code": code, "framework": body.framework}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# 14. BDD Gherkin üretimi (yeni endpoint)
@router.post("/generate-bdd")
def generate_bdd(body: GenerateBddBody) -> dict:
    """Doğal dil gereksinimden Gherkin BDD senaryosu üretir.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    try:
        engine = _get_engine()
        result = engine.generate_gherkin(body.requirement)
        return {"feature": result}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# 15. Self-healing locator
@router.post("/self-heal")
def self_heal(body: SelfHealBody) -> dict:
    """Kırık locator için yeni locator önerisi üretir.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    try:
        engine = _get_engine()
        result = engine.self_heal_locator(
            failed_locator=body.failed_locator,
            accessibility_tree=body.accessibility_tree or "",
            error_message=body.error_message or "",
            page_url=body.page_url or "",
        )
        return result if isinstance(result, dict) else {"new_locator": result, "healed": True}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# 16. Element bul
@router.post("/find-element")
def find_element(body: FindElementBody) -> dict:
    """Accessibility tree'den element locator'ı üretir.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    try:
        engine = _get_engine()
        locator = engine.find_element_locator(
            element_intent=body.element_intent,
            accessibility_tree=body.accessibility_tree or "",
        )
        return {"locator": locator}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# 17. Healing log
@router.get("/healing-log")
def healing_log() -> dict:
    """Self-healing geçmişini döndürür.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    try:
        engine = _get_engine()
        log = engine.get_healing_log()
        return {"log": log, "count": len(log)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# 18. Anomaly tespiti
@router.post("/analyze-anomaly")
def analyze_anomaly(body: AnalyzeAnomalyBody) -> dict:
    """Test çalışma sonuçlarında anomaly tespit eder.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    try:
        engine = _get_engine()
        anomalies = engine.analyze_anomalies(
            total=body.total,
            passed=body.passed,
            failed=body.failed,
            total_duration=body.total_duration,
            avg_duration=body.avg_duration,
        )
        return {"anomalies": anomalies}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# 19. Flaky test raporu
@router.get("/flaky-report")
def flaky_report() -> dict:
    """Flaky test analiz raporunu döndürür.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    try:
        engine = _get_engine()
        report = engine.get_flaky_report()
        return {"report": report}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# 20. Coverage gap analizi
@router.post("/coverage-gaps")
def coverage_gaps(body: CoverageGapsBody) -> dict:
    """Coverage raporundan gap'leri analiz eder.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    try:
        engine = _get_engine()
        gaps = engine.analyze_coverage_gaps(
            coverage_path=body.coverage_path,
            generate_suggestions=body.generate_suggestions,
        )
        return {"gaps": gaps}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# 21. Test önceliklendirme
@router.post("/prioritize")
def prioritize_tests(body: PrioritizeBody) -> dict:
    """Git diff'e göre testleri önceliklendirir.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    try:
        engine = _get_engine()
        result = engine.prioritize_tests(
            git_diff=body.git_diff,
            time_budget_seconds=body.time_budget_seconds,
            min_score_threshold=body.min_score_threshold,
        )
        return {"tests": result}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# 22. LLM kullanım istatistikleri
@router.get("/stats")
def ai_stats() -> dict:
    """LLM kullanım istatistiklerini döndürür (toplam çağrı, token, maliyet).

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    try:
        engine = _get_engine()
        stats = engine.get_llm_stats()
        return stats if isinstance(stats, dict) else {"stats": stats}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# 23. Assertion analizi
@router.post("/analyze-assertions")
def analyze_assertions(body: AnalyzeAssertionsBody) -> dict:
    """Test dosyasındaki eksik assertion'ları analiz eder.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    try:
        engine = _get_engine()
        suggestions = engine.analyze_assertions(body.file_path)
        return {"suggestions": suggestions, "file_path": body.file_path}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ─── Private helpers (service test code generation) ──────────────────────────

def _generate_pytest_service_tests(tests: list) -> str:
    lines = [
        '"""AI tarafından üretilmiş servis testleri"""',
        "import pytest",
        "import requests",
        "",
        'BASE_URL = "http://localhost:8000"',
        "",
    ]
    for t in tests:
        fn_name = t["title"].lower().replace(" ", "_").replace("-", "_")[:50]
        fn_name = "".join(c for c in fn_name if c.isalnum() or c == "_")
        req = t.get("request", {})
        exp = t.get("expected_response", {})
        lines += [
            f"def test_{fn_name}():",
            f"    \"\"\"{t.get('description', t['title'])}\"\"\"",
            f"    response = requests.{req.get('method', 'GET').lower()}(",
            f"        BASE_URL + \"{req.get('path', '/')}\",",
        ]
        if req.get("headers"):
            lines.append(f"        headers={req['headers']},")
        if req.get("body"):
            lines.append(f"        json={req['body']},")
        lines += [
            "    )",
            f"    assert response.status_code == {exp.get('status_code', 200)}",
        ]
        for contains in exp.get("body_contains", []):
            lines.append(f'    assert "{contains}" in response.text')
        lines.append("")
    return "\n".join(lines)


def _generate_gherkin_service_tests(tests: list) -> str:
    lines = ["Feature: AI Üretimi Servis Testleri", ""]
    for t in tests:
        req = t.get("request", {})
        exp = t.get("expected_response", {})
        tags = "@" + " @".join(t.get("tags", "").split(",")) if t.get("tags") else ""
        lines += [
            f"  {tags}".rstrip(),
            f"  Scenario: {t['title']}",
            f"    Given servis endpoint \"{req.get('path', '/')}\" hazır",
            f"    When {req.get('method', 'GET')} isteği gönderilir",
            f"    Then yanıt kodu {exp.get('status_code', 200)} olmalıdır",
            "",
        ]
    return "\n".join(lines)


def _generate_postman_collection(tests: list) -> dict:
    items = []
    for t in tests:
        req = t.get("request", {})
        items.append(
            {
                "name": t["title"],
                "request": {
                    "method": req.get("method", "GET"),
                    "url": {
                        "raw": "{{BASE_URL}}" + req.get("path", "/"),
                        "host": ["{{BASE_URL}}"],
                        "path": req.get("path", "/").split("/"),
                    },
                    "header": [{"key": k, "value": v} for k, v in req.get("headers", {}).items()],
                    "body": (
                        {
                            "mode": "raw",
                            "raw": json.dumps(req.get("body", {}), ensure_ascii=False),
                            "options": {"raw": {"language": "json"}},
                        }
                        if req.get("body")
                        else None
                    ),
                },
                "response": [],
            }
        )
    return {
        "info": {
            "name": "AI Üretimi Servis Testleri",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": items,
    }
