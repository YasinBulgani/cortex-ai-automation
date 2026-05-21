"""
BankingOrchestrator — Banking QA Ekibini Yöneten Orkestratör (v2 — Phase A)

Sıfır müdahale pipeline'ı (her döngüde):

  Döngü N:
    0.  ProjectScannerAjan    → Projeyi otomatik tara (kullanıcı girdi yok)
    0b. RiskScorer            → Taranan testleri risk skoruna göre önceliklendir
    0c. GapAnalyzer           → Kapsam boşluklarını tespit et → senaryo üretimine feed
    1.  VeriAnalistiAjan      → DB/API/log analizi → business flow'lar
    2.  SenaryoUreticiAjan    → Pozitif/Negatif/EdgeCase senaryolar
    3.  RegülasyonAjanı       → Kural motoru + manuel key'ler
    4.  OtomasyonKararAjanı   → UI/API/DB/Manuel matrisi
    5.  KodUreticiAjan        → BDD + Playwright + API kodu
    5b. KaliteHakimiAjan      → LLM-as-Judge: 4 boyutlu rubrik (Senaryo/Regülasyon/Assertion/Veri)
    6.  OutputWriterAjan      → Üretilen kodları diske yaz
    7.  TestRunnerAjan        → Testleri otomatik çalıştır
    7b. AutoHealerAjan        → Kırılan selector'ları otomatik tamir et
    8.  SelfImprovingAjanı    → Analiz + öğren + sonraki döngü önceliği

  Yeni Yetenekler (Phase A):
    - RiskScorer: Test önceliklendirme (6 faktör, weighted scoring)
    - GapAnalyzer: Kapsam boşluk analizi (API/UI/Senaryo/Veri)
    - QualityJudge: 4 boyutlu kalite kapısı (score < 5 → FAIL, 5-7 → WARN, 7+ → PASS)
    - AutoHealer: 3 katmanlı selector tamiri (zero-cost → cache → LLM)

  Her döngü çıktısı KnowledgeStore'a kaydedilir.
  Sonraki döngü bir öncekinin öğrenimlerini bağlam olarak alır.
  SchedulerAgent her gece 02:00'da otomatik tetikler.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


def _ws_broadcast(event_type: str, payload: dict) -> None:
    """WebSocket uzerinden pipeline olay yayini — fire-and-forget."""
    try:
        from app.domains.notifications.service import manager

        loop = asyncio.get_running_loop()
        loop.create_task(manager.broadcast(f"pipeline.{event_type}", payload))
    except RuntimeError:
        logger.debug("_ws_broadcast: calisan event loop yok, '%s' olayi atlanıyor", event_type)
    except Exception as exc:
        logger.warning("_ws_broadcast: '%s' olayi gonderilemedi — %s", event_type, exc)


class BankingPhase(str, Enum):
    IDLE = "idle"
    SCANNING = "scanning"               # Ajan 0
    RISK_SCORING = "risk_scoring"       # Ajan 0b — RiskScorer
    GAP_ANALYSIS = "gap_analysis"       # Ajan 0c — GapAnalyzer
    RISK_AND_GAP_PARALLEL = "risk_scoring + gap_analysis"  # 0b+0c parallel
    DATA_ANALYSIS = "data_analysis"     # Ajan 1
    SCENARIO_GENERATION = "scenario_generation"  # Ajan 2
    SCENARIO_DEBATE = "scenario_debate"  # Ajan 2b — DebateOrchestrator 🆕
    REGULATION = "regulation"           # Ajan 3
    AUTOMATION_DECISION = "automation_decision"  # Ajan 4
    CODE_GENERATION = "code_generation" # Ajan 5
    CODE_DEBATE = "code_debate"         # Ajan 5a — DebateOrchestrator 🆕
    QUALITY_GATE = "quality_gate"       # Ajan 5b — QualityJudge
    WRITING_OUTPUT = "writing_output"   # Ajan 6
    RUNNING_TESTS = "running_tests"     # Ajan 7
    AUTO_HEALING = "auto_healing"       # Ajan 7b — AutoHealer
    SELF_IMPROVING = "self_improving"   # Ajan 8
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BankingLog:
    timestamp: str
    phase: str
    agent: str
    message: str
    level: str = "info"

    def dict(self) -> dict:
        return asdict(self)


@dataclass
class CycleOutput:
    cycle: int
    analysis: dict = field(default_factory=dict)
    scenarios: list = field(default_factory=list)
    regulation_rules: dict = field(default_factory=dict)
    manual_keys: list = field(default_factory=list)
    automation_matrix: list = field(default_factory=list)
    generated_code: dict = field(default_factory=dict)
    improvements: dict = field(default_factory=dict)
    # Phase A yeni alanlar
    risk_scores: list = field(default_factory=list)
    coverage_gaps: list = field(default_factory=list)
    quality_verdict: dict = field(default_factory=dict)
    heal_results: dict = field(default_factory=dict)
    test_results: dict = field(default_factory=dict)

    def to_report(self) -> dict:
        return {
            "cycle": self.cycle,
            "scenario_count": len(self.scenarios),
            "rule_count": len(self.regulation_rules.get("rules", [])),
            "manual_key_count": len(self.manual_keys),
            "automation_summary": self.regulation_rules.get("compliance_summary", {}),
            "code_generated": self.generated_code.get("generated_count", 0),
            "improvement_score": self.improvements.get("cycle_assessment", {}).get("overall_score", 0),
            # Phase A
            "risk_scored_tests": len(self.risk_scores),
            "coverage_gaps_found": len(self.coverage_gaps),
            "quality_score": self.quality_verdict.get("weighted_score", 0),
            "quality_verdict": self.quality_verdict.get("verdict", "N/A"),
            "healed_selectors": self.heal_results.get("healed", 0),
        }


class BankingPipelineState:
    """Banking pipeline'ının durumunu tutan singleton."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.run_id: str | None = None
        self.phase: BankingPhase = BankingPhase.IDLE
        self.running: bool = False
        self.logs: list[BankingLog] = []
        self.cycles: list[CycleOutput] = []
        self.current_cycle: int = 0
        self.total_cycles: int = 3
        self.progress: int = 0
        self.started_at: str | None = None
        self.completed_at: str | None = None
        self.final_report: dict = {}

    def log(self, phase: str, agent: str, msg: str, level: str = "info") -> None:
        entry = BankingLog(
            timestamp=datetime.now(timezone.utc).isoformat(),
            phase=phase,
            agent=agent,
            message=msg,
            level=level,
        )
        self.logs.append(entry)
        log_fn = logger.info if level == "info" else (
            logger.warning if level == "warning" else logger.error
        )
        log_fn("[%s] %s: %s", agent, phase, msg)

        # WebSocket broadcast
        _ws_broadcast("log", {
            "run_id": self.run_id,
            "phase": self.phase.value,
            "progress": self.progress,
            "cycle": self.current_cycle,
            "total_cycles": self.total_cycles,
            "agent": agent,
            "message": msg,
            "level": level,
        })

    def set_phase(self, new_phase: BankingPhase) -> None:
        """Faz değiştir ve WebSocket uzerinden bildir."""
        self.phase = new_phase
        _ws_broadcast("phase_change", {
            "run_id": self.run_id,
            "phase": new_phase.value,
            "progress": self.progress,
            "cycle": self.current_cycle,
            "total_cycles": self.total_cycles,
        })

    def snapshot(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "phase": self.phase.value,
            "running": self.running,
            "current_cycle": self.current_cycle,
            "total_cycles": self.total_cycles,
            "progress": self.progress,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "logs": [e.dict() for e in self.logs[-100:]],  # son 100 log
            "cycle_reports": [c.to_report() for c in self.cycles],
            "final_report": self.final_report,
        }


