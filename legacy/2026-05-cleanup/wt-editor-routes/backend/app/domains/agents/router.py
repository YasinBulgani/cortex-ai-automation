"""Agent orchestration endpoints — genel pipeline + banking QA ekibi + full pipeline."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.infra.database import get_db
from app.infra.models import User
from app.domains.tspm.models import TspmProject, TspmProjectMember
from app.domains.agents.analytics_service import (
    get_heal_history_data,
    get_heal_stats_data,
    get_llm_trace_stats_data,
    get_llm_traces_data,
    get_locator_trend_data,
)
from app.domains.agents.orchestration_service import (
    cancel_all_agents_run,
    cancel_banking_team_run,
    cancel_full_pipeline_run,
    get_all_agents_logs,
    get_all_agents_status,
    get_banking_pipeline_logs,
    get_banking_pipeline_report,
    get_banking_pipeline_status,
    get_banking_scheduler_info,
    get_banking_system_health,
    get_full_pipeline_logs,
    get_full_pipeline_report,
    get_full_pipeline_status,
    quick_start_full_pipeline,
    start_all_agents_run,
    start_banking_team_run,
    start_full_pipeline_run,
    trigger_banking_team_now,
)
from app.domains.agents.banking_team.heal_schemas import (
    HealRequest,
    HealResponse,
    HealDetailEntry,
    HealHistoryResponse,
    HealHistoryEntry,
    HealStatsResponse,
)
from app.domains.agents.banking_team.locator_schemas import (
    FallbackResolveRequest,
    FallbackResolveResponse,
    FallbackStrategyResult,
    StabilityAnalyzeRequest,
    StabilityAnalyzeResponse,
    StabilityDetail,
    ImproveSuggestRequest,
    ImproveSuggestResponse,
    POMGenerateRequest,
    POMGenerateResponse,
    BreakagePredictRequest,
    BreakagePredictResponse,
    TrendAnalysisResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]


def _is_admin_user(user: User) -> bool:
    for role in user.roles:
        for role_permission in role.permissions:
            if role_permission.permission == "admin.*":
                return True
    return False


def _require_project_access(db: Session, user: User, project_id: str) -> str:
    project_id = project_id.strip()
    if not project_id:
        raise HTTPException(400, "project_id gerekli")
    if db.get(TspmProject, project_id) is None:
        raise HTTPException(404, "Proje bulunamadi")
    if _is_admin_user(user):
        return project_id
    is_member = db.scalar(
        select(func.count()).where(
            TspmProjectMember.project_id == project_id,
            TspmProjectMember.user_id == user.id,
        )
    )
    if not is_member:
        raise HTTPException(403, "Bu projeye erisim yetkiniz yok")
    return project_id


def _require_scoped_project_id(db: Session, user: User, project_id: str | None) -> str:
    if project_id and project_id.strip():
        return _require_project_access(db, user, project_id)
    raise HTTPException(400, "project_id gerekli")


class RunAllRequest(BaseModel):
    project_id: Optional[str] = None


class RunAllResponse(BaseModel):
    run_id: str
    message: str


@router.post("/run-all", response_model=RunAllResponse)
async def start_all_agents(
    body: RunAllRequest,
    bg: BackgroundTasks,
    db: DB,
    user: CurrentUser,
):
    if body.project_id:
        _require_project_access(db, user, body.project_id)
    elif not _is_admin_user(user):
        raise HTTPException(400, "project_id gerekli")
    return RunAllResponse(**start_all_agents_run(bg, body.project_id))


@router.get("/status")
def get_pipeline_status(user: CurrentUser):
    return get_all_agents_status()


@router.get("/logs")
def get_pipeline_logs(user: CurrentUser, since: int = 0):
    """Return logs starting from index `since` for incremental polling."""
    return get_all_agents_logs(since)


@router.post("/cancel")
def cancel_pipeline(user: CurrentUser):
    return cancel_all_agents_run()


# ═══════════════════════════════════════════════════════════════════════════════
# Banking QA Ekibi Endpoint'leri
# ═══════════════════════════════════════════════════════════════════════════════

class BankingRunRequest(BaseModel):
    description: str = Field(
        default="Bankacılık uygulaması",
        description="Sistem açıklaması (örn. 'Medifim internet bankacılığı')",
    )
    db_schema: str = Field(default="", description="DB şeması veya tablo listesi")
    api_docs: str = Field(default="", description="API endpoint dokümantasyonu")
    logs: str = Field(default="", description="Örnek log satırları")
    regulations: list[str] = Field(
        default=["BDDK", "PCI-DSS", "MASAK", "KYC", "KVKK"],
        description="Uygulanacak regülasyonlar",
    )
    focus_module: str = Field(default="", description="Öncelikli modül (opsiyonel)")
    total_cycles: int = Field(default=3, ge=1, le=10, description="Kaç öğrenme döngüsü çalışsın")


@router.post("/banking/run")
async def start_banking_team(
    body: BankingRunRequest,
    bg: BackgroundTasks,
    user: CurrentUser,
):
    """Banking QA ekibini başlat. Ollama ile tamamen local çalışır."""
    return start_banking_team_run(
        bg,
        input_data=body.model_dump(exclude={"total_cycles"}),
        total_cycles=body.total_cycles,
    )


@router.get("/banking/status")
def get_banking_status(user: CurrentUser):
    """Banking pipeline'ının anlık durumunu döndür."""
    return get_banking_pipeline_status()


