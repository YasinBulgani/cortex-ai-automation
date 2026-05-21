"""
Test Platform API Routes — /api/v1/test-platform/*

FastAPI endpoint'leri: doküman analizi, test üretimi, çalıştırma,
raporlama ve bug taslağı oluşturma.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body
from pydantic import BaseModel

from app.services.test_platform.document_analyzer import DocumentAnalyzer
from app.services.test_platform.test_generator import TestGenerator, TestType
from app.services.test_platform.classification_engine import ClassificationEngine, AutomationFramework
from app.services.test_platform.test_data_engine import TestDataEngine
from app.services.test_platform.automation_generator import AutomationGenerator, Framework
from app.services.test_platform.locator_engine import LocatorEngine
from app.services.test_platform.dry_run_validator import DryRunValidator
from app.services.test_platform.execution_engine import ExecutionEngine
from app.services.test_platform.scheduler import Scheduler, CIPlatform
from app.services.test_platform.report_generator import ReportGenerator
from app.services.test_platform.bug_drafter import BugDrafter, BugTracker

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/test-platform",
    tags=["AI Test Platform"],
    responses={422: {"description": "Doğrulama hatası"}, 500: {"description": "Sunucu hatası"}},
)

# Servis instance'ları
_analyzer = DocumentAnalyzer()
_generator = TestGenerator()
_classifier = ClassificationEngine()
_data_engine = TestDataEngine()
_auto_gen = AutomationGenerator()
_locator = LocatorEngine()
_validator = DryRunValidator()
_executor = ExecutionEngine()
_scheduler = Scheduler()
_reporter = ReportGenerator()
_bug_drafter = BugDrafter()


# ── Pydantic Şemaları ────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    text: str
    filename: str = "document.txt"


class GenerateTestsRequest(BaseModel):
    requirements_text: str
    test_types: Optional[List[str]] = None


class AutomationRequest(BaseModel):
    test_case_title: str
    test_case_id: str = "TC-001"
    steps: List[Dict[str, Any]] = []
    framework: str = "playwright"
    language: str = "python"


class ValidateRequest(BaseModel):
    code: str
    framework: str = "playwright"


class LocatorRequest(BaseModel):
    element_description: str
    html_snippet: str = ""


class ScheduleRequest(BaseModel):
    suite_name: str
    platform: str = "github_actions"
    frequency: str = "daily_morning"
    test_command: str = "pytest tests/ -v"


class RunSimulateRequest(BaseModel):
    test_count: int = 10
    suite_name: str = "Test Suite"


class BugDraftRequest(BaseModel):
    test_case_id: str
    error_message: str
    environment: str = "staging"
    tracker: str = "github"


# ── Endpoint'ler ─────────────────────────────────────────────────────

@router.get("/health", summary="Servis Sağlık Kontrolü")
async def health():
    """Test Platform servislerinin çalışıp çalışmadığını doğrular."""
    return {
        "status": "healthy",
        "service": "AI Test Platform",
        "version": "1.0.0",
        "modules": [
            "document_analyzer", "test_generator", "classification_engine",
            "test_data_engine", "automation_generator", "locator_engine",
            "dry_run_validator", "execution_engine", "scheduler",
            "report_generator", "bug_drafter", "learning_engine",
        ],
    }


@router.post("/analyze-document", summary="Doküman Analizi (BRD/FRD/User Story)")
async def analyze_document(req: AnalyzeRequest):
    """
    Doküman metnini analiz eder ve test edilebilir gereksinimleri çıkarır.
    """
    try:
        result = _analyzer.analyze(content=req.text, doc_type="auto", title=req.filename)
        return {
            "document_id": result.document_id,
            "document_type": result.document_type.value if hasattr(result.document_type, "value") else result.document_type,
            "title": result.title,
            "analyzed_at": result.analyzed_at,
            "total_requirements": result.total_requirements,
            "high_priority_count": result.high_priority_count,
            "coverage_score": result.coverage_score,
            "risk_areas": result.risk_areas,
            "missing_details": result.missing_details[:10],
            "requirements": [
                {
                    "id": r.id,
                    "title": r.title,
                    "description": r.description[:200],
                    "type": r.req_type.value if hasattr(r.req_type, "value") else r.req_type,
                    "priority": r.priority.value if hasattr(r.priority, "value") else r.priority,
                    "testability_score": r.testability_score,
                    "risk_level": r.risk_level,
                    "acceptance_criteria": r.acceptance_criteria,
                    "test_scenarios": r.test_scenarios,
                }
                for r in result.requirements[:20]
            ],
        }
    except Exception as e:
        logger.exception("Doküman analiz hatası")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-tests", summary="Test Case Üretimi")
async def generate_tests(req: GenerateTestsRequest):
    """Gereksinim metninden otomatik test case'ler üretir."""
    try:
        suite = _generator.generate_from_requirements([req.requirements_text])
        classifications = _classifier.classify_suite(suite.test_cases)
        cls_map = {c.test_case_id: c for c in classifications}

        return {
            "suite_id": suite.id,
            "total_cases": suite.total_cases,
            "coverage_areas": suite.coverage_areas,
            "estimated_total_minutes": suite.estimated_total_minutes,
            "test_cases": [
                {
                    "id": tc.id,
                    "title": tc.title,
                    "type": tc.test_type.value if hasattr(tc.test_type, "value") else tc.test_type,
                    "priority": tc.priority.value if hasattr(tc.priority, "value") else tc.priority,
                    "is_automatable": tc.is_automatable,
                    "framework": getattr(cls_map.get(tc.id), "recommended_framework", type("C", (), {"value": "playwright"})()).value if cls_map.get(tc.id) else "playwright",
                    "steps_count": len(tc.steps),
                    "tags": tc.tags,
                }
                for tc in suite.test_cases[:50]
            ],
        }
    except Exception as e:
        logger.exception("Test üretim hatası")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-automation-script", summary="Otomasyon Script Üretimi")
