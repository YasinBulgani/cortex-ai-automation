"""
Enriched BDD Generator — turns requirements into high-quality Gherkin scenarios.

Pipeline:
  1. Load context: requirement, existing scenarios, related requirements,
     KnowledgeStore patterns, CrossAgentMemory feedback
  2. Step library scan: extract reusable step patterns from all project scenarios
  3. Generate with LLM: SmartRouter model, few-shot examples, banking domain context
  4. Post-process: validate Gherkin, compute step reuse, quality scoring, tagging

Python 3.9 compatible (no PEP 604 unions, no from __future__ import annotations).
"""

import json
import logging
import re
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.tspm.models import (
    TspmRequirement,
    TspmScenario,
    TspmScenarioRequirement,
)

logger = logging.getLogger(__name__)

# ── Turkish Gherkin keywords ─────────────────────────────────────────────────

_TR_KEYWORDS = {
    "feature": ["Ozellik:", "Özellik:"],
    "scenario": ["Senaryo:", "Senaryo Taslagi:"],
    "given": ["Diyelim ki", "Olduğu gibi"],
    "when": ["Eğer"],
    "then": ["O zaman"],
    "and": ["Ve"],
    "but": ["Ama"],
}

_EN_KEYWORDS = {
    "feature": ["Feature:"],
    "scenario": ["Scenario:", "Scenario Outline:"],
    "given": ["Given"],
    "when": ["When"],
    "then": ["Then"],
    "and": ["And"],
    "but": ["But"],
}

_ALL_STEP_PREFIXES = (
    _TR_KEYWORDS["given"] + _TR_KEYWORDS["when"] + _TR_KEYWORDS["then"]
    + _TR_KEYWORDS["and"] + _TR_KEYWORDS["but"]
    + _EN_KEYWORDS["given"] + _EN_KEYWORDS["when"] + _EN_KEYWORDS["then"]
    + _EN_KEYWORDS["and"] + _EN_KEYWORDS["but"]
)

_GIVEN_PREFIXES = _TR_KEYWORDS["given"] + _EN_KEYWORDS["given"]
_WHEN_PREFIXES = _TR_KEYWORDS["when"] + _EN_KEYWORDS["when"]
_THEN_PREFIXES = _TR_KEYWORDS["then"] + _EN_KEYWORDS["then"]
_AND_PREFIXES = _TR_KEYWORDS["and"] + _EN_KEYWORDS["and"]

# ── Banking domain context (for system prompt) ──────────────────────────────

_BANKING_DOMAIN_CONTEXT = """\
## Bankacilik Domain Bilgisi

Turkiye bankacilik regülasyonlari ve terminoloji:
- BDDK (Bankacilik Duzenleme ve Denetleme Kurumu): Bankacilik islem limitleri, gunluk/aylik transfer limitleri
- KVKK (Kisisel Verilerin Korunmasi Kanunu): Musteri verileri (TCKN, IBAN, telefon) korunmali
- MASAK: 75.000 TRY ustu islemler icin supheli islem bildirimi
- PSD2 / Acik Bankacilik: 3. parti erisim, SCA (Strong Customer Authentication)
- SPK: Yatirim islemleri icin ek kurallar

Temel terminoloji:
- Hesap (Account), Bakiye (Balance), Transfer, Havale, EFT, SWIFT
- Odeme (Payment), Fatura (Invoice/Bill), Taksit (Installment)
- Musteri (Customer), IBAN, TCKN (TC Kimlik Numarasi)
- Kredi (Loan/Credit), Faiz (Interest), Vade (Maturity)
- Doviz (Foreign Currency), Kur (Exchange Rate)
- Kart (Card), CVV, PIN, OTP, 3D Secure
"""


# ═══════════════════════════════════════════════════════════════════════════════
# BDDGenerator
# ═══════════════════════════════════════════════════════════════════════════════