@router.get("/banking/logs")
def get_banking_logs(user: CurrentUser, since: int = 0):
    """Son logları artımlı olarak döndür (polling için)."""
    return get_banking_pipeline_logs(since)


@router.get("/banking/report")
def get_banking_report(user: CurrentUser):
    """Tamamlanan pipeline'ın final raporunu döndür."""
    return get_banking_pipeline_report()


@router.post("/banking/cancel")
def cancel_banking_pipeline(user: CurrentUser):
    """Çalışan banking pipeline'ını iptal et."""
    return cancel_banking_team_run()


@router.post("/banking/trigger-now")
async def trigger_banking_now(
    bg: BackgroundTasks,
    user: CurrentUser,
    cycles: int = 2,
):
    """
    Ekibi hemen başlat — sıfır müdahale.
    ProjectScanner projeyi otomatik tarar, hiçbir girdi gerekmez.
    """
    return trigger_banking_team_now(bg, cycles)


@router.get("/banking/scheduler")
def get_scheduler_info(user: CurrentUser):
    """Scheduler durumu ve sonraki çalışma zamanı."""
    return get_banking_scheduler_info()


@router.get("/banking/health")
def banking_system_health(user: CurrentUser):
    """
    7/24 sistem sağlık durumu.
    Watchdog bu endpoint'i izler.
    """
    return get_banking_system_health()


# ═══════════════════════════════════════════════════════════════════════════════
# Full Pipeline — Analizden Otomasyona Uçtan Uca
# ═══════════════════════════════════════════════════════════════════════════════

class PipelineStartRequest(BaseModel):
    """Pipeline başlatma isteği."""
    project_name: str = Field(
        ...,
        description="Proje adı (TSPM'de oluşturulur/bulunur)",
        examples=["İnternet Bankacılığı"],
    )
    target_url: Optional[str] = Field(
        default=None,
        description="Hedef uygulama URL'si (crawl için)",
        examples=["https://demo.bank.com"],
    )
    description: str = Field(
        default="",
        description="Proje/modül açıklaması",
    )
    cycles: int = Field(
        default=2, ge=1, le=10,
        description="Öğrenme döngüsü sayısı",
    )
    regulations: list[str] = Field(
        default=["BDDK", "KVKK"],
        description="Uygulanacak regülasyonlar",
    )
    generate_bdd: bool = Field(default=True, description="BDD feature dosyaları üret")
    generate_playwright: bool = Field(default=True, description="Playwright test kodları üret")
    generate_api_tests: bool = Field(default=True, description="API test kodları üret")
    run_tests: bool = Field(default=True, description="Üretilen testleri koş")
    auto_heal: bool = Field(default=True, description="Kırık testleri otomatik onar")
    crawl_max_pages: int = Field(default=10, ge=1, le=50, description="Crawl max sayfa sayısı")
    max_quality_retries: int = Field(default=2, ge=0, le=5, description="Kalite kapısı retry sayısı")


