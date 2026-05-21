"""Scenario Agent — Intent + AppMap → Gherkin."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from ..prompts.scenario import SCENARIO_SYSTEM_PROMPT, build_scenario_user_prompt
from ..prompts.registry import resolve_agent_system_prompt
from ..schemas.scenario import GherkinFeature, ScenarioSpec
from ..state import AgentState
from ..tools.ai_gateway import ai_complete
from ..tools.dsl_grounding import ground_steps
from ..tools.gherkin_parser import parse_gherkin_text
from .base import BaseAgent

logger = logging.getLogger(__name__)


class ScenarioAgent(BaseAgent):
    name = "scenario"
    description = "Intent + App Map → Gherkin feature"

    async def execute(self, state: AgentState) -> AgentState:
        intent = state.get("intent_graph")
        if not intent:
            state["scenarios"] = []
            return state

        query = (
            f"{intent.get('feature_area', '')} "
            f"{' '.join(intent.get('goals', []))} "
            f"{' '.join(intent.get('acceptance_criteria', [])[:5])}"
        )
        dsl_candidates = ground_steps(query, top_k=20, min_score=0.25)

        app_map_summary = self._build_app_map_summary(state.get("app_map", {}))

        user_prompt = build_scenario_user_prompt(
            intent_graph_json=json.dumps(intent, ensure_ascii=False, indent=2),
            app_map_summary=app_map_summary,
            dsl_candidates=dsl_candidates,
            max_scenarios=10,
        )

        try:
            system_prompt = resolve_agent_system_prompt(
                "generate_gherkin",
                SCENARIO_SYSTEM_PROMPT,
                tenant_id=state.get("tenant_id"),
            )
            response = await ai_complete(
                user_message=user_prompt,
                system_message=system_prompt,
                task_type="generate_gherkin",
                temperature=0.4,
                max_tokens=4000,
                json_mode=False,
                project_id=state.get("project_id"),
                correlation_id=state.get("run_id"),
            )
        except Exception as exc:
            logger.exception("Scenario LLM: %s", exc)
            state.setdefault("errors", []).append({
                "agent": self.name, "error": str(exc),
                "error_type": type(exc).__name__,
            })
            state["scenarios"] = []
            return state

        self.track_cost(
            state,
            tokens_input=response.usage.input_tokens,
            tokens_output=response.usage.output_tokens,
            model=response.model_used,
        )

        feature = parse_gherkin_text(response.content)
        if feature is None:
            state["scenarios"] = [{"raw": response.content, "parsed": False}]
            return state

        spec = ScenarioSpec(
            features=[feature],
            grounded_steps_count=self._count_grounded_steps(feature, dsl_candidates),
            novel_steps_count=self._count_novel_steps(feature, dsl_candidates),
        )
        feature_paths = self._write_feature_files(
            feature=feature,
            project_id=state.get("project_id", "default"),
            run_id=state.get("run_id", "run"),
        )

        state["scenarios"] = [
            {
                "name": feature.name,
                "tags": list(feature.tags),
                "scenario_count": len(feature.scenarios),
                "language": feature.language,
                "feature_path": feature_paths[0] if feature_paths else None,
                "grounded_count": spec.grounded_steps_count,
                "novel_count": spec.novel_steps_count,
            }
        ]
        logger.info(
            "Scenario tamam — %d senaryo, %d grounded, %d novel",
            len(feature.scenarios),
            spec.grounded_steps_count,
            spec.novel_steps_count,
        )
        return state

    def _build_app_map_summary(self, app_map: dict) -> str:
        if not app_map:
            return "(App Map yok)"
        pages = app_map.get("pages", [])
        forms = app_map.get("forms", [])
        apis = app_map.get("apis_observed", [])
        lines = [
            f"- {len(pages)} sayfa keşfedildi",
            f"- {len(forms)} form",
            f"- {len(apis)} API çağrısı gözlendi",
        ]
        if pages:
            lines.append("\nSayfalar (ilk 10):")
            for p in pages[:10]:
                url = p.get("url", "") if isinstance(p, dict) else ""
                title = p.get("title", "") if isinstance(p, dict) else ""
                lines.append(f"  • {title or '(başlıksız)'} — {url}")
        if forms:
            lines.append("\nFormlar (ilk 5):")
            for f in forms[:5]:
                fid = f.get("form_id") or f.get("form_name") or "(isimsiz)"
                lines.append(f"  • {fid} → {f.get('action', '')}")
        return "\n".join(lines)

    def _count_grounded_steps(self, feature, dsl_candidates):
        if not dsl_candidates:
            return 0
        dsl_lower = [d.lower() for d in dsl_candidates]
        count = 0
        for sc in feature.scenarios:
            for step in sc.steps:
                text_lower = step.text.lower()
                if any(self._similar(text_lower, d) for d in dsl_lower):
                    count += 1
        return count

    def _count_novel_steps(self, feature, dsl_candidates):
        total = sum(len(s.steps) for s in feature.scenarios)
        return total - self._count_grounded_steps(feature, dsl_candidates)

    def _similar(self, a, b, threshold=0.6):
        def bigrams(s):
            return {s[i : i + 2] for i in range(len(s) - 1)}
        ab, bb = bigrams(a), bigrams(b)
        if not ab or not bb:
            return False
        return len(ab & bb) / len(ab | bb) >= threshold

    def _write_feature_files(self, *, feature, project_id, run_id):
        try:
            base = Path("engine/features/generated")
            if not base.parent.exists():
                base = Path("/tmp/twai_generated_features")
            base.mkdir(parents=True, exist_ok=True)
            safe_name = feature.name.replace("/", "_").replace(" ", "_")[:60]
            fname = f"{safe_name}_{run_id[:8]}.feature"
            out_path = base / fname
            out_path.write_text(feature.to_gherkin_text(), encoding="utf-8")
            logger.info("Feature yazıldı: %s", out_path)
            return [str(out_path)]
        except Exception as exc:
            logger.warning("Feature yazılamadı: %s", exc)
            return []


_agent = ScenarioAgent()


async def scenario_node(state: AgentState) -> AgentState:
    return await _agent(state)