# Global singleton
banking_pipeline = BankingPipelineState()


def _init_risk_scorer():
    """Engine modülünden RiskScorer'ı yükle (yoksa None)."""
    try:
        from engine.core.ai_prioritizer.risk_scorer import RiskScorer
        return RiskScorer()
    except ImportError:
        logger.info("RiskScorer modülü bulunamadı, risk skorlama devre dışı.")
        return None
    except Exception as e:
        logger.warning("RiskScorer init hatası: %s", e)
        return None


def _init_gap_analyzer():
    """Engine modülünden GapAnalyzer'ı yükle (yoksa None)."""
    try:
        from engine.core.ai_coverage.gap_analyzer import CoverageGapAnalyzer
        return CoverageGapAnalyzer()
    except ImportError:
        logger.info("GapAnalyzer modülü bulunamadı, kapsam analizi devre dışı.")
        return None
    except Exception as e:
        logger.warning("GapAnalyzer init hatası: %s", e)
        return None


async def run_banking_team(
    run_id: str,
    input_data: dict | None = None,
    total_cycles: int = 3,
) -> None:
    """
    Banking QA ekibini sıfır müdahale ile çalıştır.

    input_data opsiyoneldir — verilmezse ProjectScannerAgent otomatik toplar.
    input_data keys (tümü opsiyonel):
      description  — Sistem açıklaması
      db_schema    — DB şeması
      api_docs     — API dökümantasyonu
      logs         — Örnek loglar
      regulations  — Uygulanacak regülasyonlar
      focus_module — Odaklanılacak modül
    """
    from app.domains.agents.banking_team import (
        DataAnalystAgent,
        ScenarioGeneratorAgent,
        RegulationAgent,
        AutomationDecisionAgent,
        CodeGeneratorAgent,
        SelfImprovingAgent,
        AutoHealerAgent,
        QualityJudgeAgent,
    )
    from app.domains.agents.banking_team.debate_orchestrator import DebateOrchestrator
    from app.domains.agents.banking_team.project_scanner import ProjectScannerAgent
    from app.domains.agents.banking_team.output_writer import OutputWriterAgent
    from app.domains.agents.banking_team.test_runner import TestRunnerAgent
    from app.domains.ai.knowledge_store import KnowledgeStore

    banking_pipeline.running = True
    banking_pipeline.run_id = run_id
    banking_pipeline.total_cycles = total_cycles
    banking_pipeline.started_at = datetime.now(timezone.utc).isoformat()
    banking_pipeline.progress = 0

    PHASES_PER_CYCLE = 15  # 0-8 + 4 yeni faz + 2 debate faz
    total_steps = PHASES_PER_CYCLE * total_cycles
    step = 0

    def advance(n: int = 1) -> None:
        nonlocal step
        step += n
        banking_pipeline.progress = min(int(step / total_steps * 100), 99)

    # Ajan örnekleri oluştur — 11 ajan (9 mevcut + 2 Phase A + 1 P1 Debate)
    scanner = ProjectScannerAgent()
    analyst = DataAnalystAgent()
    generator = ScenarioGeneratorAgent()
    regulator = RegulationAgent()
    decision = AutomationDecisionAgent()
    coder = CodeGeneratorAgent()
    judge = QualityJudgeAgent()       # Phase A: LLM-as-Judge
    debater = DebateOrchestrator(max_rounds=2, min_quality=7.0)  # P1: Multi-Agent Debate
    writer = OutputWriterAgent()
    runner = TestRunnerAgent()
    healer = AutoHealerAgent()        # Phase A: Auto-Healer
    improver = SelfImprovingAgent()

    # Engine modülleri — disconnected modüller artık bağlı
    risk_scorer = _init_risk_scorer()
    gap_analyzer = _init_gap_analyzer()

    project_id = (input_data or {}).get("project_id")
    store = KnowledgeStore(project_id=project_id)
    previous_improvements: list = []
    all_scenarios: list = []

    try:
        for cycle in range(1, total_cycles + 1):
            banking_pipeline.current_cycle = cycle
            cycle_out = CycleOutput(cycle=cycle)

            banking_pipeline.log(
                "orchestrator", "Orkestratör",
                f"━━━ Döngü {cycle}/{total_cycles} Başlıyor ━━━", "info",
            )

            # ═════════════════════════════════════════════════════════
            # FAZI 0 — Proje Tarayıcı (sıfır müdahale için kritik)
            # ═════════════════════════════════════════════════════════
            banking_pipeline.set_phase(BankingPhase.SCANNING)
            banking_pipeline.log("scanning", "Proje Tarayıcı", f"[{cycle}] Proje otomatik taranıyor...")

            scan_result = await asyncio.get_event_loop().run_in_executor(
                None, scanner.safe_run, {"project_hint": (input_data or {}).get("focus_module", "")}
            )
            # Taranan verilerle input_data'yı zenginleştir — kullanıcı verisi öncelikli
            scanned = scan_result.data
            merged_input: dict = {**scanned, **(input_data or {})}
            advance()

            banking_pipeline.log(
                "scanning", "Proje Tarayıcı",
                f"[{cycle}] DB şeması, {len(scanned.get('api_docs', '').splitlines())} endpoint, "
                f"git log tarandı. Regülasyonlar: {', '.join(scanned.get('regulations', []))}",
                "success" if scan_result.success else "warning",
            )

            # ═════════════════════════════════════════════════════════
            # FAZ 0b+0c — Risk Scorer + Gap Analyzer (PARALEL)
            # ═════════════════════════════════════════════════════════
            banking_pipeline.set_phase(BankingPhase.RISK_AND_GAP_PARALLEL)
            risk_profiles = []
            coverage_gaps = []

            async def _run_risk_scoring() -> None:
                """Phase 0b: Risk Scorer — runs concurrently with gap analysis."""
                nonlocal risk_profiles
                if risk_scorer:
                    banking_pipeline.log("risk_scoring", "Risk Skorlayıcı", f"[{cycle}] Testler risk skorlanıyor...")
                    try:
                        changed_files = scanned.get("changed_files", [])
                        existing_tests = scanned.get("existing_tests", [])

                        if existing_tests and changed_files:
                            risk_profiles = await asyncio.get_event_loop().run_in_executor(
                                None, risk_scorer.score_all, existing_tests, changed_files,
                            )
                            cycle_out.risk_scores = [
                                {"test_id": rp.test_id, "score": rp.total_score, "factors": rp.factor_scores}
                                for rp in risk_profiles[:20]
                            ] if hasattr(risk_profiles[0] if risk_profiles else None, 'test_id') else []

                            banking_pipeline.log(
                                "risk_scoring", "Risk Skorlayıcı",
                                f"[{cycle}] {len(risk_profiles)} test skorlandı. "
                                f"En riskli: {risk_profiles[0].test_id if risk_profiles and hasattr(risk_profiles[0], 'test_id') else 'N/A'}",
                                "success",
                            )
                        else:
                            banking_pipeline.log(
                                "risk_scoring", "Risk Skorlayıcı",
                                f"[{cycle}] Test veya değişen dosya bulunamadı, atlanıyor.",
                                "info",
                            )
                    except Exception as e:
                        banking_pipeline.log("risk_scoring", "Risk Skorlayıcı", f"[{cycle}] Hata: {e}", "warning")
                else:
                    banking_pipeline.log("risk_scoring", "Risk Skorlayıcı", f"[{cycle}] Modül devre dışı.", "info")

            async def _run_gap_analysis() -> None:
                """Phase 0c: Gap Analyzer — runs concurrently with risk scoring."""
                nonlocal coverage_gaps
                if gap_analyzer:
                    banking_pipeline.log("gap_analysis", "Kapsam Analizci", f"[{cycle}] Kapsam boşlukları analiz ediliyor...")
                    try:
                        api_docs = scanned.get("api_docs", "")
                        existing_test_content = scanned.get("existing_test_content", "")

                        if api_docs:
                            api_report = await asyncio.get_event_loop().run_in_executor(
                                None, gap_analyzer.analyze_api_coverage, api_docs, existing_test_content,
                            )
                            if hasattr(api_report, 'gaps'):
                                coverage_gaps.extend([
                                    {"area": g.area, "target": g.target, "severity": g.severity,
                                     "description": g.description, "suggested_test": g.suggested_test}
                                    for g in api_report.gaps
                                ])

                        ui_pages = scanned.get("ui_pages", [])
                        if ui_pages:
                            ui_report = await asyncio.get_event_loop().run_in_executor(
                                None, gap_analyzer.analyze_ui_coverage, ui_pages, existing_test_content,
                            )
                            if hasattr(ui_report, 'gaps'):
                                coverage_gaps.extend([
                                    {"area": g.area, "target": g.target, "severity": g.severity,
                                     "description": g.description, "suggested_test": g.suggested_test}
                                    for g in ui_report.gaps
                                ])

                        cycle_out.coverage_gaps = coverage_gaps

                        banking_pipeline.log(
                            "gap_analysis", "Kapsam Analizci",
                            f"[{cycle}] {len(coverage_gaps)} kapsam boşluğu tespit edildi. "
                            f"Yüksek: {sum(1 for g in coverage_gaps if g.get('severity') == 'high')}",
                            "success" if coverage_gaps else "info",
                        )
                    except Exception as e:
                        banking_pipeline.log("gap_analysis", "Kapsam Analizci", f"[{cycle}] Hata: {e}", "warning")
                else:
                    banking_pipeline.log("gap_analysis", "Kapsam Analizci", f"[{cycle}] Modül devre dışı.", "info")

            await asyncio.gather(
                _run_risk_scoring(),
                _run_gap_analysis(),
            )
            advance(2)

            # ── Geçmiş bilgiyi KnowledgeStore'dan al ─────────────────
            knowledge_ctx = ""
            try:
                chunks = store.retrieve(
                    merged_input.get("description", "bankacılık"),
                    top_k=4,
                    sources=["insight", "execution", "error_pattern"],
                    project_id=project_id,
                )
                if chunks:
                    knowledge_ctx = "\n".join([c.content for c in chunks])
            except Exception:
                pass

            # ═════════════════════════════════════════════════════════
            # FAZI 1 — Veri Analisti
            # ═════════════════════════════════════════════════════════
            banking_pipeline.set_phase(BankingPhase.DATA_ANALYSIS)
            banking_pipeline.log("data_analysis", "Veri Analisti", f"[{cycle}] Analiz başlıyor...")

            analyst_ctx = {
                **merged_input,
                "existing_knowledge": knowledge_ctx,
                "project_id": project_id,
            }
            analyst_result = await asyncio.get_event_loop().run_in_executor(
                None, analyst.safe_run, analyst_ctx
            )
            cycle_out.analysis = analyst_result.data
            advance()

            banking_pipeline.log(
                "data_analysis", "Veri Analisti",
                f"[{cycle}] {len(analyst_result.data.get('business_flows', []))} iş akışı, "
                f"{len(analyst_result.data.get('critical_areas', []))} kritik alan tespit edildi.",
                "success" if analyst_result.success else "warning",
            )

            # ═════════════════════════════════════════════════════════
            # FAZI 2 — Senaryo Üretici
            # ═════════════════════════════════════════════════════════
            banking_pipeline.set_phase(BankingPhase.SCENARIO_GENERATION)
            banking_pipeline.log("scenario_generation", "Senaryo Üretici", f"[{cycle}] Senaryolar üretiliyor...")

            gen_ctx = {
                "analysis": cycle_out.analysis,
                "description": input_data.get("description", ""),
                "focus_module": input_data.get("focus_module", ""),
                "existing_scenarios": all_scenarios[-20:],
                "project_id": project_id,
            }
            # Phase A: Kapsam boşluklarını senaryo üretimine feed et
            if coverage_gaps:
                high_gaps = [g for g in coverage_gaps if g.get("severity") == "high"]
                if high_gaps:
                    gap_hints = "; ".join(
                        f"{g['area']}: {g['target']}" for g in high_gaps[:5]
                    )
                    gen_ctx["coverage_gap_hints"] = gap_hints
                    gen_ctx["gap_suggested_tests"] = [g.get("suggested_test", "") for g in high_gaps[:5]]

            # Phase A: Risk skorlarını senaryo üretimine feed et
            if risk_profiles and cycle_out.risk_scores:
                gen_ctx["high_risk_tests"] = [
                    r["test_id"] for r in cycle_out.risk_scores[:5]
                    if r.get("score", 0) > 0.7
                ]

            # Önceki döngünün iyileştirme önerilerinden yeni senaryo ihtiyaçları
            if previous_improvements:
                new_needed = previous_improvements[-1].get("new_scenarios_needed", [])
                if new_needed:
                    focus = new_needed[0].get("area", "")
                    if focus:
                        gen_ctx["focus_module"] = focus

            gen_result = await asyncio.get_event_loop().run_in_executor(
                None, generator.safe_run, gen_ctx
            )
            cycle_out.scenarios = gen_result.data.get("scenarios", [])
            all_scenarios.extend(cycle_out.scenarios)
            advance()

            banking_pipeline.log(
                "scenario_generation", "Senaryo Üretici",
                f"[{cycle}] {len(cycle_out.scenarios)} senaryo üretildi.",
                "success" if gen_result.success else "warning",
            )

            # ═════════════════════════════════════════════════════════
            # FAZ 2b — Senaryo Debate (Author → Critic → Revise → Judge) 🆕
            # ═════════════════════════════════════════════════════════
            if cycle_out.scenarios and len(cycle_out.scenarios) >= 3:
                banking_pipeline.set_phase(BankingPhase.SCENARIO_DEBATE)
                banking_pipeline.log(
                    "scenario_debate", "Tartışma Orkestratörü",
                    f"[{cycle}] Senaryo debate başlıyor ({len(cycle_out.scenarios)} senaryo)...",
                )

                debate_ctx = {
                    "debate_type": "scenario",
                    "author_output": gen_result.data,
                    "description": input_data.get("description", ""),
                    "regulation_rules": {},  # Henüz regulation çalışmadı
                    "project_id": project_id,
                }
                debate_result = await asyncio.get_event_loop().run_in_executor(
                    None, debater.safe_run, debate_ctx
                )

                if debate_result.success:
                    debate_data = debate_result.data
                    final_output = debate_data.get("final_output", {})
                    improved_scenarios = final_output.get("scenarios", [])

                    if improved_scenarios:
                        # Debate sonrası senaryoları güncelle
                        old_count = len(cycle_out.scenarios)
                        cycle_out.scenarios = improved_scenarios
                        new_count = len(cycle_out.scenarios)
                        improvement = debate_data.get("improvement", 0)

                        banking_pipeline.log(
                            "scenario_debate", "Tartışma Orkestratörü",
                            f"[{cycle}] Debate tamamlandı: {old_count}→{new_count} senaryo, "
                            f"skor: {debate_data.get('quality_score', '?')}/10, "
                            f"iyileşme: +{improvement:.1f}, "
                            f"verdict: {debate_data.get('verdict', '?')}",
                            "success",
                        )
                    else:
                        banking_pipeline.log(
                            "scenario_debate", "Tartışma Orkestratörü",
                            f"[{cycle}] Debate sonucu dönmedi, orijinal senaryolar korunuyor.",
                            "warning",
                        )
                else:
                    banking_pipeline.log(
                        "scenario_debate", "Tartışma Orkestratörü",
                        f"[{cycle}] Debate başarısız: {debate_result.error[:80]}",
                        "warning",
                    )
            advance()

            # ═════════════════════════════════════════════════════════
            # FAZI 3 — Regülasyon Ajanı
            # ═════════════════════════════════════════════════════════
            banking_pipeline.set_phase(BankingPhase.REGULATION)
            banking_pipeline.log("regulation", "Regülasyon Ajanı", f"[{cycle}] Kural motoru çalışıyor...")

            reg_ctx = {
                "scenarios": cycle_out.scenarios,
                "description": input_data.get("description", ""),
                "regulations": input_data.get("regulations", ["BDDK", "PCI-DSS", "MASAK", "KYC", "KVKK"]),
                "project_id": project_id,
            }
            reg_result = await asyncio.get_event_loop().run_in_executor(
                None, regulator.safe_run, reg_ctx
            )
            cycle_out.regulation_rules = reg_result.data
            cycle_out.manual_keys = reg_result.data.get("manual_keys", [])
            advance()

            banking_pipeline.log(
                "regulation", "Regülasyon Ajanı",
                f"[{cycle}] {len(reg_result.data.get('rules', []))} kural, "
                f"{len(cycle_out.manual_keys)} manuel key.",
                "success" if reg_result.success else "warning",
            )

            # ═════════════════════════════════════════════════════════
            # FAZI 4 — Otomasyon Karar Ajanı
            # ═════════════════════════════════════════════════════════
            banking_pipeline.set_phase(BankingPhase.AUTOMATION_DECISION)
            banking_pipeline.log("automation_decision", "Otomasyon Karar Ajanı", f"[{cycle}] Matris oluşturuluyor...")

            dec_ctx = {
                "scenarios": cycle_out.scenarios,
                "manual_keys": cycle_out.manual_keys,
                "description": input_data.get("description", ""),
                "project_id": project_id,
            }
            dec_result = await asyncio.get_event_loop().run_in_executor(
                None, decision.safe_run, dec_ctx
            )
            cycle_out.automation_matrix = dec_result.data.get("automation_matrix", [])
            advance()

            auto_summary = dec_result.data.get("summary", {})
            banking_pipeline.log(
                "automation_decision", "Otomasyon Karar Ajanı",
                f"[{cycle}] UI={auto_summary.get('ui', 0)}, "
                f"API={auto_summary.get('api', 0)}, "
                f"Manuel={auto_summary.get('manual', 0)}",
                "success" if dec_result.success else "warning",
            )

            # ═════════════════════════════════════════════════════════
            # FAZI 5 — Kod Üretici
            # ═════════════════════════════════════════════════════════
            banking_pipeline.set_phase(BankingPhase.CODE_GENERATION)
            banking_pipeline.log("code_generation", "Kod Üretici", f"[{cycle}] Kod üretiliyor...")

            code_ctx = {
                "automation_matrix": cycle_out.automation_matrix,
                "scenarios": cycle_out.scenarios,
                "description": input_data.get("description", ""),
                "generate": ["bdd", "playwright", "api"],
                "project_id": project_id,
            }
            code_result = await asyncio.get_event_loop().run_in_executor(
                None, coder.safe_run, code_ctx
            )
            cycle_out.generated_code = code_result.data
            advance()

            banking_pipeline.log(
                "code_generation", "Kod Üretici",
                f"[{cycle}] {code_result.data.get('generated_count', 0)} dosya üretildi.",
                "success" if code_result.success else "warning",
            )

            # ═════════════════════════════════════════════════════════
            # FAZ 5a — Kod Debate (Author → Critic → Revise → Judge) 🆕
            # ═════════════════════════════════════════════════════════
            has_code = any(
                code_result.data.get(k)
                for k in ("bdd_features", "playwright_tests", "api_tests")
            )
            if has_code:
                banking_pipeline.set_phase(BankingPhase.CODE_DEBATE)
                banking_pipeline.log(
                    "code_debate", "Tartışma Orkestratörü",
                    f"[{cycle}] Kod debate başlıyor...",
                )

                code_debate_ctx = {
                    "debate_type": "code",
                    "author_output": code_result.data,
                    "description": input_data.get("description", ""),
                    "regulation_rules": cycle_out.regulation_rules,
                    "scenarios": cycle_out.scenarios,
                    "project_id": project_id,
                }
                code_debate_result = await asyncio.get_event_loop().run_in_executor(
                    None, debater.safe_run, code_debate_ctx
                )

                if code_debate_result.success:
                    cd_data = code_debate_result.data
                    final_code = cd_data.get("final_output", {})

                    # Eğer debate iyileştirilmiş kod döndürdüyse güncelle
                    if final_code.get("bdd_features") or final_code.get("playwright_tests"):
                        cycle_out.generated_code = final_code
                        banking_pipeline.log(
                            "code_debate", "Tartışma Orkestratörü",
                            f"[{cycle}] Kod debate tamamlandı: "
                            f"skor: {cd_data.get('quality_score', '?')}/10, "
                            f"verdict: {cd_data.get('verdict', '?')}",
                            "success",
                        )
                    else:
                        banking_pipeline.log(
                            "code_debate", "Tartışma Orkestratörü",
                            f"[{cycle}] Kod debate sonucu uygulanmadı, orijinal kod korunuyor.",
                            "warning",
                        )
                else:
                    banking_pipeline.log(
                        "code_debate", "Tartışma Orkestratörü",
                        f"[{cycle}] Kod debate başarısız: {code_debate_result.error[:80]}",
                        "warning",
                    )
            advance()

            # ═════════════════════════════════════════════════════════
            # FAZ 5b — Quality Judge (LLM-as-Judge Kalite Kapısı)
            # ═════════════════════════════════════════════════════════
            banking_pipeline.set_phase(BankingPhase.QUALITY_GATE)
            banking_pipeline.log("quality_gate", "Kalite Hakimi", f"[{cycle}] Kalite değerlendirmesi başlıyor...")

            judge_ctx = {
                "scenarios": cycle_out.scenarios,
                "generated_code": cycle_out.generated_code,
                "regulation_rules": cycle_out.regulation_rules,
                "description": input_data.get("description", ""),
                "project_id": project_id,
            }
            judge_result = await asyncio.get_event_loop().run_in_executor(
                None, judge.safe_run, judge_ctx
            )
            cycle_out.quality_verdict = judge_result.data
            advance()

            quality_score = judge_result.data.get("weighted_score", 0)
            verdict = judge_result.data.get("verdict", "N/A")

            banking_pipeline.log(
                "quality_gate", "Kalite Hakimi",
                f"[{cycle}] Kalite skoru: {quality_score:.1f}/10 → {verdict}. "
                f"{'✓ Kalite kapısı geçildi' if verdict in ('PASS', 'WARN') else '✗ Kalite yetersiz'}",
                "success" if verdict == "PASS" else ("warning" if verdict == "WARN" else "error"),
            )

            # Kalite kapısı FAIL ise kodları atlama seçeneği
            quality_gate_passed = verdict in ("PASS", "WARN", "SKIP")

            # ═════════════════════════════════════════════════════════
            # FAZI 6 — Output Writer (diske yaz)
            # ═════════════════════════════════════════════════════════
            banking_pipeline.set_phase(BankingPhase.WRITING_OUTPUT)

            if quality_gate_passed:
                banking_pipeline.log("writing_output", "Çıktı Yazıcı", f"[{cycle}] Dosyalar diske yazılıyor...")

                write_ctx = {
                    "run_id": f"{run_id}-c{cycle}",
                    "scenarios": cycle_out.scenarios,
                    "regulation_rules": cycle_out.regulation_rules,
                    "automation_matrix": cycle_out.automation_matrix,
                    "generated_code": cycle_out.generated_code,
                    "manual_keys": cycle_out.manual_keys,
                    "project_id": project_id,
                }
                write_result = await asyncio.get_event_loop().run_in_executor(
                    None, writer.safe_run, write_ctx
                )

                banking_pipeline.log(
                    "writing_output", "Çıktı Yazıcı",
                    f"[{cycle}] {write_result.data.get('file_count', 0)} dosya yazıldı: "
                    f"{', '.join(write_result.data.get('written_files', [])[:3])}...",
                    "success" if write_result.success else "warning",
                )
            else:
                # Kalite kapısı FAIL — dosya yazma atla
                from .banking_team.base_agent import AgentResult as _AR
                write_result = _AR(agent_name="Çıktı Yazıcı", success=False,
                                    data={"file_count": 0, "written_files": [],
                                           "skipped_reason": f"Kalite kapısı FAIL (skor: {quality_score:.1f})"})
                banking_pipeline.log(
                    "writing_output", "Çıktı Yazıcı",
                    f"[{cycle}] Kalite kapısı FAIL — dosya yazma atlandı (skor: {quality_score:.1f}/10).",
                    "warning",
                )
            advance()

            # ═════════════════════════════════════════════════════════
            # FAZI 7 — Test Runner (otomatik çalıştır)
            # ═════════════════════════════════════════════════════════
            banking_pipeline.set_phase(BankingPhase.RUNNING_TESTS)
            banking_pipeline.log("running_tests", "Test Koşucu", f"[{cycle}] Üretilen testler çalıştırılıyor...")

            run_ctx = {
                "run_id": f"{run_id}-c{cycle}",
                "written_files": write_result.data.get("written_files", []),
                "run_playwright": True,
                "run_pytest": True,
                "timeout": 90,
                "project_id": project_id,
            }
            test_result = await asyncio.get_event_loop().run_in_executor(
                None, runner.safe_run, run_ctx
            )
            advance()

            banking_pipeline.log(
                "running_tests", "Test Koşucu",
                f"[{cycle}] Testler tamamlandı: "
                f"pass={test_result.data.get('total_passed', 0)} "
                f"fail={test_result.data.get('total_failed', 0)}",
                "success" if test_result.success else "warning",
            )

            cycle_out.test_results = test_result.data

            # ═════════════════════════════════════════════════════════
            # FAZ 7b — Auto-Healer (Kırılan Testleri Otomatik Tamir)
            # ═════════════════════════════════════════════════════════
            banking_pipeline.set_phase(BankingPhase.AUTO_HEALING)
            failed_count = test_result.data.get("total_failed", 0)

            if failed_count > 0 and quality_gate_passed:
                banking_pipeline.log(
                    "auto_healing", "Otomatik Tamirci",
                    f"[{cycle}] {failed_count} başarısız test tespit edildi, otomatik tamir başlıyor...",
                )

                # Test runner output'undan kırık test bilgilerini derle
                failed_tests = _extract_failed_tests(test_result.data)

                if failed_tests:
                    heal_ctx = {
                        "failed_tests": failed_tests,
                        "test_files_dir": "e2e/banking",
                        "project_id": project_id,
                    }
                    heal_result = await asyncio.get_event_loop().run_in_executor(
                        None, healer.safe_run, heal_ctx
                    )
                    cycle_out.heal_results = heal_result.data

                    healed = heal_result.data.get("healed", 0)
                    total_broken = heal_result.data.get("total_broken", 0)

                    banking_pipeline.log(
                        "auto_healing", "Otomatik Tamirci",
                        f"[{cycle}] {healed}/{total_broken} kırık selector tamir edildi.",
                        "success" if healed > 0 else "info",
                    )

                    # RiskScorer'a başarısız testleri kaydet
                    if risk_scorer:
                        for ft in failed_tests:
                            try:
                                risk_scorer.record_result(ft.get("test_name", ""), passed=False)
                            except Exception:
                                pass
                else:
                    banking_pipeline.log(
                        "auto_healing", "Otomatik Tamirci",
                        f"[{cycle}] Kırık test detayı çıkarılamadı.",
                        "info",
                    )
            else:
                banking_pipeline.log(
                    "auto_healing", "Otomatik Tamirci",
                    f"[{cycle}] {'Başarısız test yok' if failed_count == 0 else 'Kalite kapısından geçemedi'}, atlanıyor.",
                    "info",
                )

                # Başarılı testleri RiskScorer'a kaydet
                if risk_scorer and test_result.data.get("total_passed", 0) > 0:
                    try:
                        risk_scorer.record_result(f"cycle-{cycle}-batch", passed=True)
                    except Exception:
                        pass
            advance()

            # ═════════════════════════════════════════════════════════
            # FAZI 8 — Self-Improving
            # ═════════════════════════════════════════════════════════
            banking_pipeline.set_phase(BankingPhase.SELF_IMPROVING)
            banking_pipeline.log("self_improving", "Self-Improving Ajanı", f"[{cycle}] Döngü analiz ediliyor...")

            improve_ctx = {
                "cycle_number": cycle,
                "analysis": cycle_out.analysis,
                "scenarios": cycle_out.scenarios,
                "regulation_rules": cycle_out.regulation_rules,
                "automation_matrix": cycle_out.automation_matrix,
                "generated_code": cycle_out.generated_code,
                "knowledge_history": knowledge_ctx,
                "previous_improvements": previous_improvements,
                # Test koşu sonuçları
                "test_results": {
                    "passed": test_result.data.get("total_passed", 0),
                    "failed": test_result.data.get("total_failed", 0),
                    "playwright": test_result.data.get("playwright"),
                    "pytest": test_result.data.get("pytest"),
                },
                "written_files": write_result.data.get("written_files", []),
                # Phase A: Yeni veriler
                "quality_verdict": cycle_out.quality_verdict,
                "heal_results": cycle_out.heal_results,
                "coverage_gaps": cycle_out.coverage_gaps,
                "risk_scores": cycle_out.risk_scores[:5],
                "project_id": project_id,
            }
            improve_result = await asyncio.get_event_loop().run_in_executor(
                None, improver.safe_run, improve_ctx
            )
            cycle_out.improvements = improve_result.data
            previous_improvements.append(improve_result.data)
            advance()

            score = improve_result.data.get("cycle_assessment", {}).get("overall_score", 0)
            banking_pipeline.log(
                "self_improving", "Self-Improving Ajanı",
                f"[{cycle}] Döngü skoru: {score}/10. "
                f"{len(improve_result.data.get('improvements', []))} iyileştirme önerisi.",
                "success",
            )

            banking_pipeline.cycles.append(cycle_out)
            banking_pipeline.log(
                "orchestrator", "Orkestratör",
                f"━━━ Döngü {cycle}/{total_cycles} Tamamlandı ━━━", "success",
            )

            if cycle < total_cycles:
                await asyncio.sleep(0.5)  # Ollama'ya nefes aldır

        # ── Final Rapor ───────────────────────────────────────────────
        banking_pipeline.final_report = _build_final_report(banking_pipeline.cycles, input_data)
        banking_pipeline.set_phase(BankingPhase.COMPLETED)
        banking_pipeline.progress = 100

        total_scenarios = sum(len(c.scenarios) for c in banking_pipeline.cycles)
        total_code = sum(c.generated_code.get("generated_count", 0) for c in banking_pipeline.cycles)
        banking_pipeline.log(
            "orchestrator", "Orkestratör",
            f"✓ {total_cycles} döngü tamamlandı. "
            f"Toplam {total_scenarios} senaryo, {total_code} kod dosyası üretildi.",
            "success",
        )
        _ws_broadcast("completed", {
            "run_id": banking_pipeline.run_id,
            "total_scenarios": total_scenarios,
            "total_code": total_code,
            "total_cycles": total_cycles,
        })

    except Exception as exc:
        banking_pipeline.set_phase(BankingPhase.FAILED)
        banking_pipeline.log("orchestrator", "Orkestratör", f"Pipeline hatası: {exc}", "error")
        _ws_broadcast("failed", {
            "run_id": banking_pipeline.run_id,
            "error": str(exc),
        })
        logger.exception("Banking pipeline hatası")
    finally:
        banking_pipeline.running = False
        banking_pipeline.completed_at = datetime.now(timezone.utc).isoformat()