class PipelineStartResponse(BaseModel):
    run_id: str
    project_name: str
    message: str
    total_cycles: int


@router.post("/pipeline/start", response_model=PipelineStartResponse)
async def start_full_pipeline(
    body: PipelineStartRequest,
    bg: BackgroundTasks,
    db: DB,
    user: CurrentUser,
):
    """
    Analizden otomasyona uçtan uca pipeline başlat.

    Akış: Proje kurulum → Crawl → Analiz → Senaryo → Kod → Test → Heal → Öğrenme → Rapor
    """
    return PipelineStartResponse(
        **start_full_pipeline_run(
            bg,
            db,
            project_name=body.project_name,
            target_url=body.target_url,
            description=body.description,
            cycles=body.cycles,
            regulations=body.regulations,
            generate_bdd=body.generate_bdd,
            generate_playwright=body.generate_playwright,
            generate_api_tests=body.generate_api_tests,
            run_tests=body.run_tests,
            auto_heal=body.auto_heal,
            crawl_max_pages=body.crawl_max_pages,
            max_quality_retries=body.max_quality_retries,
        )
    )


@router.get("/pipeline/status")
def get_pipeline_status_full(user: CurrentUser):
    """Pipeline anlık durum — faz, ilerleme, senaryo sayısı, kalite skoru."""
    return get_full_pipeline_status()


@router.get("/pipeline/logs")
def get_pipeline_logs_full(user: CurrentUser, since: int = 0):
    """Pipeline logları — artımlı polling için `since` parametresi kullan."""
    return get_full_pipeline_logs(since)


@router.get("/pipeline/report")
def get_pipeline_report(user: CurrentUser):
    """Tamamlanan pipeline'ın final raporunu döndür."""
    return get_full_pipeline_report()


@router.post("/pipeline/cancel")
def cancel_full_pipeline(user: CurrentUser):
    """Çalışan pipeline'ı iptal et."""
    return cancel_full_pipeline_run()