class BDDGenerator:
    """Enriched BDD scenario generator that produces high-quality Gherkin."""

    def __init__(self, db: Session, project_id: str):
        self.db = db
        self.project_id = project_id
        # Lazy-init agent so import-time errors do not crash the module
        self._agent = None  # type: Any

    def _get_agent(self):
        # type: () -> Any
        if self._agent is None:
            from app.domains.agents.banking_team.base_agent import BaseAgent
            agent = BaseAgent()
            agent.name = "bdd_generator"
            agent.temperature = 0.35
            agent.max_tokens = 8192
            self._agent = agent
        return self._agent

    # ── Public API ───────────────────────────────────────────────────────────

    def generate_scenarios(
        self,
        requirement_id: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Full generation pipeline for a single requirement."""
        t0 = time.time()
        opts = options or {}

        # 1. Load context
        requirement = self._load_requirement(requirement_id)
        existing_scenarios = self._load_existing_scenarios(requirement_id)
        related_reqs = self._load_related_requirements(requirement)
        knowledge_ctx = self._query_knowledge(requirement)
        agent_ctx = self._get_agent_memory_context()

        # 2. Step library scan
        step_lib = self.get_step_library()

        # 3. LLM generation
        model_name = "unknown"
        try:
            from app.domains.ai.smart_model_router import route_model
            rec = route_model(
                task_type="test_generation",
                complexity="high",
                has_financial=True,
            )
            agent = self._get_agent()
            agent.model = rec.model
            agent.temperature = rec.temperature
            agent.max_tokens = rec.max_tokens
            model_name = rec.model
        except Exception as exc:
            logger.debug("SmartRouter unavailable, using default: %s", exc)

        system_prompt = self._build_system_prompt(
            requirement=requirement,
            existing_scenarios=existing_scenarios,
            related_reqs=related_reqs,
            step_lib=step_lib,
            knowledge_ctx=knowledge_ctx,
            agent_ctx=agent_ctx,
        )

        user_prompt = self._build_user_prompt(requirement, opts)

        few_shot = ""
        try:
            from app.domains.ai.few_shot_bank import get_few_shot_examples
            keywords = self._extract_keywords(requirement)
            few_shot = get_few_shot_examples("test_generation", keywords, max_examples=1)
        except Exception:
            pass

        if few_shot:
            system_prompt += "\n" + few_shot

        agent = self._get_agent()
        raw = agent.call_json(system_prompt, user_prompt)

        # 4. Post-process
        raw_scenarios = raw.get("scenarios", [])
        if not raw_scenarios and isinstance(raw.get("items"), list):
            raw_scenarios = raw["items"]

        processed = []
        for sc in raw_scenarios:
            processed.append(self._post_process_scenario(sc, step_lib))

        # Compute aggregates
        reuse_rates = [s["step_reuse_rate"] for s in processed if s.get("step_reuse_rate") is not None]
        avg_reuse = sum(reuse_rates) / len(reuse_rates) if reuse_rates else 0.0

        duration_ms = (time.time() - t0) * 1000

        # Fire-and-forget observability
        self._publish_generation_event(requirement, processed, duration_ms)

        return {
            "requirement_id": requirement_id,
            "requirement_title": requirement.title,
            "scenarios": processed,
            "step_library_size": step_lib["total_steps"],
            "avg_step_reuse": round(avg_reuse, 3),
            "generation_model": model_name,
            "duration_ms": round(duration_ms, 1),
        }

    def generate_for_module(self, module: str) -> Dict[str, Any]:
        """Generate BDD for all requirements whose source matches module."""
        stmt = (
            select(TspmRequirement)
            .where(TspmRequirement.project_id == self.project_id)
            .where(TspmRequirement.source == module)
        )
        reqs = list(self.db.scalars(stmt).all())
        if not reqs:
            return {
                "module": module,
                "requirement_count": 0,
                "results": [],
                "total_scenarios": 0,
            }

        results = []
        total_scenarios = 0
        for req in reqs:
            try:
                result = self.generate_scenarios(req.id)
                results.append(result)
                total_scenarios += len(result.get("scenarios", []))
            except Exception as exc:
                logger.warning("BDD generation failed for req %s: %s", req.id, exc)
                results.append({
                    "requirement_id": req.id,
                    "requirement_title": req.title,
                    "error": str(exc),
                    "scenarios": [],
                })

        return {
            "module": module,
            "requirement_count": len(reqs),
            "results": results,
            "total_scenarios": total_scenarios,
        }

    def bulk_generate(
        self,
        requirement_ids: List[str],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate BDD for multiple requirements."""
        results = []
        total_scenarios = 0
        total_duration = 0.0

        for req_id in requirement_ids:
            try:
                result = self.generate_scenarios(req_id, options)
                results.append(result)
                total_scenarios += len(result.get("scenarios", []))
                total_duration += result.get("duration_ms", 0)
            except Exception as exc:
                logger.warning("Bulk BDD generation failed for req %s: %s", req_id, exc)
                results.append({
                    "requirement_id": req_id,
                    "requirement_title": "",
                    "error": str(exc),
                    "scenarios": [],
                })

        return {
            "requirement_count": len(requirement_ids),
            "results": results,
            "total_scenarios": total_scenarios,
            "total_duration_ms": round(total_duration, 1),
        }

    def suggest_edge_cases(self, requirement_id: str) -> Dict[str, Any]:
        """Suggest additional edge cases and negative scenarios."""
        requirement = self._load_requirement(requirement_id)
        existing = self._load_existing_scenarios(requirement_id)

        existing_summary = ""
        if existing:
            titles = [s.title for s in existing]
            existing_summary = "\n".join("- " + t for t in titles)

        system_prompt = (
            "Sen bir kidemli QA muhendisisin. Bankacilik uygulamalari icin edge case "
            "ve negatif senaryo analizi yapiyorsun.\n\n"
            + _BANKING_DOMAIN_CONTEXT
            + "\n\nMevcut senaryolari inceleyerek eksik olan edge case, negatif ve "
            "boundary senaryolarini onermelisin. Her oneri icin Gherkin formati kullan.\n\n"
            "MUTLAKA asagidaki JSON formatinda yanit ver:\n"
            '{\n  "suggestions": [\n    {\n'
            '      "scenario_type": "edge_case|negative|boundary",\n'
            '      "title": "Senaryo basligi",\n'
            '      "description": "Neden bu senaryo gerekli",\n'
            '      "gherkin": "Ozellik: ...\\n  Senaryo: ...\\n    ...",\n'
            '      "rationale": "Bu senaryonun test edilme gerekçesi"\n'
            "    }\n  ]\n}"
        )

        user_prompt = (
            "Gereksinim:\n"
            "Baslik: {title}\n"
            "Aciklama: {desc}\n\n"
            "Mevcut Senaryolar:\n{existing}\n\n"
            "Yukaridaki gereksinim ve mevcut senaryolari analiz ederek "
            "eksik edge case, negatif ve boundary senaryolarini oner."
        ).format(
            title=requirement.title,
            desc=requirement.description or "",
            existing=existing_summary or "(Henuz senaryo yok)",
        )

        agent = self._get_agent()
        raw = agent.call_json(system_prompt, user_prompt)

        suggestions = raw.get("suggestions", [])
        if not suggestions and isinstance(raw.get("items"), list):
            suggestions = raw["items"]

        return {
            "requirement_id": requirement_id,
            "existing_scenario_count": len(existing),
            "suggestions": suggestions,
        }

    def get_step_library(self) -> Dict[str, Any]:
        """Extract full step library from all project scenarios."""
        stmt = (
            select(TspmScenario)
            .where(TspmScenario.project_id == self.project_id)
        )
        scenarios = list(self.db.scalars(stmt).all())

        given_steps = []  # type: List[str]
        when_steps = []   # type: List[str]
        then_steps = []   # type: List[str]
        and_steps = []    # type: List[str]
        all_steps = []    # type: List[str]

        for sc in scenarios:
            steps_data = sc.steps or []
            for step in steps_data:
                if not isinstance(step, dict):
                    continue
                kw = step.get("keyword", "").strip()
                text = step.get("text", "").strip()
                if not text:
                    continue

                full_step = "{kw} {text}".format(kw=kw, text=text) if kw else text
                all_steps.append(full_step)

                kw_lower = kw.lower()
                if any(g.lower() in kw_lower for g in _GIVEN_PREFIXES):
                    given_steps.append(text)
                elif any(w.lower() in kw_lower for w in _WHEN_PREFIXES):
                    when_steps.append(text)
                elif any(t.lower() in kw_lower for t in _THEN_PREFIXES):
                    then_steps.append(text)
                elif any(a.lower() in kw_lower for a in _AND_PREFIXES):
                    and_steps.append(text)

            # Also parse from gherkin text in description (some scenarios store gherkin there)
            desc = sc.description or ""
            for line in desc.split("\n"):
                stripped = line.strip()
                for prefix in _ALL_STEP_PREFIXES:
                    if stripped.startswith(prefix):
                        step_text = stripped[len(prefix):].strip()
                        if step_text:
                            all_steps.append(stripped)
                        break

        # Deduplicate while preserving order
        given_unique = list(dict.fromkeys(given_steps))
        when_unique = list(dict.fromkeys(when_steps))
        then_unique = list(dict.fromkeys(then_steps))
        and_unique = list(dict.fromkeys(and_steps))

        # Most used steps
        counter = Counter(all_steps)
        most_used = [
            {"step": step, "count": count}
            for step, count in counter.most_common(20)
        ]

        return {
            "total_steps": len(set(all_steps)),
            "given_steps": given_unique,
            "when_steps": when_unique,
            "then_steps": then_unique,
            "and_steps": and_unique,
            "most_used": most_used,
        }

    def validate_gherkin(self, gherkin: str) -> Dict[str, Any]:
        """Validate Gherkin syntax and return errors/warnings."""
        errors = []   # type: List[str]
        warnings = [] # type: List[str]

        if not gherkin or not gherkin.strip():
            return {"valid": False, "errors": ["Gherkin metni bos"], "warnings": []}

        lines = gherkin.strip().split("\n")
        stripped_lines = [l.strip() for l in lines]

        # Check Feature/Ozellik presence
        has_feature = any(
            l.startswith(kw) for l in stripped_lines
            for kw in (_TR_KEYWORDS["feature"] + _EN_KEYWORDS["feature"])
        )
        if not has_feature:
            errors.append("Ozellik:/Feature: satirı bulunamadı")

        # Check Scenario presence
        has_scenario = any(
            l.startswith(kw) for l in stripped_lines
            for kw in (_TR_KEYWORDS["scenario"] + _EN_KEYWORDS["scenario"])
        )
        if not has_scenario:
            errors.append("Senaryo:/Scenario: satirı bulunamadı")

        # Check step keywords
        step_lines = [
            l for l in stripped_lines
            if any(l.startswith(p) for p in _ALL_STEP_PREFIXES)
        ]
        if not step_lines:
            errors.append("Hicbir adim satirı bulunamadı (Given/When/Then veya Turkce karsiliklari)")

        # Check for empty steps
        for i, line in enumerate(stripped_lines):
            for prefix in _ALL_STEP_PREFIXES:
                if line == prefix or line == prefix.rstrip(":"):
                    errors.append("Satir {n}: Bos adim — '{prefix}'".format(n=i + 1, prefix=prefix))

        # Check for duplicate steps within same scenario
        seen_steps = set()  # type: set
        for line in stripped_lines:
            for prefix in _ALL_STEP_PREFIXES:
                if line.startswith(prefix):
                    if line in seen_steps:
                        warnings.append("Tekrarlanan adim: '{line}'".format(line=line))
                    seen_steps.add(line)
                    break

        # Check Given-When-Then order within scenarios
        step_order = []  # type: List[str]
        for line in stripped_lines:
            for kw_type in ["given", "when", "then"]:
                prefixes = _TR_KEYWORDS[kw_type] + _EN_KEYWORDS[kw_type]
                if any(line.startswith(p) for p in prefixes):
                    step_order.append(kw_type)
                    break

        if step_order:
            # Check that Given comes before When, When before Then
            given_idx = -1
            when_idx = -1
            then_idx = -1
            for i, s in enumerate(step_order):
                if s == "given" and given_idx == -1:
                    given_idx = i
                elif s == "when" and when_idx == -1:
                    when_idx = i
                elif s == "then" and then_idx == -1:
                    then_idx = i

            if when_idx != -1 and given_idx != -1 and when_idx < given_idx:
                warnings.append("Given adimlari When adimlarindan once gelmeli")
            if then_idx != -1 and when_idx != -1 and then_idx < when_idx:
                warnings.append("When adimlari Then adimlarindan once gelmeli")

        valid = len(errors) == 0
        return {"valid": valid, "errors": errors, "warnings": warnings}

    # ── Context loading helpers ──────────────────────────────────────────────

    def _load_requirement(self, requirement_id: str) -> TspmRequirement:
        req = self.db.get(TspmRequirement, requirement_id)
        if req is None:
            raise ValueError("Gereksinim bulunamadi: {rid}".format(rid=requirement_id))
        if req.project_id != self.project_id:
            raise ValueError("Gereksinim bu projeye ait degil")
        return req

    def _load_existing_scenarios(self, requirement_id: str) -> List[TspmScenario]:
        """Load scenarios linked to this requirement."""
        stmt = (
            select(TspmScenario)
            .join(TspmScenarioRequirement, TspmScenarioRequirement.scenario_id == TspmScenario.id)
            .where(TspmScenarioRequirement.requirement_id == requirement_id)
            .where(TspmScenario.project_id == self.project_id)
        )
        return list(self.db.scalars(stmt).all())

    def _load_related_requirements(self, requirement: TspmRequirement) -> List[TspmRequirement]:
        """Load requirements from the same source (module) or with similar title."""
        stmt = (
            select(TspmRequirement)
            .where(TspmRequirement.project_id == self.project_id)
            .where(TspmRequirement.id != requirement.id)
        )
        if requirement.source:
            stmt = stmt.where(TspmRequirement.source == requirement.source)
        results = list(self.db.scalars(stmt.limit(10)).all())
        return results

    def _query_knowledge(self, requirement: TspmRequirement) -> str:
        """Query KnowledgeStore for relevant patterns."""
        try:
            from app.domains.ai.knowledge_store import KnowledgeStore
            store = KnowledgeStore(project_id=self.project_id)
            query = "BDD senaryo {title} {desc}".format(
                title=requirement.title,
                desc=(requirement.description or "")[:200],
            )
            chunks = store.retrieve(query, top_k=3, sources=["feature_file", "insight"])
            if chunks:
                return "\n".join(
                    "[{src}] {content}".format(src=c.source, content=c.content[:300])
                    for c in chunks
                )
        except Exception as exc:
            logger.debug("KnowledgeStore query failed: %s", exc)
        return ""

    def _get_agent_memory_context(self) -> str:
        """Get CrossAgentMemory context."""
        try:
            from app.domains.ai.cross_agent_memory import CrossAgentMemory
            return CrossAgentMemory.get_context_for_agent(
                "bdd_generator",
                project_id=self.project_id,
                relevant_tags=["bdd", "gherkin", "scenario", "quality"],
                max_chars=1500,
            )
        except Exception as exc:
            logger.debug("CrossAgentMemory context failed: %s", exc)
        return ""

    def _extract_keywords(self, requirement: TspmRequirement) -> List[str]:
        """Extract keywords from requirement for few-shot matching."""
        text = "{title} {desc}".format(
            title=requirement.title,
            desc=requirement.description or "",
        ).lower()

        banking_terms = [
            "transfer", "havale", "eft", "iban", "hesap", "bakiye",
            "odeme", "fatura", "musteri", "kredi", "kart", "login",
            "auth", "otp", "doviz", "kur",
        ]
        found = [t for t in banking_terms if t in text]
        return found[:5] if found else ["transfer"]

    # ── Prompt building ──────────────────────────────────────────────────────

    def _build_system_prompt(
        self,
        requirement: TspmRequirement,
        existing_scenarios: List[TspmScenario],
        related_reqs: List[TspmRequirement],
        step_lib: Dict[str, Any],
        knowledge_ctx: str,
        agent_ctx: str,
    ) -> str:
        sections = []  # type: List[str]

        sections.append(
            "Sen bir kidemli QA muhendisisin. Bankacilik uygulamalari icin "
            "BDD (Behavior-Driven Development) formatinda test senaryolari uretiyorsun.\n\n"
            "KURALLAR:\n"
            "1. Turkce Gherkin kullan: Ozellik:, Senaryo:, Diyelim ki, Ve, Eger, O zaman\n"
            "2. Her senaryo icin cesitli tipler uret: happy_path, negative, edge_case, boundary\n"
            "3. Senaryolar test edilebilir, aciK ve net olmali\n"
            "4. Mevcut adim kutuphanesinden mumkun oldugunca yeniden kullan\n"
            "5. Bankacilik terminolojisini dogru kullan\n"
            "6. KVKK, BDDK, MASAK regülasyonlarini goz onunde bulundur\n"
        )

        sections.append(_BANKING_DOMAIN_CONTEXT)

        # Step library
        if step_lib["total_steps"] > 0:
            lib_section = "## Mevcut Adim Kutuphanesi (yeniden kullan!)\n"
            for category in ["given_steps", "when_steps", "then_steps"]:
                steps = step_lib.get(category, [])[:15]
                if steps:
                    label = category.replace("_steps", "").upper()
                    lib_section += "\n{label}:\n".format(label=label)
                    for s in steps:
                        lib_section += "- {s}\n".format(s=s)
            sections.append(lib_section)

        # Existing scenarios (to avoid duplication)
        if existing_scenarios:
            existing_section = "## Mevcut Senaryolar (TEKRAR ETME!)\n"
            for sc in existing_scenarios[:10]:
                existing_section += "- {title}\n".format(title=sc.title)
            sections.append(existing_section)

        # Related requirements
        if related_reqs:
            related_section = "## Ilgili Gereksinimler\n"
            for rr in related_reqs[:5]:
                related_section += "- [{eid}] {title}\n".format(
                    eid=rr.external_id, title=rr.title,
                )
            sections.append(related_section)

        # Knowledge context
        if knowledge_ctx:
            sections.append(
                "## Domain Bilgisi (KnowledgeStore)\n{ctx}\n".format(ctx=knowledge_ctx)
            )

        # Agent memory context
        if agent_ctx:
            sections.append(agent_ctx)

        # Output format
        sections.append(
            "\n## CIKTI FORMATI\n"
            "MUTLAKA asagidaki JSON formatinda yanit ver, baska hicbir sey yazma:\n"
            '{\n  "scenarios": [\n    {\n'
            '      "title": "Senaryo basligi",\n'
            '      "feature_name": "Ozellik adi",\n'
            '      "gherkin": "Ozellik: ...\\n  Senaryo: ...\\n    Diyelim ki ...\\n    Eger ...\\n    O zaman ...",\n'
            '      "steps": [{"keyword": "Diyelim ki", "text": "adim metni"}],\n'
            '      "tags": ["@happy_path"],\n'
            '      "scenario_type": "happy_path"\n'
            "    }\n  ]\n}"
        )

        return "\n\n".join(sections)

    def _build_user_prompt(
        self,
        requirement: TspmRequirement,
        opts: Dict[str, Any],
    ) -> str:
        max_scenarios = opts.get("max_scenarios", 6)
        include_negative = opts.get("include_negative", True)
        include_edge = opts.get("include_edge", True)
        include_boundary = opts.get("include_boundary", True)

        types_list = ["happy_path"]
        if include_negative:
            types_list.append("negative")
        if include_edge:
            types_list.append("edge_case")
        if include_boundary:
            types_list.append("boundary")

        prompt = (
            "Asagidaki gereksinim icin BDD senaryolari uret.\n\n"
            "Gereksinim ID: {eid}\n"
            "Baslik: {title}\n"
            "Aciklama: {desc}\n"
            "Oncelik: {priority}\n"
            "Kaynak: {source}\n\n"
            "Istenen senaryo tipleri: {types}\n"
            "Maksimum senaryo sayisi: {max_sc}\n"
        ).format(
            eid=requirement.external_id,
            title=requirement.title,
            desc=requirement.description or "(Aciklama yok)",
            priority=requirement.priority,
            source=requirement.source or "(Kaynak belirtilmemis)",
            types=", ".join(types_list),
            max_sc=max_scenarios,
        )

        extra = opts.get("extra_instructions", "")
        if extra:
            prompt += "\nEk Talimatlar: {extra}\n".format(extra=extra)

        return prompt

    # ── Post-processing ──────────────────────────────────────────────────────

    def _post_process_scenario(
        self,
        raw: Dict[str, Any],
        step_lib: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate, score and tag a single generated scenario."""
        title = raw.get("title", "Isimsiz Senaryo")
        feature_name = raw.get("feature_name", raw.get("feature", ""))
        gherkin = raw.get("gherkin", "")
        steps = raw.get("steps", [])
        tags = raw.get("tags", [])
        scenario_type = raw.get("scenario_type", "happy_path")

        # Ensure tags are prefixed with @
        normalized_tags = []
        for t in tags:
            tag = t if t.startswith("@") else "@" + t
            normalized_tags.append(tag)

        # Add scenario_type tag if not present
        type_tag = "@" + scenario_type
        if type_tag not in normalized_tags:
            normalized_tags.insert(0, type_tag)

        # Extract steps from gherkin if steps list is empty
        if not steps and gherkin:
            steps = self._extract_steps_from_gherkin(gherkin)

        # Calculate step reuse rate
        reuse_rate = self._compute_step_reuse(steps, step_lib)

        # Quality scoring
        quality_score = self._compute_quality_score(
            title=title,
            gherkin=gherkin,
            steps=steps,
            scenario_type=scenario_type,
            reuse_rate=reuse_rate,
        )

        return {
            "title": title,
            "feature_name": feature_name,
            "gherkin": gherkin,
            "steps": steps,
            "tags": normalized_tags,
            "scenario_type": scenario_type,
            "step_reuse_rate": round(reuse_rate, 3),
            "quality_score": round(quality_score, 1),
        }

    def _extract_steps_from_gherkin(self, gherkin: str) -> List[Dict[str, Any]]:
        """Parse step keywords and text from raw Gherkin."""
        steps = []  # type: List[Dict[str, Any]]
        for line in gherkin.split("\n"):
            stripped = line.strip()
            for prefix in _ALL_STEP_PREFIXES:
                if stripped.startswith(prefix):
                    text = stripped[len(prefix):].strip()
                    if text:
                        # Check for data table
                        table = None  # type: Optional[List[Any]]
                        steps.append({
                            "keyword": prefix.strip(),
                            "text": text,
                            "table": table,
                        })
                    break
        return steps

    def _compute_step_reuse(
        self,
        steps: List[Dict[str, Any]],
        step_lib: Dict[str, Any],
    ) -> float:
        """Compute what fraction of generated steps match existing library."""
        if not steps:
            return 0.0

        # Gather all known step texts
        known_steps = set()  # type: set
        for category in ["given_steps", "when_steps", "then_steps", "and_steps"]:
            for s in step_lib.get(category, []):
                known_steps.add(s.lower().strip())

        if not known_steps:
            return 0.0

        matched = 0
        for step in steps:
            text = step.get("text", "").lower().strip()
            if text in known_steps:
                matched += 1
            else:
                # Fuzzy match: check if any known step is contained or vice versa
                for known in known_steps:
                    if _fuzzy_step_match(text, known):
                        matched += 1
                        break

        return matched / len(steps)

    def _compute_quality_score(
        self,
        title: str,
        gherkin: str,
        steps: List[Dict[str, Any]],
        scenario_type: str,
        reuse_rate: float,
    ) -> float:
        """Compute quality score 0-10."""
        score = 0.0

        # Title quality (0-2)
        if title and len(title) > 10:
            score += 1.0
        if title and len(title) > 20:
            score += 0.5
        if title and not title.startswith("Senaryo"):
            score += 0.5

        # Gherkin structure (0-3)
        if gherkin:
            validation = self.validate_gherkin(gherkin)
            if validation["valid"]:
                score += 2.0
            elif not validation["errors"]:
                score += 1.0
            if not validation.get("warnings"):
                score += 1.0

        # Steps quality (0-3)
        if steps:
            if len(steps) >= 3:
                score += 1.0
            if len(steps) >= 5:
                score += 0.5
            # Has Given, When, Then
            keywords = [s.get("keyword", "").lower() for s in steps]
            kw_text = " ".join(keywords)
            has_given = any(g.lower() in kw_text for g in _GIVEN_PREFIXES)
            has_when = any(w.lower() in kw_text for w in _WHEN_PREFIXES)
            has_then = any(t.lower() in kw_text for t in _THEN_PREFIXES)
            if has_given and has_when and has_then:
                score += 1.5

        # Step reuse bonus (0-1)
        score += reuse_rate * 1.0

        # Scenario type variety bonus (0-1)
        if scenario_type in ("negative", "edge_case", "boundary"):
            score += 1.0

        return min(score, 10.0)

    # ── Observability ────────────────────────────────────────────────────────

    def _publish_generation_event(
        self,
        requirement: TspmRequirement,
        scenarios: List[Dict[str, Any]],
        duration_ms: float,
    ) -> None:
        """Fire-and-forget: publish to CrossAgentMemory."""
        try:
            from app.domains.ai.cross_agent_memory import CrossAgentMemory
            CrossAgentMemory.publish(
                agent_name="bdd_generator",
                event_type="test_generated",
                data={
                    "project_id": self.project_id,
                    "requirement_id": requirement.id,
                    "requirement_title": requirement.title,
                    "scenario_count": len(scenarios),
                    "avg_quality": (
                        sum(s.get("quality_score", 0) for s in scenarios) / len(scenarios)
                        if scenarios else 0
                    ),
                    "duration_ms": round(duration_ms, 1),
                },
                tags=["bdd", "gherkin", requirement.priority],
            )
        except Exception as exc:
            logger.debug("CrossAgentMemory publish failed: %s", exc)


# ── Utility ──────────────────────────────────────────────────────────────────

def _fuzzy_step_match(generated: str, known: str) -> bool:
    """Check if two step texts are similar enough to count as reused."""
    if not generated or not known:
        return False
    # Exact match
    if generated == known:
        return True
    # One contains the other
    if generated in known or known in generated:
        return True
    # Word overlap >= 60%
    gen_words = set(generated.split())
    known_words = set(known.split())
    if not gen_words or not known_words:
        return False
    overlap = gen_words & known_words
    overlap_ratio = len(overlap) / max(len(gen_words), len(known_words))
    return overlap_ratio >= 0.6


# ── Legacy compatibility — keep old function signature working ───────────────

def generate_bdd_scenarios(
    analysis_text: str,
    extra_instructions: str = "",
) -> List[Dict[str, Any]]:
    """Legacy wrapper for backward compatibility with existing router endpoints.

    Provider priority: AI Gateway -> OpenAI -> Anthropic -> rule-based fallback.
    """
    import json as _json
    import re as _re

    _SYSTEM_PROMPT = (
        "Sen bir kidemli QA muhendisisin. Kullanici sana bir analiz dokumani verecek.\n"
        "Bu dokumani analiz ederek BDD formatinda test senaryolari uret.\n\n"
        "Kurallar:\n"
        "1. Her senaryo Gherkin formatinda olmali: Feature, Scenario, Given/When/Then adimlari.\n"
        "2. Turkce anahtar kelimeler kullan: Ozellik, Senaryo, Diyelim ki, Ve, Eger, O zaman.\n"
        "3. Senaryolar kapsamli ve test edilebilir olmali.\n"
        "4. Pozitif ve negatif senaryolari dahil et.\n"
        "5. Sinir deger analizlerini dahil et.\n\n"
        "MUTLAKA asagidaki JSON formatinda yanit ver:\n"
        '{\n  "scenarios": [\n    {\n'
        '      "title": "Senaryo basligi",\n'
        '      "description": "Kisa aciklama",\n'
        '      "feature": "Ozellik adi",\n'
        '      "gherkin": "Ozellik: ...\\n  Senaryo: ...",\n'
        '      "tags": ["pozitif"],\n'
        '      "steps": [\n'
        '        {"keyword": "Diyelim ki", "text": "adim metni"}\n'
        "      ]\n"
        "    }\n  ]\n}"
    )

    def _strip_fences(raw):
        # type: (str) -> str
        cleaned = raw.strip()
        cleaned = _re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = _re.sub(r"\n?```$", "", cleaned)
        return cleaned.strip()

    def _parse_llm_json(raw):
        # type: (str) -> List[Dict[str, Any]]
        cleaned = _strip_fences(raw)
        try:
            parsed = _json.loads(cleaned)
        except _json.JSONDecodeError:
            match = _re.search(r"\{.*\}", cleaned, _re.DOTALL)
            if match:
                parsed = _json.loads(match.group())
            else:
                logger.error("LLM response is not valid JSON: %s", raw[:500])
                raise ValueError("AI yaniti gecerli JSON formatinda degil.")
        scenarios = parsed.get("scenarios", [])
        if not isinstance(scenarios, list):
            raise ValueError("AI yanitinda 'scenarios' listesi bulunamadi.")
        return scenarios

    user_content = "Analiz Dokumani:\n\n{text}".format(text=analysis_text)
    if extra_instructions:
        user_content += "\n\nEk Talimatlar:\n{extra}".format(extra=extra_instructions)

    # 1) AI Gateway
    try:
        from app.domains.ai.gateway_client import gateway_complete, gateway_is_available
        if gateway_is_available():
            raw = gateway_complete(
                task_type="generate_gherkin",
                user_message=user_content,
                system_message=_SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=4000,
            )
            return _parse_llm_json(raw)
    except Exception as exc:
        logger.warning("AI Gateway BDD basarisiz: %s", exc)

    # 2) OpenAI (cached client)
    try:
        from app.config import settings
        if getattr(settings, "openai_api_key", None):
            from app.domains.ai.service import _get_openai_client
            client = _get_openai_client()
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            return _parse_llm_json(raw)
    except Exception as exc:
        logger.warning("OpenAI BDD basarisiz: %s", exc)

    # 3) Anthropic (cached client)
    try:
        from app.config import settings as _settings
        if getattr(_settings, "anthropic_api_key", None):
            from app.domains.ai.service import _get_anthropic_client
            client = _get_anthropic_client()
            response = client.messages.create(
                model=_settings.anthropic_model,
                max_tokens=4096,
                system=_SYSTEM_PROMPT + "\n\nYanit MUTLAKA gecerli JSON objesi olmali.",
                messages=[{"role": "user", "content": user_content}],
            )
            raw = response.content[0].text
            return _parse_llm_json(raw)
    except Exception as exc:
        logger.warning("Anthropic BDD basarisiz: %s", exc)

    # 4) Rule-based fallback
    logger.info("LLM unavailable — using rule-based BDD fallback")
    sentences = _re.split(r"[.!?\n]+", analysis_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    scenarios = []  # type: List[Dict[str, Any]]
    for i, sentence in enumerate(sentences[:10]):
        title = "Senaryo {n}: {s}".format(n=i + 1, s=sentence[:60])
        gherkin = (
            "Ozellik: Analiz Senaryosu\n"
            "  Senaryo: {title}\n"
            "    Diyelim ki sistem hazir durumda\n"
            "    Eger {sent}\n"
            "    O zaman beklenen sonuc dogrulanir"
        ).format(title=title, sent=sentence.lower())
        scenarios.append({
            "title": title,
            "description": sentence,
            "feature": "Analiz Dokumani",
            "gherkin": gherkin,
            "tags": ["auto-generated", "fallback"],
            "steps": [
                {"keyword": "Diyelim ki", "text": "sistem hazir durumda"},
                {"keyword": "Eger", "text": sentence.lower()},
                {"keyword": "O zaman", "text": "beklenen sonuc dogrulanir"},
            ],
        })
    return scenarios