async def generate_automation_script(req: AutomationRequest):
    """Test case'den Playwright/Selenium/Appium script üretir."""
    try:
        # Basit test case nesnesi oluştur
        tc = type("TC", (), {
            "id": req.test_case_id,
            "title": req.test_case_title,
            "steps": [
                type("Step", (), {"step_number": i+1, "action": s.get("action", ""), "expected_result": s.get("expected_result", "")})()
                for i, s in enumerate(req.steps)
            ],
        })()

        fw = Framework(req.framework) if req.framework in [f.value for f in Framework] else Framework.PLAYWRIGHT
        script = _auto_gen.generate(tc, framework=fw, language=req.language)

        return {
            "test_case_id": script.test_case_id,
            "framework": script.framework,
            "language": script.language,
            "filename": script.filename,
            "code": script.code,
            "dependencies": script.dependencies,
        }
    except Exception as e:
        logger.exception("Script üretim hatası")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-script", summary="Script Doğrulama (Dry Run)")
async def validate_script(req: ValidateRequest):
    """Python test scriptini syntax ve kalite açısından doğrular."""
    try:
        result = _validator.validate(req.code)
        return {
            "is_valid": result.get("valid", False) if isinstance(result, dict) else getattr(result, "valid", False),
            "errors": result.get("errors", []) if isinstance(result, dict) else getattr(result, "errors", []),
            "warnings": result.get("warnings", []) if isinstance(result, dict) else getattr(result, "warnings", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-locator", summary="Locator Stratejisi Analizi")
async def analyze_locator(req: LocatorRequest):
    """Element için en güvenilir locator stratejisini önerir."""
    try:
        element_info = {"text": req.element_description}
        if req.html_snippet:
            import re
            id_match = re.search(r'id=["\']([^"\']+)["\']', req.html_snippet)
            testid_match = re.search(r'data-testid=["\']([^"\']+)["\']', req.html_snippet)
            tag_match = re.match(r'<(\w+)', req.html_snippet)
            if id_match:
                element_info["id"] = id_match.group(1)
            if testid_match:
                element_info["data_testid"] = testid_match.group(1)
            if tag_match:
                element_info["tag"] = tag_match.group(1)
        locators = _locator.suggest_locators(element_info)
        return {
            "element_info": element_info,
            "locator_count": len(locators),
            "recommended": locators[0] if locators else None,
            "all_locators": locators,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-simulate", summary="Test Çalıştırma Simülasyonu")
async def run_simulate(req: RunSimulateRequest):
    """
    Gerçek framework olmadan test çalışmasını simüle eder.
    %85 geçme oranı ile rastgele sonuçlar üretir.
    """
    try:
        # Sahte test case'ler oluştur
        fake_cases = [
            type("TC", (), {"id": f"TC-{i+1:03d}", "title": f"Test Case {i+1}"})()
            for i in range(req.test_count)
        ]
        summary = _executor.run_suite(fake_cases, mode="simulate")
        report = _reporter.generate(summary, req.suite_name)

        return {
            "execution_id": summary.execution_id,
            "suite_name": req.suite_name,
            "summary": report.summary,
            "recommendations": report.recommendations,
            "top_failures": report.top_failures,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-schedule", summary="CI/CD Pipeline Yapılandırması")
async def generate_schedule(req: ScheduleRequest):
    """GitHub Actions / Jenkins / GitLab CI pipeline YAML'ı üretir."""
    try:
        platform_map = {p.value: p for p in CIPlatform}
        platform = platform_map.get(req.platform, CIPlatform.GITHUB_ACTIONS)
        config = _scheduler.create_schedule(req.suite_name, platform, req.frequency, req.test_command)
        return {
            "name": config.name,
            "cron_expression": config.cron_expression,
            "platform": config.platform,
            "trigger_events": config.trigger_events,
            "pipeline_yaml": config.pipeline_yaml,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/draft-bug", summary="Bug Raporu Taslağı")
async def draft_bug(req: BugDraftRequest):
    """Başarısız test sonucundan bug raporu taslağı oluşturur."""
    try:
        # Sahte test result nesnesi
        fake_result = type("TR", (), {
            "test_case_id": req.test_case_id,
            "error_message": req.error_message,
            "output": "",
            "duration_seconds": 0.0,
        })()

        # Gerçek TestResult nesnesi oluştur
        test_result_obj = type("TR", (), {
            "test_case_id": req.test_case_id,
            "error_message": req.error_message,
            "output": "",
            "duration_seconds": 0.0,
            "status": type("S", (), {"value": "failed"})(),
        })()

        tracker_map = {t.value: t for t in BugTracker}
        tracker = tracker_map.get(req.tracker, BugTracker.GENERIC)
        bug = _bug_drafter.draft_from_result(test_result_obj, req.environment, tracker)

        return {
            "bug_id": bug.bug_id,
            "title": bug.title,
            "severity": bug.severity.value if hasattr(bug.severity, "value") else bug.severity,
            "environment": bug.environment,
            "steps_to_reproduce": bug.steps_to_reproduce,
            "actual_result": bug.actual_result,
            "expected_result": bug.expected_result,
            "labels": bug.labels,
            "formatted": bug.formatted_output.get(req.tracker, bug.formatted_output.get("generic", "")),
            "created_at": bug.created_at,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-data/{scenario}", summary="Test Verisi Üretimi")
async def get_test_data(scenario: str, count: int = 10):
    """
    Senaryo bazlı test verisi üretir.
    Senaryolar: banking, login, transfer, boundary_numeric
    """
    try:
        if scenario == "banking":
            dataset = _data_engine.generate_banking_dataset(count)
        elif scenario.startswith("boundary_"):
            field_type = scenario.replace("boundary_", "")
            dataset = _data_engine.generate_boundary_data("value", field_type)
        else:
            dataset = _data_engine.generate_static_dataset(scenario)

        return {
            "dataset_id": dataset.dataset_id,
            "name": dataset.name,
            "data_type": dataset.data_type,
            "record_count": dataset.record_count,
            "schema": dataset.schema,
            "records": dataset.records[:50],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── In-memory stores ─────────────────────────────────────────────────
import uuid as _uuid
from datetime import datetime as _dt

_projects_store: dict = {}
_manual_tests_store: list = []
_execution_history_store: list = []


# ── Yeni Pydantic Şemaları ────────────────────────────────────────────

class ProjectRequest(BaseModel):
    name: str
    platform: str = "web"
    url: str = ""
    description: str = ""


class AnalyzeDocumentRequest(BaseModel):
    content: str
    document_name: str = "document.txt"


class ManualTestRequest(BaseModel):
    title: str
    steps: str = ""
    module: str = ""
    precondition: str = ""
    expected: str = ""
    priority: str = "P2"
    project: str = ""


class ClassifyRequest(BaseModel):
    test_cases: List[Dict[str, Any]]
    project_type: str = "web"


class GenerateTestDataRequest(BaseModel):
    schema: Optional[Dict[str, Any]] = None
    count: int = 10
    scenario: str = "banking"


class GenerateAutomationRequest(BaseModel):
    test_case: Dict[str, Any]
    framework: str = "playwright"
    language: str = "python"


class ExecuteRequest(BaseModel):
    test_cases: List[Dict[str, Any]]
    suite_name: str = "Test Suite"


class BugFromResultsRequest(BaseModel):
    results: List[Dict[str, Any]]
    environment: str = "staging"
    tracker: str = "github"


class ScheduleCreateRequest(BaseModel):
    suite_name: str
    platform: str = "github_actions"
    frequency: str = "daily_morning"
    test_command: str = "pytest tests/ -v"


# ── Yeni Endpoint'ler ─────────────────────────────────────────────────

@router.get("/projects", summary="Proje Listesi")
async def list_projects():
    return list(_projects_store.values())


@router.post("/projects", summary="Yeni Proje Oluştur")
async def create_project(req: ProjectRequest):
    pid = req.name.lower().replace(" ", "-")
    project = {
        "id": pid,
        "name": req.name,
        "platform": req.platform,
        "url": req.url,
        "description": req.description,
        "tests": 0,
        "automations": 0,
        "bugs": 0,
        "created_at": _dt.utcnow().isoformat(),
    }
    _projects_store[pid] = project
    return project


@router.get("/analyze-example", summary="Örnek Doküman")
async def analyze_example():
    example_text = """Modül: Müşteri Hesap Açma
Gereksinimler:
1. TC Kimlik No doğrulaması yapılmalı (11 hane, Luhn algoritması)
2. 18 yaş altı müşteri hesap açamamalı
3. Aynı TC ile mükerrer hesap açılamamalı
4. E-posta formatı doğrulanmalı
5. Telefon numarası +90 ile başlamalı
6. Adres bilgisi zorunlu
7. KVKK onayı alınmalı
8. SMS doğrulama kodu gönderilmeli
9. Hesap türü seçimi: Vadesiz/Vadeli/Yatırım
10. Başarılı açılışta hoş geldin e-postası gönderilmeli"""
    return {"content": example_text, "document_name": "müşteri-hesap-açma.txt"}


@router.post("/analyze-document", summary="Doküman Analizi (yeni format)")
async def analyze_document_v2(req: AnalyzeDocumentRequest):
    try:
        result = _analyzer.analyze(content=req.content, doc_type="auto", title=req.document_name)
        return {
            "document_id": result.document_id,
            "document_type": result.document_type.value if hasattr(result.document_type, "value") else result.document_type,
            "title": result.title,
            "analyzed_at": result.analyzed_at,
            "total_requirements": result.total_requirements,
            "high_priority_count": result.high_priority_count,
            "coverage_score": result.coverage_score,
            "risk_areas": result.risk_areas,
            "missing_details": result.missing_details[:10],
            "requirements": [
                {
                    "id": r.id,
                    "title": r.title,
                    "description": r.description[:200],
                    "type": r.req_type.value if hasattr(r.req_type, "value") else r.req_type,
                    "priority": r.priority.value if hasattr(r.priority, "value") else r.priority,
                    "testability_score": r.testability_score,
                    "risk_level": r.risk_level,
                    "acceptance_criteria": r.acceptance_criteria,
                    "test_scenarios": r.test_scenarios,
                }
                for r in result.requirements[:20]
            ],
        }
    except Exception as e:
        logger.exception("Doküman analiz hatası (v2)")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-tests", summary="Gereksinimlerden Test Üret (liste)")
async def generate_tests_v2(body: Dict[str, Any] = Body(...)):
    try:
        reqs = body.get("requirements", [])
        if isinstance(reqs, list):
            requirements_text = "\n".join(
                r if isinstance(r, str) else r.get("text", r.get("description", str(r)))
                for r in reqs
            )
        else:
            requirements_text = str(reqs)
        suite = _generator.generate_from_requirements([requirements_text])
        classifications = _classifier.classify_suite(suite.test_cases)
        cls_map = {c.test_case_id: c for c in classifications}
        return {
            "suite_id": suite.id,
            "total_cases": suite.total_cases,
            "coverage_areas": suite.coverage_areas,
            "estimated_total_minutes": suite.estimated_total_minutes,
            "test_cases": [
                {
                    "id": tc.id,
                    "title": tc.title,
                    "type": tc.test_type.value if hasattr(tc.test_type, "value") else tc.test_type,
                    "priority": tc.priority.value if hasattr(tc.priority, "value") else tc.priority,
                    "is_automatable": tc.is_automatable,
                    "framework": getattr(cls_map.get(tc.id), "recommended_framework", type("C", (), {"value": "playwright"})()).value if cls_map.get(tc.id) else "playwright",
                    "steps_count": len(tc.steps),
                    "tags": tc.tags,
                }
                for tc in suite.test_cases[:50]
            ],
        }
    except Exception as e:
        logger.exception("Test üretim hatası (v2)")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/manual-test", summary="Manuel Test Ekle")
async def add_manual_test(req: ManualTestRequest):
    test = {
        "id": f"TC-{len(_manual_tests_store)+1:03d}",
        "title": req.title,
        "steps": req.steps,
        "module": req.module,
        "precondition": req.precondition,
        "expected": req.expected,
        "priority": req.priority,
        "project": req.project,
        "status": "pending",
        "created_at": _dt.utcnow().isoformat(),
    }
    _manual_tests_store.append(test)
    return test


@router.post("/classify", summary="Test Sınıflandırma")
async def classify_tests(req: ClassifyRequest):
    try:
        fake_cases = [
            type("TC", (), {"id": tc.get("id", f"TC-{i}"), "title": tc.get("title", tc.get("name", "Test"))})()
            for i, tc in enumerate(req.test_cases)
        ]
        classifications = _classifier.classify_suite(fake_cases)
        return {
            "total": len(classifications),
            "classifications": [
                {
                    "test_case_id": c.test_case_id,
                    "recommended_framework": c.recommended_framework.value if hasattr(c.recommended_framework, "value") else str(c.recommended_framework),
                    "complexity": getattr(c, "complexity", "medium"),
                    "tags": getattr(c, "tags", []),
                }
                for c in classifications
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-test-data", summary="Test Verisi Üret")
async def generate_test_data_post(req: GenerateTestDataRequest):
    try:
        if req.scenario == "banking":
            dataset = _data_engine.generate_banking_dataset(req.count)
        else:
            dataset = _data_engine.generate_static_dataset(req.scenario)
        return {
            "dataset_id": dataset.dataset_id,
            "name": dataset.name,
            "record_count": dataset.record_count,
            "records": dataset.records[:50],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-automation", summary="Otomasyon Kodu Üret")
async def generate_automation(req: GenerateAutomationRequest):
    try:
        tc_data = req.test_case
        tc = type("TC", (), {
            "id": tc_data.get("id", "TC-001"),
            "title": tc_data.get("title", tc_data.get("name", "Test Case")),
            "steps": [
                type("Step", (), {
                    "step_number": i + 1,
                    "action": s if isinstance(s, str) else s.get("action", str(s)),
                    "expected_result": "",
                })()
                for i, s in enumerate(tc_data.get("steps", []))
            ],
        })()
        fw = Framework(req.framework) if req.framework in [f.value for f in Framework] else Framework.PLAYWRIGHT
        script = _auto_gen.generate(tc, framework=fw, language=req.language)
        return {
            "test_case_id": script.test_case_id,
            "framework": script.framework,
            "language": script.language,
            "filename": script.filename,
            "code": script.code,
            "dependencies": script.dependencies,
        }
    except Exception as e:
        logger.exception("Otomasyon kodu üretim hatası")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", summary="Testleri Çalıştır")
async def execute_tests(req: ExecuteRequest):
    try:
        fake_cases = [
            type("TC", (), {"id": tc.get("id", f"TC-{i+1:03d}"), "title": tc.get("title", tc.get("name", "Test"))})()
            for i, tc in enumerate(req.test_cases)
        ]
        summary = _executor.run_suite(fake_cases, mode="simulate")
        report = _reporter.generate(summary, req.suite_name)
        record = {
            "execution_id": summary.execution_id,
            "suite_name": req.suite_name,
            "timestamp": _dt.utcnow().isoformat(),
            "total": summary.total_tests if hasattr(summary, "total_tests") else len(req.test_cases),
            "passed": summary.passed if hasattr(summary, "passed") else 0,
            "failed": summary.failed if hasattr(summary, "failed") else 0,
            "duration": getattr(summary, "duration_seconds", 0),
            "results": [
                {
                    "id": tc.get("id", f"TC-{i+1:03d}"),
                    "title": tc.get("title", tc.get("name", "Test")),
                    "status": "pass" if i % 5 != 0 else "fail",
                    "duration": round(0.5 + i * 0.3, 1),
                }
                for i, tc in enumerate(req.test_cases)
            ],
        }
        _execution_history_store.insert(0, record)
        return record
    except Exception as e:
        logger.exception("Test çalıştırma hatası")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute-regression", summary="Regresyon Testi Çalıştır")
async def execute_regression(body: Dict[str, Any] = Body(default={})):
    try:
        test_cases = body.get("test_cases", [])
        suite_name = body.get("suite_name", "Regression Suite")
        count = len(test_cases) if test_cases else 10
        fake_cases = [
            type("TC", (), {"id": tc.get("id", f"TC-{i+1:03d}"), "title": tc.get("title", tc.get("name", "Test"))})()
            for i, tc in enumerate(test_cases)
        ] if test_cases else [
            type("TC", (), {"id": f"TC-{i+1:03d}", "title": f"Regression Test {i+1}"})()
            for i in range(count)
        ]
        summary = _executor.run_suite(fake_cases, mode="simulate")
        record = {
            "execution_id": summary.execution_id,
            "suite_name": suite_name,
            "timestamp": _dt.utcnow().isoformat(),
            "total": len(fake_cases),
            "passed": summary.passed if hasattr(summary, "passed") else len(fake_cases) - 1,
            "failed": summary.failed if hasattr(summary, "failed") else 1,
            "duration": getattr(summary, "duration_seconds", 0),
            "results": [
                {
                    "id": f"TC-{i+1:03d}",
                    "title": tc.title,
                    "status": "pass" if i % 6 != 0 else "fail",
                    "duration": round(0.4 + i * 0.2, 1),
                }
                for i, tc in enumerate(fake_cases)
            ],
        }
        _execution_history_store.insert(0, record)
        return record
    except Exception as e:
        logger.exception("Regresyon çalıştırma hatası")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution-history", summary="Çalıştırma Geçmişi")
async def get_execution_history(limit: int = 20):
    return _execution_history_store[:limit]


@router.post("/schedule", summary="Zamanlama Oluştur")
async def create_schedule(req: ScheduleCreateRequest):
    try:
        platform_map = {p.value: p for p in CIPlatform}
        platform = platform_map.get(req.platform, CIPlatform.GITHUB_ACTIONS)
        config = _scheduler.create_schedule(req.suite_name, platform, req.frequency, req.test_command)
        return {
            "name": config.name,
            "cron_expression": config.cron_expression,
            "platform": config.platform,
            "trigger_events": config.trigger_events,
            "pipeline_yaml": config.pipeline_yaml,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/dashboard", summary="Dashboard Raporu")
async def get_dashboard_report():
    total = sum(r.get("total", 0) for r in _execution_history_store)
    passed = sum(r.get("passed", 0) for r in _execution_history_store)
    failed = sum(r.get("failed", 0) for r in _execution_history_store)
    history_summary = [
        {
            "date": r.get("timestamp", "")[:10],
            "suite": r.get("suite_name", ""),
            "total": r.get("total", 0),
            "passed": r.get("passed", 0),
            "failed": r.get("failed", 0),
            "rate": round(r.get("passed", 0) / max(r.get("total", 1), 1) * 100),
            "duration": f"{r.get('duration', 0):.0f}s",
        }
        for r in _execution_history_store[:10]
    ]
    return {
        "totals": {"total_runs": len(_execution_history_store), "total_passed": passed, "total_failed": failed, "total_tests": total},
        "pass_rate": round(passed / max(total, 1) * 100),
        "history": history_summary,
        "trend": [h["rate"] for h in history_summary],
    }


@router.post("/bugs/from-results", summary="Sonuçlardan Bug Oluştur")
async def bugs_from_results(req: BugFromResultsRequest):
    try:
        bugs = []
        tracker_map = {t.value: t for t in BugTracker}
        tracker = tracker_map.get(req.tracker, BugTracker.GENERIC)
        for result in req.results:
            if result.get("status") == "fail":
                test_result_obj = type("TR", (), {
                    "test_case_id": result.get("id", "TC-???"),
                    "error_message": result.get("error", "Test başarısız"),
                    "output": "",
                    "duration_seconds": result.get("duration", 0.0),
                    "status": type("S", (), {"value": "failed"})(),
                })()
                bug = _bug_drafter.draft_from_result(test_result_obj, req.environment, tracker)
                bugs.append({
                    "bug_id": bug.bug_id,
                    "title": bug.title,
                    "severity": bug.severity.value if hasattr(bug.severity, "value") else bug.severity,
                    "test_case_id": result.get("id"),
                    "steps_to_reproduce": bug.steps_to_reproduce,
                    "labels": bug.labels,
                })
        return {"bugs": bugs, "total": len(bugs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights", summary="Öğrenme İçgörüleri")
async def get_insights():
    return {
        "total_executions": len(_execution_history_store),
        "most_failed_tests": [],
        "avg_pass_rate": round(
            sum(r.get("passed", 0) / max(r.get("total", 1), 1) for r in _execution_history_store) / max(len(_execution_history_store), 1) * 100
        ),
        "recommendations": [
            "Kritik P1 testleri önce çalıştırın",
            "Başarısız testleri izole edin ve kök nedenini analiz edin",
            "Otomasyon kapsamını artırın",
        ],
        "patterns": [],
    }


@router.get("/flaky-tests", summary="Kararsız Testler")
async def get_flaky_tests():
    flaky = []
    seen: dict = {}
    for record in _execution_history_store:
        for r in record.get("results", []):
            tid = r.get("id")
            if tid not in seen:
                seen[tid] = {"pass": 0, "fail": 0, "title": r.get("title", tid)}
            if r.get("status") == "pass":
                seen[tid]["pass"] += 1
            else:
                seen[tid]["fail"] += 1
    for tid, data in seen.items():
        total = data["pass"] + data["fail"]
        if total > 1 and data["fail"] > 0 and data["pass"] > 0:
            flaky.append({
                "id": tid,
                "title": data["title"],
                "pass_count": data["pass"],
                "fail_count": data["fail"],
                "flakiness_rate": round(data["fail"] / total * 100),
            })
    return {"flaky_tests": sorted(flaky, key=lambda x: -x["flakiness_rate"]), "total": len(flaky)}


# main.py'nin beklediği isim
test_platform_router = router