@router.post("/pipeline/quick-start")
async def quick_start_pipeline(
    bg: BackgroundTasks,
    db: DB,
    user: CurrentUser,
    project_name: str = "Otomatik Keşif",
    target_url: Optional[str] = None,
):
    """
    Tek satırda pipeline başlat — minimum konfigürasyon.
    Sadece proje adı ve (opsiyonel) URL yeterli.
    """
    return quick_start_full_pipeline(
        bg,
        db,
        project_name=project_name,
        target_url=target_url,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Heal Pipeline Endpoint'leri
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/heal/run", response_model=HealResponse)
async def run_heal_pipeline(
    body: HealRequest,
    bg: BackgroundTasks,
    db: DB,
    user: CurrentUser,
):
    """Kirik testleri otomatik tamir et.

    Playwright MCP oturumu varsa canli DOM ve browser dogrulama kullanilir.
    auto_update=true ile dogrulanan selector'lar otomatik dosyaya yazilir.
    """
    import time as _time
    from pathlib import Path
    from app.domains.agents.banking_team.heal_pipeline import HealPipeline

    t0 = _time.time()

    # Proje kokunu bul
    project_root = Path(__file__).resolve().parents[4]
    scoped_project_id = _require_scoped_project_id(db, user, body.project_id)
    pipeline_obj = HealPipeline(project_root, project_id=scoped_project_id)

    # Test bilgilerini dict listesine cevir
    failed_tests = [t.model_dump() for t in body.failed_tests]

    result = await pipeline_obj.run(
        failed_tests=failed_tests,
        session_id=body.session_id or "",
    )

    # auto_update degilse dosya guncelleme sonuclarini sifirla
    # (pipeline icinde zaten file_updated kontrolu var ama
    #  burada ek guvenlik katmani)
    details = []
    for d in result.details:
        entry = HealDetailEntry(
            file=d.get("file", ""),
            test_name=d.get("test_name", ""),
            broken_selector=d.get("broken_selector", ""),
            new_selector=d.get("new_selector", ""),
            healed=d.get("healed", False),
            strategy=d.get("strategy", ""),
            tier=d.get("tier", ""),
            confidence=d.get("confidence", 0.0),
            verified_in_browser=d.get("verified_in_browser", False),
            live_dom_used=d.get("live_dom_used", False),
            file_updated=d.get("file_updated", False) if body.auto_update else False,
            screenshot_before=d.get("screenshot_before", ""),
            screenshot_after=d.get("screenshot_after", ""),
            error=d.get("error", ""),
        )
        details.append(entry)

    return HealResponse(
        total_broken=result.total_broken,
        healed=result.healed,
        verified=result.verified,
        updated_files=result.updated_files if body.auto_update else 0,
        duration_ms=result.duration_ms,
        details=details,
    )


@router.get("/heal/history", response_model=HealHistoryResponse)
def get_heal_history(user: CurrentUser, db: DB, limit: int = 20, project_id: str = ""):
    """Son heal islemlerini getir (KnowledgeStore'dan)."""
    scoped_project_id = _require_scoped_project_id(db, user, project_id)
    return get_heal_history_data(project_id=scoped_project_id, limit=limit)


@router.get("/heal/stats", response_model=HealStatsResponse)
def get_heal_stats(user: CurrentUser, db: DB, project_id: str = ""):
    """Healing istatistiklerini getir."""
    scoped_project_id = _require_scoped_project_id(db, user, project_id)
    return get_heal_stats_data(project_id=scoped_project_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Locator Intelligence Endpoint'leri
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/locator/resolve", response_model=FallbackResolveResponse)
async def resolve_locator_fallback(
    body: FallbackResolveRequest,
    db: DB,
    user: CurrentUser,
):
    """Kirilan selector icin fallback zincirini calistir.

    Tier-1 (heuristik) → Tier-2 (AI) → Tier-3 (Playwright MCP) sirasiyla dener,
    confidence_threshold'u asan ilk sonucu dondurur.
    """
    import time as _time

    try:
        from app.domains.agents.banking_team.locator_fallback_chain import LocatorFallbackChain

        scoped_project_id = _require_scoped_project_id(db, user, body.project_id)
        t0 = _time.time()
        chain = LocatorFallbackChain(project_id=scoped_project_id)
        result = await chain.resolve(
            selector=body.selector,
            dom_snippet=body.dom_snippet,
            page_url=body.page_url,
            error_message=body.error_message,
            session_id=body.session_id,
            confidence_threshold=body.confidence_threshold,
            context={**body.context, "project_id": scoped_project_id},
        )
        total_ms = int((_time.time() - t0) * 1000)

        # Map chain result to response
        all_results = []
        for r in result.get("results", []):
            all_results.append(FallbackStrategyResult(
                strategy=r.get("strategy", ""),
                selector=r.get("selector", ""),
                confidence=r.get("confidence", 0.0),
                stability_score=r.get("stability_score", 0),
                found=r.get("found", False),
                reason=r.get("reason", ""),
                latency_ms=r.get("latency_ms", 0),
            ))

        return FallbackResolveResponse(
            success=result.get("success", False),
            best_selector=result.get("best_selector"),
            best_strategy=result.get("best_strategy"),
            best_confidence=result.get("best_confidence", 0.0),
            best_stability=result.get("best_stability", 0),
            original_selector=body.selector,
            strategies_tried=len(all_results),
            total_latency_ms=result.get("total_latency_ms", total_ms),
            all_results=all_results,
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="LocatorFallbackChain modulu henuz yuklenmemis.",
        ) from exc
    except Exception as exc:
        logger.exception(
            "Locator fallback resolution failed for project %s",
            body.project_id or "",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fallback zinciri hatasi: {str(exc)[:300]}",
        ) from exc


@router.post("/locator/stability", response_model=StabilityAnalyzeResponse)
async def analyze_locator_stability(
    body: StabilityAnalyzeRequest,
    user: CurrentUser,
):
    """Locator'larin stabilite analizini yap.

    Her locator icin 0-5 arasi skor ve risk seviyesi dondurur.
    """
    try:
        from app.domains.agents.banking_team.locator_intelligence import LocatorIntelligence

        intel = LocatorIntelligence()
        locator_dicts = [loc.model_dump() for loc in body.locators]
        result = await intel.analyze_stability(
            locators=locator_dicts,
            dom_snippet=body.dom_snippet,
        )

        details = []
        for d in result.get("details", []):
            details.append(StabilityDetail(
                selector=d.get("selector", ""),
                name=d.get("name", ""),
                score=d.get("score", 0),
                risk_level=d.get("risk_level", "critical"),
                reasons=d.get("reasons", []),
                suggestion=d.get("suggestion"),
            ))

        raw_improvements = result.get("improvements", [])
        improvements: list[dict] = []
        for improvement in raw_improvements:
            if isinstance(improvement, dict):
                improvements.append(improvement)
            elif isinstance(improvement, str) and improvement.strip():
                improvements.append({"message": improvement.strip()})

        return StabilityAnalyzeResponse(
            total_locators=result.get("total_locators", len(body.locators)),
            healthy=result.get("healthy", 0),
            warning=result.get("warning", 0),
            critical=result.get("critical", 0),
            avg_score=result.get("avg_score", 0.0),
            details=details,
            improvements=improvements,
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="LocatorIntelligence modulu henuz yuklenmemis.",
        ) from exc
    except Exception as exc:
        logger.exception("Locator stability analysis failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stabilite analizi hatasi: {str(exc)[:300]}",
        ) from exc


@router.post("/locator/improve", response_model=ImproveSuggestResponse)
async def suggest_locator_improvements(
    body: ImproveSuggestRequest,
    user: CurrentUser,
):
    """Zayif locator'lar icin iyilestirme onerileri uret."""
    try:
        from app.domains.agents.banking_team.locator_intelligence import LocatorIntelligence

        intel = LocatorIntelligence()
        locator_dicts = [loc.model_dump() for loc in body.locators]
        result = await intel.suggest_improvements(
            locators=locator_dicts,
            dom_snippet=body.dom_snippet,
        )

        from app.domains.agents.banking_team.locator_schemas import ImproveSuggestion as _IS

        suggestions = []
        for s in result.get("suggestions", []):
            suggestions.append(_IS(
                original_selector=s.get("original_selector", ""),
                original_score=s.get("original_score", 0),
                suggested_selector=s.get("suggested_selector", ""),
                suggested_score=s.get("suggested_score", 0),
                improvement_reason=s.get("improvement_reason", ""),
                confidence=s.get("confidence", 0.0),
            ))

        return ImproveSuggestResponse(
            suggestions=suggestions,
            total_improved=result.get("total_improved", len(suggestions)),
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="LocatorIntelligence modulu henuz yuklenmemis.",
        ) from exc
    except Exception as exc:
        logger.exception("Locator improvement suggestion failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Iyilestirme onerisi hatasi: {str(exc)[:300]}",
        ) from exc


@router.post("/locator/pom/generate", response_model=POMGenerateResponse)
async def generate_page_object_model(
    body: POMGenerateRequest,
    user: CurrentUser,
):
    """Sayfa elementlerinden Page Object Model (POM) kodu uret."""
    try:
        from app.domains.agents.banking_team.locator_intelligence import LocatorIntelligence

        intel = LocatorIntelligence()
        result = await intel.generate_page_object(
            page_name=body.page_name,
            page_url=body.page_url,
            elements=body.elements,
            session_id=body.session_id,
            language=body.language,
        )

        return POMGenerateResponse(
            page_name=result.get("page_name", body.page_name),
            language=result.get("language", body.language),
            code=result.get("code", ""),
            element_count=result.get("element_count", 0),
            file_name=result.get("file_name", f"{body.page_name}.ts"),
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="LocatorIntelligence modulu henuz yuklenmemis.",
        ) from exc
    except Exception as exc:
        logger.exception("POM generation failed for page %s", body.page_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"POM uretme hatasi: {str(exc)[:300]}",
        ) from exc


@router.post("/locator/predict", response_model=BreakagePredictResponse)
async def predict_locator_breakage(
    body: BreakagePredictRequest,
    user: CurrentUser,
):
    """Locator'larin kirilma riskini tahmin et."""
    try:
        from app.domains.agents.banking_team.locator_intelligence import LocatorIntelligence

        intel = LocatorIntelligence()
        locator_dicts = [loc.model_dump() for loc in body.locators]
        result = await intel.predict_breakage(
            locators=locator_dicts,
            recent_changes=body.recent_changes,
        )

        from app.domains.agents.banking_team.locator_schemas import BreakagePrediction as _BP

        predictions = []
        for p in result.get("predictions", []):
            predictions.append(_BP(
                selector=p.get("selector", ""),
                name=p.get("name", ""),
                risk_score=p.get("risk_score", 0.0),
                risk_factors=p.get("risk_factors", []),
                recommendation=p.get("recommendation", ""),
            ))

        return BreakagePredictResponse(
            predictions=predictions,
            high_risk_count=result.get("high_risk_count", 0),
            medium_risk_count=result.get("medium_risk_count", 0),
            low_risk_count=result.get("low_risk_count", 0),
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="LocatorIntelligence modulu henuz yuklenmemis.",
        ) from exc
    except Exception as exc:
        logger.exception("Locator breakage prediction failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Kirilma tahmini hatasi: {str(exc)[:300]}",
        ) from exc


@router.get("/locator/trends", response_model=TrendAnalysisResponse)
def get_locator_heal_trends(user: CurrentUser, db: DB, project_id: str = ""):
    """Heal trend analizi — strateji dagilimi, en cok kirilan selector'lar, sayfa bazli istatistik."""
    scoped_project_id = _require_scoped_project_id(db, user, project_id)
    return get_locator_trend_data(project_id=scoped_project_id)


# ═══════════════════════════════════════════════════════════════════════════════
# LLM Trace / Observability Endpoint'leri
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/llm-traces")
def get_llm_traces(
    user: CurrentUser,
    db: DB,
    run_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    limit: int = 50,
    project_id: str = "",
):
    """Son LLM cagrilarini getir — debug ve gozlemlenebilirlik icin."""
    scoped_project_id = _require_scoped_project_id(db, user, project_id)
    from app.deps import _user_permissions

    perms = _user_permissions(user)
    scoped_user_id = None if "admin.*" in perms else str(user.id)
    return get_llm_traces_data(
        project_id=scoped_project_id,
        user_id=scoped_user_id,
        run_id=run_id,
        agent_name=agent_name,
        limit=limit,
    )


@router.get("/llm-traces/stats")
def get_llm_trace_stats(user: CurrentUser, db: DB, project_id: str = ""):
    """LLM cagri istatistikleri — toplam, basarili, basarisiz, ortalama gecikme."""
    scoped_project_id = _require_scoped_project_id(db, user, project_id)
    from app.deps import _user_permissions

    perms = _user_permissions(user)
    scoped_user_id = None if "admin.*" in perms else str(user.id)
    return get_llm_trace_stats_data(project_id=scoped_project_id, user_id=scoped_user_id)