def _extract_failed_tests(test_data: dict) -> list[dict]:
    """TestRunner çıktısından kırık test bilgilerini çıkar (AutoHealer için)."""
    failed_tests = []

    # Playwright sonuçları
    pw = test_data.get("playwright") or {}
    if pw.get("failed", 0) > 0:
        # JSON reporter output varsa parse et
        output = pw.get("output", "")
        if output:
            import re
            # "Error: locator.click: ..." pattern'ını yakala
            errors = re.findall(
                r'(?:TimeoutError|Error):\s*(?:locator\.\w+|page\.\w+).*?(?:Selector|locator):\s*["\']?([^"\'\n]+)',
                output,
            )
            for i, selector in enumerate(errors[:5]):
                failed_tests.append({
                    "file": "e2e/banking/",
                    "test_name": f"playwright-test-{i+1}",
                    "error": output[:200],
                    "selector": selector.strip(),
                    "dom_snippet": "",
                })

        # Kırık test yoksa genel bir kayıt ekle
        if not failed_tests and pw.get("failed", 0) > 0:
            failed_tests.append({
                "file": "e2e/banking/",
                "test_name": "playwright-unknown",
                "error": f"Playwright: {pw.get('failed', 0)} test başarısız",
                "selector": "",
                "dom_snippet": "",
            })

    # pytest sonuçları
    pt = test_data.get("pytest") or {}
    if pt.get("failed", 0) > 0:
        failed_tests.append({
            "file": "api-tests/banking/",
            "test_name": "pytest-unknown",
            "error": f"pytest: {pt.get('failed', 0)} test başarısız",
            "selector": "",
            "dom_snippet": "",
        })

    return failed_tests


