"""
PipelineService — Analizden Otomasyona Uçtan Uca Pipeline.

Akis:
  1. Proje Kurulum    -> TSPM'de proje oluştur/bul
  2. Keşif            -> Engine crawl + ProjectScanner
  3. Analiz           -> DataAnalyst + RiskScorer + GapAnalyzer
  4. Senaryo Uretimi  -> ScenarioGenerator + Debate + Regulation
  5. Kod Uretimi      -> CodeGenerator + QualityJudge (feedback loop)
  6. Kayit            -> TSPM'e senaryo/kod kaydet + diske yaz
  7. Test Kosumu       -> Engine uzerinden test çalıştır
  8. Onarim           -> AutoHealer + tekrar kosum
  9. Ogrenme          -> SelfImproving + KnowledgeStore kaydet
  10. Rapor           -> Son durum ozeti

Kullanim:
  svc = PipelineService(db_session)
  result = await svc.run(PipelineConfig(
      project_name="Internet Bankaciligi",
      target_url="https://demo.bank.com",
      ...
  ))
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pipeline Configuration & State
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PipelinePhase(str, Enum):
    """Pipeline fazlari — her biri bagimsiz bir is birimi."""
    INITIALIZING = "initializing"
    DISCOVERY = "discovery"
    ANALYSIS = "analysis"
    SCENARIO_GENERATION = "scenario_generation"
    SCENARIO_REVIEW = "scenario_review"
    CODE_GENERATION = "code_generation"
    QUALITY_GATE = "quality_gate"
    PERSISTING = "persisting"
    TEST_EXECUTION = "test_execution"
    AUTO_HEALING = "auto_healing"
    LEARNING = "learning"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineConfig:
    """Pipeline baslatma konfigurasyonu."""
    project_name: str
    target_url: str | None = None
    description: str = ""
    cycles: int = 2
    regulations: list[str] = field(default_factory=lambda: ["BDDK", "KVKK"])
    generate_bdd: bool = True
    generate_playwright: bool = True
    generate_api_tests: bool = True
    run_tests: bool = True
    auto_heal: bool = True
    max_quality_retries: int = 2
    crawl_max_pages: int = 10
    crawl_depth: int = 2


@dataclass
class PipelineLog:
    """Tek bir log kaydi."""
    ts: float
    phase: str
    level: str  # info, warn, error, success
    message: str


@dataclass
class PipelineState:
    """Pipeline çalışma durumu — thread-safe."""
    run_id: str = field(default_factory=lambda: secrets.token_hex(8))
    phase: PipelinePhase = PipelinePhase.INITIALIZING
    progress: int = 0  # 0-100
    running: bool = False
    started_at: float = 0.0
    finished_at: float = 0.0
    current_cycle: int = 0
    total_cycles: int = 1
    logs: list[PipelineLog] = field(default_factory=list)
    error: str | None = None
    warnings: list[str] = field(default_factory=list)  # Kurtarilabilen hatalar

    # Ara sonuclar
    project_id: str | None = None
    discovered_pages: list[dict] = field(default_factory=list)
    analysis: dict = field(default_factory=dict)
    scenarios: list[dict] = field(default_factory=list)
    generated_code: dict = field(default_factory=dict)
    quality_score: float = 0.0
    test_results: dict = field(default_factory=dict)
    healing_results: dict = field(default_factory=dict)
    learning: dict = field(default_factory=dict)

    # TSPM kayit ID'leri
    tspm_scenario_ids: list[str] = field(default_factory=list)
    tspm_execution_id: str | None = None


class PipelineService:
    """Uctan uca otomasyon pipeline servisi."""

    def __init__(self, db: Session):
        self._db = db
        self._state = PipelineState()
        self._cancel_requested = False

    @property
    def state(self) -> PipelineState:
        return self._state

    def cancel(self) -> None:
        """Pipeline'i iptal et."""
        self._cancel_requested = True
        self._log("warn", "Pipeline iptal istendi")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ANA PIPELINE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def run(self, config: PipelineConfig) -> dict[str, Any]:
        """
        Tam pipeline çalıştır — analizden otomasyona.

        Returns: Final rapor dict'i
        """
        self._state.running = True
        self._state.started_at = time.time()
        self._state.total_cycles = config.cycles

        # Proje bağlam cache'ini sıfırla — her pipeline başında taze bağlam oluşsun
        try:
            from app.domains.agents.banking_team.base_agent import BaseAgent
            BaseAgent.reset_project_context()
        except Exception as exc:
            logger.warning("Proje baglam cache'i sifirlanamadi — %s", exc)

        try:
            # -- 1. Initialization -----------------------------------------
            self._set_phase(PipelinePhase.INITIALIZING, 0)
            project = await self._phase_init(config)

            for cycle in range(1, config.cycles + 1):
                if self._cancel_requested:
                    self._log("warn", "Pipeline iptal edildi")
                    break

                self._state.current_cycle = cycle
                self._log("info", f"=== Dongu {cycle}/{config.cycles} basliyor ===")

                # -- 2. Discovery ------------------------------------------
                self._set_phase(PipelinePhase.DISCOVERY, 10)
                discovery = await self._phase_discovery(config)

                # -- 3. Analysis -------------------------------------------
                self._set_phase(PipelinePhase.ANALYSIS, 20)
                analysis = await self._phase_analysis(discovery, config)

                # -- 4. Scenario Generation --------------------------------
                self._set_phase(PipelinePhase.SCENARIO_GENERATION, 35)
                scenarios = await self._phase_scenario_generation(analysis, config)

                # -- 5. Scenario Review (Debate + Regulation) --------------
                self._set_phase(PipelinePhase.SCENARIO_REVIEW, 45)
                reviewed = await self._phase_scenario_review(scenarios, config)

                # -- 6. Code Generation (with quality gate loop) -----------
                self._set_phase(PipelinePhase.CODE_GENERATION, 55)
                code = await self._phase_code_generation(reviewed, config)

                # -- 7. Quality Gate ---------------------------------------
                self._set_phase(PipelinePhase.QUALITY_GATE, 65)
                quality_passed = await self._phase_quality_gate(code, reviewed, config)

                if not quality_passed:
                    self._log("warn", f"Kalite kapisi gecilemedi (dongu {cycle}), sonraki donguye geciliyor")
                    continue

                # -- 8. Persist to TSPM ------------------------------------
                self._set_phase(PipelinePhase.PERSISTING, 70)
                await self._phase_persist(reviewed, code, config)

                # -- 9. Test Execution -------------------------------------
                if config.run_tests:
                    self._set_phase(PipelinePhase.TEST_EXECUTION, 78)
                    test_results = await self._phase_test_execution(code, config)

                    # -- 10. Auto-Healing ----------------------------------
                    if config.auto_heal and test_results.get("total_failed", 0) > 0:
                        self._set_phase(PipelinePhase.AUTO_HEALING, 85)
                        await self._phase_auto_healing(test_results, config)

                # -- 11. Learning ------------------------------------------
                self._set_phase(PipelinePhase.LEARNING, 92)
                await self._phase_learning(cycle, config)

            # -- 12. Final Report ------------------------------------------
            self._set_phase(PipelinePhase.REPORTING, 98)
            report = await self._phase_report(config)

            self._set_phase(PipelinePhase.COMPLETED, 100)
            self._log("success", "Pipeline basariyla tamamlandi")
            self._broadcast_ws("completed", {
                "scenario_count": len(self._state.scenarios),
                "quality_score": self._state.quality_score,
            })
            return report

        except Exception as exc:
            from app.domains.agents.banking_team.errors import AgentError
            self._state.phase = PipelinePhase.FAILED
            self._state.error = str(exc)
            self._log("error", f"Pipeline hatasi: {exc}")
            self._broadcast_ws("failed", {"error": str(exc)})
            logger.exception("Pipeline hatasi")

            # Kurtarilabilir hata ise kismi sonuç don
            is_recoverable = isinstance(exc, AgentError) and exc.recoverable
            return {
                "success": False,
                "partial": is_recoverable,
                "error": str(exc),
                "phase": self._state.phase.value,
                "run_id": self._state.run_id,
                "warnings": self._state.warnings,
                "scenarios_so_far": len(self._state.scenarios),
                "quality_score": self._state.quality_score,
            }
        finally:
            self._state.running = False
            self._state.finished_at = time.time()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PHASE IMPLEMENTATIONS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _phase_init(self, config: PipelineConfig) -> dict:
        """Faz 1: Proje oluştur/bul, engine saglik kontrolu."""
        from app.domains.tspm.models import TspmProject

        self._log("info", f"Proje: {config.project_name}")

        # TSPM projesi bul veya oluştur
        project = self._db.query(TspmProject).filter(
            TspmProject.name == config.project_name
        ).first()

        if not project:
            project = TspmProject(
                id=str(uuid.uuid4()),
                name=config.project_name,
                description=config.description or f"Pipeline tarafindan olusturuldu — {config.target_url or 'N/A'}",
            )
            self._db.add(project)
            self._db.commit()
            self._log("info", f"Yeni proje olusturuldu: {project.id}")
        else:
            self._log("info", f"Mevcut proje bulundu: {project.id}")

        self._state.project_id = project.id

        # Engine saglik kontrolu
        from app.domains.agents.engine_client import get_engine_client
        engine = get_engine_client()
        alive = await engine.is_alive()
        if alive:
            self._log("info", "Engine servisi erisilebilir")
        else:
            self._log("warn", "Engine servisi erisilemez — sadece agent tabanli analiz yapilacak")

        return {"project_id": project.id, "engine_alive": alive}

    async def _phase_discovery(self, config: PipelineConfig) -> dict:
        """Faz 2: Hedef uygulama kesfi — Engine crawl + ProjectScanner."""
        result: dict[str, Any] = {
            "pages": [],
            "selectors": [],
            "scanner_data": {},
        }

        # Engine uzerinden crawl (varsa)
        if config.target_url:
            from app.domains.agents.engine_client import get_engine_client
            engine = get_engine_client()

            if await engine.is_alive():
                self._log("info", f"Crawl basliyor: {config.target_url}")
                crawl_result = await engine.crawl(
                    config.target_url,
                    max_pages=config.crawl_max_pages,
                    depth=config.crawl_depth,
                )
                if not crawl_result.get("error"):
                    pages = crawl_result.get("pages", [])
                    result["pages"] = pages
                    self._state.discovered_pages = pages
                    self._log("info", f"Crawl tamamlandi: {len(pages)} sayfa kesfedildi")

                    # Selector discovery
                    sel_result = await engine.discover_selectors(config.target_url)
                    if not sel_result.get("error"):
                        result["selectors"] = sel_result.get("selectors", [])
                        self._log("info", f"Selector kesfi: {len(result['selectors'])} element bulundu")
                else:
                    self._log("warn", f"Crawl hatasi: {crawl_result.get('detail', 'bilinmeyen')}")

        # ProjectScanner (kod tabani analizi)
        try:
            from app.domains.agents.banking_team.project_scanner import ProjectScannerAgent
            scanner = ProjectScannerAgent()
            ctx = {"project_hint": config.description, "project_id": self._state.project_id}
            scanner_result = scanner.safe_run(ctx)
            if scanner_result.success:
                result["scanner_data"] = scanner_result.data or {}
                self._log("info", "Kod tabani taramasi tamamlandi")
            else:
                self._log("warn", f"Scanner hatasi: {scanner_result.error}")
        except Exception as exc:
            self._log("warn", f"ProjectScanner yuklenemedi: {exc}")

        return result

    async def _phase_analysis(self, discovery: dict, config: PipelineConfig) -> dict:
        """Faz 3: Veri analizi + Risk skorlama + Gap analizi (paralel)."""
        merged_input = {
            **(discovery.get("scanner_data") or {}),
            "pages": discovery.get("pages", []),
            "selectors": discovery.get("selectors", []),
            "target_url": config.target_url or "",
            "regulations": config.regulations,
        }

        # KnowledgeStore'dan baglam al
        knowledge_ctx = ""
        try:
            from app.domains.ai.knowledge_store import KnowledgeStore
            store = KnowledgeStore(project_id=self._state.project_id)
            hits = store.search(config.description or config.project_name, top_k=5)
            if hits:
                knowledge_ctx = "\n---\n".join(h.get("content", "") for h in hits)
                self._log("info", f"KnowledgeStore'dan {len(hits)} baglam alindi")
        except Exception as exc:
            logger.warning("KnowledgeStore sorgusu basarisiz — pipeline baglamsiz devam ediyor: %s", exc)

        # DataAnalyst
        analysis: dict[str, Any] = {}
        try:
            from app.domains.agents.banking_team.data_analyst import DataAnalystAgent
            analyst = DataAnalystAgent()
            ctx = {
                "merged_input": merged_input,
                "knowledge_ctx": knowledge_ctx,
                "project_id": self._state.project_id,
            }
            result = analyst.safe_run(ctx)
            if result.success:
                analysis = result.data or {}
                self._log("info", f"Analiz tamamlandi: {len(analysis.get('business_flows', []))} is akisi bulundu")
        except Exception as exc:
            self._log("warn", f"DataAnalyst hatasi: {exc}")

        # Risk & Coverage analizi — Engine uzerinden (paralel)
        risk_scores: dict = {}
        coverage_gaps: dict = {}

        from app.domains.agents.engine_client import get_engine_client
        engine = get_engine_client()
        engine_alive = await engine.is_alive()

        if engine_alive:
            async def _risk_score():
                nonlocal risk_scores
                try:
                    score = await engine.quality_score()
                    if not score.get("error"):
                        risk_scores = score
                        self._log("info", "Engine risk/kalite skoru alindi")
                except Exception as exc:
                    self._log("warn", f"Engine risk: {exc}")

            async def _gap_analyze():
                nonlocal coverage_gaps
                try:
                    gaps = await engine.coverage_gaps()
                    if not gaps.get("error"):
                        coverage_gaps = gaps
                        self._log("info", "Engine coverage analizi alindi")
                except Exception as exc:
                    self._log("warn", f"Engine coverage: {exc}")

            await asyncio.gather(_risk_score(), _gap_analyze(), return_exceptions=True)
        else:
            self._log("info", "Engine erisilemez, risk/coverage analizi atlanıyor")

        full_analysis = {
            **analysis,
            "risk_scores": risk_scores,
            "coverage_gaps": coverage_gaps,
            "merged_input": merged_input,
            "knowledge_ctx": knowledge_ctx,
        }
        self._state.analysis = full_analysis
        return full_analysis

    async def _phase_scenario_generation(self, analysis: dict, config: PipelineConfig) -> list[dict]:
        """Faz 4: Senaryo uretimi."""
        try:
            from app.domains.agents.banking_team.scenario_generator import ScenarioGeneratorAgent
            generator = ScenarioGeneratorAgent()
            ctx = {
                "analysis": analysis,
                "coverage_gap_hints": analysis.get("coverage_gaps", {}),
                "high_risk_tests": analysis.get("risk_scores", {}),
                "regulations": config.regulations,
                "previous_improvements": self._state.learning.get("improvements", []),
                "project_id": self._state.project_id,
            }
            result = generator.safe_run(ctx)
            if result.success:
                scenarios = (result.data or {}).get("scenarios", [])
                self._state.scenarios = scenarios
                self._log("info", f"Senaryo uretimi: {len(scenarios)} senaryo olusturuldu")
                return scenarios
        except Exception as exc:
            self._log("error", f"ScenarioGenerator hatasi: {exc}")

        return []

    async def _phase_scenario_review(self, scenarios: list[dict], config: PipelineConfig) -> list[dict]:
        """Faz 5: Debate + Regulation ile senaryo iyilestirme."""
        reviewed = list(scenarios)

        # Debate (en az 2 senaryo varsa)
        if len(reviewed) >= 2:
            try:
                from app.domains.agents.banking_team.debate_orchestrator import DebateOrchestrator
                debate = DebateOrchestrator()
                ctx = {
                    "author_output": {"scenarios": reviewed},
                    "task_type": "scenario_review",
                    "project_id": self._state.project_id,
                }
                result = debate.safe_run(ctx)
                if result.success and result.data:
                    refined = result.data.get("scenarios", reviewed)
                    if refined:
                        reviewed = refined
                        self._log("info", f"Debate tamamlandi: {len(reviewed)} senaryo onaylandi")
            except Exception as exc:
                self._log("warn", f"Debate atlandi: {exc}")

        # Regulation kontrolu
        try:
            from app.domains.agents.banking_team.regulation_agent import RegulationAgent
            reg = RegulationAgent()
            ctx = {
                "scenarios": reviewed,
                "regulations": config.regulations,
                "project_id": self._state.project_id,
            }
            result = reg.safe_run(ctx)
            if result.success and result.data:
                rules = result.data.get("rules", [])
                self._log("info", f"Regulasyon: {len(rules)} kural uygulandi")
                # Kurallari senaryolara ekle
                for s in reviewed:
                    s["regulation_rules"] = [
                        r for r in rules
                        if s.get("id") in (r.get("applies_to") or [])
                    ]
        except Exception as exc:
            self._log("warn", f"Regulation atlandi: {exc}")

        self._state.scenarios = reviewed
        return reviewed

    async def _phase_code_generation(self, scenarios: list[dict], config: PipelineConfig) -> dict:
        """Faz 6: Kod uretimi — BDD + Playwright + API testleri."""
        generate_types = []
        if config.generate_bdd:
            generate_types.append("bdd")
        if config.generate_playwright:
            generate_types.append("playwright")
        if config.generate_api_tests:
            generate_types.append("api")

        try:
            from app.domains.agents.banking_team.code_generator import CodeGeneratorAgent
            generator = CodeGeneratorAgent()
            ctx = {
                "scenarios": scenarios,
                "generate": generate_types,
                "target_url": config.target_url,
                "pages": self._state.discovered_pages,
                "project_id": self._state.project_id,
            }
            result = generator.safe_run(ctx)
            if result.success:
                code = result.data or {}
                count = code.get("generated_count", 0)
                self._state.generated_code = code
                self._log("info", f"Kod uretimi: {count} test dosyasi olusturuldu")
                return code
        except Exception as exc:
            self._log("error", f"CodeGenerator hatasi: {exc}")

        return {}

    async def _phase_quality_gate(self, code: dict, scenarios: list[dict], config: PipelineConfig) -> bool:
        """Faz 7: Kalite kapisi — score < 5.0 ise reddeder, feedback loop ile yeniden uretir."""
        for attempt in range(1, config.max_quality_retries + 1):
            try:
                from app.domains.agents.banking_team.quality_judge import QualityJudgeAgent
                judge = QualityJudgeAgent()
                ctx = {
                    "scenarios": scenarios,
                    "generated_code": code,
                    "regulation_rules": [
                        r for s in scenarios
                        for r in s.get("regulation_rules", [])
                    ],
                    "project_id": self._state.project_id,
                }
                result = judge.safe_run(ctx)
                if result.success and result.data:
                    score = result.data.get("weighted_score", 0)
                    verdict = result.data.get("verdict", "FAIL")
                    self._state.quality_score = score

                    if verdict in ("PASS", "WARN"):
                        self._log("info", f"Kalite kapisi GECTI: {score:.1f}/10 ({verdict})")
                        return True

                    self._log("warn", f"Kalite kapisi KALDI: {score:.1f}/10 (deneme {attempt}/{config.max_quality_retries})")

                    # Feedback loop: QualityJudge geri bildirimi ile kodu yeniden üret
                    if attempt < config.max_quality_retries:
                        feedback = result.data.get("dimensions", {})
                        self._log("info", "Feedback ile kod yeniden uretiliyor...")
                        code = await self._regenerate_code_with_feedback(scenarios, code, feedback, config)
                        self._state.generated_code = code
                else:
                    self._log("warn", "QualityJudge sonuç dondurmedi, geciriliyor")
                    return True
            except Exception as exc:
                self._log("warn", f"QualityJudge hatasi: {exc}, geciriliyor")
                return True

        return False

    async def _regenerate_code_with_feedback(
        self, scenarios: list[dict], old_code: dict, feedback: dict, config: PipelineConfig
    ) -> dict:
        """Quality gate feedback ile kodu yeniden üret."""
        try:
            from app.domains.agents.banking_team.code_generator import CodeGeneratorAgent
            generator = CodeGeneratorAgent()

            # Feedback'i context'e ekle
            weak_areas = [dim for dim, score in feedback.items() if isinstance(score, (int, float)) and score < 6.0]
            ctx = {
                "scenarios": scenarios,
                "generate": ["bdd", "playwright"],
                "target_url": config.target_url,
                "previous_code": old_code,
                "project_id": self._state.project_id,
                "quality_feedback": {
                    "weak_areas": weak_areas,
                    "feedback": feedback,
                    "instruction": f"Su alanlarda iyilestirme yap: {', '.join(weak_areas)}",
                },
            }
            result = generator.safe_run(ctx)
            if result.success and result.data:
                self._log("info", "Kod feedback ile yeniden uretildi")
                return result.data
        except Exception as exc:
            self._log("warn", f"Feedback regeneration hatasi: {exc}")

        return old_code

    async def _phase_persist(self, scenarios: list[dict], code: dict, config: PipelineConfig) -> None:
        """Faz 8: Senaryolari TSPM'e kaydet + dosyalari diske yaz."""
        from app.domains.tspm.models import TspmScenario

        project_id = self._state.project_id
        if not project_id:
            self._log("warn", "Project ID bulunamadi, TSPM kaydi atlaniyor")
            return

        saved_count = 0
        for s in scenarios:
            try:
                scenario = TspmScenario(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    title=s.get("id", "") + " — " + (s.get("module", "") or s.get("title", "Senaryo")),
                    description=s.get("expected_result", ""),
                    status="active",
                    current_version=1,
                    steps=s.get("steps"),
                    tags=s.get("tags", [s.get("type", "positive")]),
                )
                self._db.add(scenario)
                self._state.tspm_scenario_ids.append(scenario.id)
                saved_count += 1
            except Exception as exc:
                self._log("warn", f"Senaryo kayit hatasi: {exc}")

        self._db.commit()
        self._log("info", f"TSPM'e {saved_count} senaryo kaydedildi")

        # Dosyalari diske yaz (OutputWriter)
        try:
            from app.domains.agents.banking_team.output_writer import OutputWriterAgent
            writer = OutputWriterAgent()
            ctx = {
                "scenarios": scenarios,
                "generated_code": code,
                "regulation_rules": [r for s in scenarios for r in s.get("regulation_rules", [])],
                "run_id": self._state.run_id,
                "project_id": self._state.project_id,
            }
            result = writer.safe_run(ctx)
            if result.success:
                files = (result.data or {}).get("written_files", [])
                self._log("info", f"Diske {len(files)} dosya yazildi")
        except Exception as exc:
            self._log("warn", f"OutputWriter hatasi: {exc}")

        # Engine'e feature dosyalarini kaydet
        if code.get("bdd_features"):
            from app.domains.agents.engine_client import get_engine_client
            engine = get_engine_client()
            if await engine.is_alive():
                for feat in code["bdd_features"]:
                    name = feat.get("feature_file", f"generated_{secrets.token_hex(4)}.feature")
                    content = feat.get("content", "")
                    if content:
                        await engine.save_feature(name, content)
                self._log("info", f"Engine'e {len(code['bdd_features'])} feature kaydedildi")

    async def _phase_test_execution(self, code: dict, config: PipelineConfig) -> dict:
        """Faz 9: Test kosumu — Engine uzerinden veya lokal."""
        from app.domains.agents.engine_client import get_engine_client
        engine = get_engine_client()

        test_results: dict[str, Any] = {
            "total_passed": 0,
            "total_failed": 0,
            "total_tests": 0,
            "details": {},
        }

        if not await engine.is_alive():
            # Engine yoksa backend TestRunner kullan
            self._log("warn", "Engine erisilemez, backend TestRunner kullaniliyor")
            try:
                from app.domains.agents.banking_team.test_runner import TestRunnerAgent
                runner = TestRunnerAgent()
                result = runner.safe_run({
                    "run_id": self._state.run_id,
                    "written_files": (code or {}).get("written_files", []),
                })
                if result.success and result.data:
                    test_results = result.data
            except Exception as exc:
                self._log("error", f"TestRunner hatasi: {exc}")
        else:
            # Engine uzerinden test kosumu
            self._log("info", "Engine uzerinden test kosumu basliyor...")

            # BDD testleri
            if code.get("bdd_features"):
                features = [f.get("feature_file", "") for f in code["bdd_features"] if f.get("feature_file")]
                if features:
                    bdd_result = await engine.run_tests(features_list=features)
                    if not bdd_result.get("error"):
                        test_results["details"]["bdd"] = bdd_result
                        test_results["total_passed"] += bdd_result.get("passed", 0)
                        test_results["total_failed"] += bdd_result.get("failed", 0)
                        self._log("info", f"BDD: {bdd_result.get('passed', 0)} passed, {bdd_result.get('failed', 0)} failed")

            # Playwright testleri
            if code.get("playwright_tests"):
                pw_result = await engine.run_tests(markers="banking", timeout=300.0)
                if not pw_result.get("error"):
                    test_results["details"]["playwright"] = pw_result
                    test_results["total_passed"] += pw_result.get("passed", 0)
                    test_results["total_failed"] += pw_result.get("failed", 0)
                    self._log("info", f"Playwright: {pw_result.get('passed', 0)} passed, {pw_result.get('failed', 0)} failed")

        test_results["total_tests"] = test_results["total_passed"] + test_results["total_failed"]
        self._state.test_results = test_results

        # TSPM execution kaydi
        await self._record_tspm_execution(test_results)

        return test_results

    async def _record_tspm_execution(self, test_results: dict) -> None:
        """Test sonuclarini TSPM'e kaydet."""
        from app.domains.tspm.models import TspmExecution, TspmExecutionMetrics

        project_id = self._state.project_id
        if not project_id:
            return

        try:
            execution = TspmExecution(
                id=str(uuid.uuid4()),
                project_id=project_id,
                name=f"Pipeline #{self._state.run_id} — Dongu {self._state.current_cycle}",
                status="completed" if test_results.get("total_failed", 0) == 0 else "failed",
            )
            self._db.add(execution)
            self._state.tspm_execution_id = execution.id

            # Metrics
            total = test_results.get("total_tests", 0)
            passed = test_results.get("total_passed", 0)
            metrics = TspmExecutionMetrics(
                id=str(uuid.uuid4()),
                project_id=project_id,
                execution_id=execution.id,
                total=total,
                passed=passed,
                failed=test_results.get("total_failed", 0),
                pass_rate=round(passed / max(total, 1) * 100, 1),
                duration_seconds=round(time.time() - self._state.started_at, 1),
            )
            self._db.add(metrics)
            self._db.commit()
            self._log("info", f"TSPM execution kaydedildi: {execution.id}")
        except Exception as exc:
            self._log("warn", f"TSPM execution kayit hatasi: {exc}")

    async def _phase_auto_healing(self, test_results: dict, config: PipelineConfig) -> None:
        """Faz 10: Kırık testleri onar ve tekrar kos."""
        failed_count = test_results.get("total_failed", 0)
        self._log("info", f"Auto-healing basliyor: {failed_count} başarısız test")

        try:
            from app.domains.agents.banking_team.auto_healer import AutoHealerAgent
            healer = AutoHealerAgent()
            ctx = {
                "test_results": test_results,
                "failed_tests": test_results.get("details", {}),
                "project_id": self._state.project_id,
            }
            result = healer.safe_run(ctx)
            if result.success and result.data:
                healed = result.data.get("healed", 0)
                self._state.healing_results = result.data
                self._log("info", f"Auto-healing: {healed}/{failed_count} test onarildi")

                # Onarilan testleri tekrar kos
                if healed > 0 and config.run_tests:
                    self._log("info", "Onarilan testler tekrar kosuluyor...")
                    from app.domains.agents.engine_client import get_engine_client
                    engine = get_engine_client()
                    if await engine.is_alive():
                        retry = await engine.run_tests(markers="banking")
                        if not retry.get("error"):
                            new_passed = retry.get("passed", 0)
                            self._log("info", f"Tekrar kosum: {new_passed} passed")
                            self._state.test_results["retry"] = retry
        except Exception as exc:
            self._log("warn", f"AutoHealer hatasi: {exc}")

    async def _phase_learning(self, cycle: int, config: PipelineConfig) -> None:
        """Faz 11: Dongu ogrenme — SelfImproving + KnowledgeStore persist."""
        try:
            from app.domains.agents.banking_team.self_improving import SelfImprovingAgent
            improver = SelfImprovingAgent()
            ctx = {
                "cycle": cycle,
                "analysis": self._state.analysis,
                "scenarios": self._state.scenarios,
                "test_results": self._state.test_results,
                "quality_score": self._state.quality_score,
                "healing_results": self._state.healing_results,
                "project_id": self._state.project_id,
            }
            result = improver.safe_run(ctx)
            if result.success and result.data:
                self._state.learning = result.data
                improvements = result.data.get("improvements", [])
                self._log("info", f"Ogrenme: {len(improvements)} iyilestirme onerisi")

                # KnowledgeStore'a ogrenmeyi kaydet
                await self._persist_learning(result.data)
        except Exception as exc:
            self._log("warn", f"SelfImproving hatasi: {exc}")

    async def _persist_learning(self, learning: dict) -> None:
        """Ogrenme sonuclarini KnowledgeStore'a kaydet."""
        try:
            from app.domains.ai.knowledge_store import KnowledgeStore
            store = KnowledgeStore(project_id=self._state.project_id)

            summary = learning.get("learning_summary", "")
            if summary:
                store.ingest(
                    text=summary[:4000],
                    source="insight",
                    metadata={
                        "type": "pipeline_learning",
                        "run_id": self._state.run_id,
                        "cycle": self._state.current_cycle,
                        "quality_score": self._state.quality_score,
                    },
                    project_id=self._state.project_id,
                )

            improvements = learning.get("improvements", [])
            for imp in improvements[:10]:
                store.ingest(
                    text=f"Iyilestirme ({imp.get('area', '')}): {imp.get('action', '')} — {imp.get('rationale', '')}",
                    source="insight",
                    metadata={
                        "type": "improvement",
                        "run_id": self._state.run_id,
                        "area": imp.get("area", ""),
                    },
                    project_id=self._state.project_id,
                )

            self._log("info", f"KnowledgeStore'a {1 + min(len(improvements), 10)} kayit eklendi")
        except Exception as exc:
            self._log("warn", f"KnowledgeStore persist hatasi: {exc}")

    async def _phase_report(self, config: PipelineConfig) -> dict:
        """Faz 12: Final rapor."""
        elapsed = time.time() - self._state.started_at

        report = {
            "success": True,
            "run_id": self._state.run_id,
            "project_id": self._state.project_id,
            "project_name": config.project_name,
            "target_url": config.target_url,
            "total_cycles": config.cycles,
            "duration_seconds": round(elapsed, 1),
            "summary": {
                "discovered_pages": len(self._state.discovered_pages),
                "scenarios_generated": len(self._state.scenarios),
                "scenarios_saved_to_tspm": len(self._state.tspm_scenario_ids),
                "code_files_generated": self._state.generated_code.get("generated_count", 0),
                "quality_score": round(self._state.quality_score, 1),
                "tests_passed": self._state.test_results.get("total_passed", 0),
                "tests_failed": self._state.test_results.get("total_failed", 0),
                "tests_healed": self._state.healing_results.get("healed", 0),
                "improvements_learned": len(self._state.learning.get("improvements", [])),
            },
            "scenarios": self._state.scenarios,
            "test_results": self._state.test_results,
            "quality_gate": {
                "score": self._state.quality_score,
                "passed": self._state.quality_score >= 5.0,
            },
            "tspm": {
                "project_id": self._state.project_id,
                "scenario_ids": self._state.tspm_scenario_ids,
                "execution_id": self._state.tspm_execution_id,
            },
            "learning": self._state.learning,
        }

        self._log("success", f"Rapor hazır — {len(self._state.scenarios)} senaryo, "
                   f"kalite: {self._state.quality_score:.1f}/10, "
                   f"testler: {self._state.test_results.get('total_passed', 0)} gecti / "
                   f"{self._state.test_results.get('total_failed', 0)} kaldi")

        return report

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # HELPERS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _set_phase(self, phase: PipelinePhase, progress: int) -> None:
        self._state.phase = phase
        self._state.progress = progress
        self._log("info", f"Faz: {phase.value}")
        self._broadcast_ws("phase_change")

    def _log(self, level: str, message: str) -> None:
        entry = PipelineLog(
            ts=time.time(),
            phase=self._state.phase.value,
            level=level,
            message=message,
        )
        self._state.logs.append(entry)
        # warn/error seviyesindeki mesajlari warnings listesine ekle
        if level in ("warn", "error"):
            self._state.warnings.append(f"[{self._state.phase.value}] {message}")
        log_fn = getattr(logger, level if level != "success" else "info", logger.info)
        log_fn("[Pipeline %s] %s", self._state.run_id[:8], message)
        self._broadcast_ws("log", {"message": message, "level": level})

    def _broadcast_ws(self, event_type: str, extra: dict | None = None) -> None:
        """Pipeline durumunu WebSocket uzerinden yayin — fire-and-forget."""
        try:
            from app.domains.notifications.service import manager

            payload = {
                "run_id": self._state.run_id,
                "phase": self._state.phase.value,
                "progress": self._state.progress,
                "cycle": self._state.current_cycle,
                "total_cycles": self._state.total_cycles,
                **(extra or {}),
            }

            loop = asyncio.get_running_loop()
            loop.create_task(manager.broadcast(f"pipeline.{event_type}", payload))
        except RuntimeError:
            pass  # No running event loop — skip silently
        except Exception:
            pass  # WebSocket not available — continue silently

    def snapshot(self) -> dict[str, Any]:
        """Mevcut durumun JSON-serializable snapshot'i."""
        return {
            "run_id": self._state.run_id,
            "phase": self._state.phase.value,
            "progress": self._state.progress,
            "running": self._state.running,
            "current_cycle": self._state.current_cycle,
            "total_cycles": self._state.total_cycles,
            "elapsed_seconds": round(time.time() - self._state.started_at, 1) if self._state.started_at else 0,
            "error": self._state.error,
            "warnings": self._state.warnings[-20:],  # Son 20 uyari
            "project_id": self._state.project_id,
            "scenario_count": len(self._state.scenarios),
            "quality_score": self._state.quality_score,
            "test_results": {
                "passed": self._state.test_results.get("total_passed", 0),
                "failed": self._state.test_results.get("total_failed", 0),
            },
            "logs": [
                {
                    "ts": l.ts,
                    "phase": l.phase,
                    "level": l.level,
                    "message": l.message,
                }
                for l in self._state.logs[-50:]
            ],
            "log_count": len(self._state.logs),
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Global pipeline instance (singleton — tek pipeline calisir)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_active_pipeline: PipelineService | None = None


def get_active_pipeline() -> PipelineService | None:
    return _active_pipeline


def set_active_pipeline(pipeline: PipelineService | None) -> None:
    global _active_pipeline
    _active_pipeline = pipeline