def _build_final_report(cycles: list[CycleOutput], input_data: dict) -> dict:
    """Tüm döngülerin çıktısından birleşik rapor oluştur."""
    all_scenarios = []
    all_rules = []
    all_manual_keys = []
    all_bdd = []
    all_playwright = []
    all_api = []
    improvement_scores = []

    for c in cycles:
        all_scenarios.extend(c.scenarios)
        all_rules.extend(c.regulation_rules.get("rules", []))
        all_manual_keys.extend(c.manual_keys)
        all_bdd.extend(c.generated_code.get("bdd_features", []))
        all_playwright.extend(c.generated_code.get("playwright_tests", []))
        all_api.extend(c.generated_code.get("api_tests", []))
        score = c.improvements.get("cycle_assessment", {}).get("overall_score", 0)
        if score:
            improvement_scores.append(float(score))

    # Tekrar eden senaryoları çıkar (ID bazlı)
    seen_ids: set = set()
    unique_scenarios = []
    for s in all_scenarios:
        sid = s.get("id", "")
        if sid not in seen_ids:
            seen_ids.add(sid)
            unique_scenarios.append(s)

    # Otomasyon matrisi — son döngünün kararı geçerli
    last_matrix = cycles[-1].automation_matrix if cycles else []

    avg_score = round(sum(improvement_scores) / len(improvement_scores), 2) if improvement_scores else 0

    return {
        "system": input_data.get("description", ""),
        "total_cycles": len(cycles),
        "average_quality_score": avg_score,
        "scenarios": {
            "total": len(unique_scenarios),
            "by_type": {
                t: sum(1 for s in unique_scenarios if s.get("type") == t)
                for t in ["positive", "negative", "edge_case"]
            },
            "by_priority": {
                p: sum(1 for s in unique_scenarios if s.get("priority") == p)
                for p in ["P0", "P1", "P2", "P3"]
            },
            "list": unique_scenarios,
        },
        "regulation": {
            "total_rules": len(all_rules),
            "manual_keys": all_manual_keys,
            "rules": all_rules[:50],  # ilk 50 kural
        },
        "automation": {
            "matrix": last_matrix,
            "summary": {
                d: sum(1 for m in last_matrix if d in m.get("decision", ""))
                for d in ["UI", "API", "DB", "MANUAL"]
            },
        },
        "generated_code": {
            "bdd_features": all_bdd,
            "playwright_tests": all_playwright,
            "api_tests": all_api,
            "total_files": len(all_bdd) + len(all_playwright) + len(all_api),
        },
        "improvements": [
            c.improvements.get("learning_summary", "")
            for c in cycles
            if c.improvements.get("learning_summary")
        ],
        # Phase A metrikleri
        "quality_gate": {
            "scores": [c.quality_verdict.get("weighted_score", 0) for c in cycles if c.quality_verdict],
            "verdicts": [c.quality_verdict.get("verdict", "N/A") for c in cycles if c.quality_verdict],
            "avg_score": round(
                sum(c.quality_verdict.get("weighted_score", 0) for c in cycles if c.quality_verdict)
                / max(sum(1 for c in cycles if c.quality_verdict), 1), 2
            ),
        },
        "auto_healing": {
            "total_healed": sum(c.heal_results.get("healed", 0) for c in cycles),
            "total_broken": sum(c.heal_results.get("total_broken", 0) for c in cycles),
        },
        "coverage_analysis": {
            "total_gaps": sum(len(c.coverage_gaps) for c in cycles),
            "high_severity": sum(
                sum(1 for g in c.coverage_gaps if g.get("severity") == "high")
                for c in cycles
            ),
        },
        "risk_scoring": {
            "tests_scored": sum(len(c.risk_scores) for c in cycles),
        },
    }
