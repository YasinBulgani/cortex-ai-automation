"""Coder Agent — Gherkin + locator → Playwright TS."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from ..prompts.coder import CODER_SYSTEM_PROMPT, build_coder_user_prompt
from ..schemas.code import CodeFile, GeneratedCode
from ..state import AgentState
from ..tools.ai_gateway import ai_complete
from .base import BaseAgent

logger = logging.getLogger(__name__)


class CoderAgent(BaseAgent):
    name = "coder"
    description = "Gherkin + locator → Playwright TS kod"

    async def execute(self, state: AgentState) -> AgentState:
        scenarios = state.get("scenarios", [])
        if not scenarios:
            state["generated_code"] = GeneratedCode().to_state_dict()
            return state

        feature_text = self._read_feature(scenarios[0] if scenarios else {})
        if not feature_text:
            state["generated_code"] = GeneratedCode().to_state_dict()
            return state

        locators_state = state.get("locators", [])
        locators_json = json.dumps(
            [l if isinstance(l, dict) else l.to_state_dict() for l in locators_state],
            ensure_ascii=False, indent=2,
        )[:8000]

        target_url = state.get("input_payload", {}).get("url", "")
        user_prompt = build_coder_user_prompt(
            feature_text=feature_text,
            locators_json=locators_json,
            target_url=target_url,
        )

        try:
            response = await ai_complete(
                user_message=user_prompt,
                system_message=CODER_SYSTEM_PROMPT,
                task_type="generate_playwright",
                temperature=0.2,
                max_tokens=6000,
                json_mode=True,
                project_id=state.get("project_id"),
                correlation_id=state.get("run_id"),
            )
        except Exception as exc:
            logger.exception("Coder LLM: %s", exc)
            state.setdefault("errors", []).append({
                "agent": self.name, "error": str(exc),
                "error_type": type(exc).__name__,
            })
            state["generated_code"] = GeneratedCode().to_state_dict()
            return state

        self.track_cost(
            state,
            tokens_input=response.usage.input_tokens,
            tokens_output=response.usage.output_tokens,
            model=response.model_used,
        )

        parsed = response.parsed_json()
        if not isinstance(parsed, dict):
            logger.warning("Coder JSON parse fail")
            code = GeneratedCode(
                files=[CodeFile(
                    path="e2e/generated/raw.spec.ts",
                    content=response.content,
                    language="typescript",
                    purpose="spec",
                )],
            )
        else:
            files: list[CodeFile] = []
            for f in parsed.get("files", []):
                if not isinstance(f, dict):
                    continue
                try:
                    f.setdefault("language", "typescript")
                    f.setdefault("purpose", "spec")
                    files.append(CodeFile(**f))
                except Exception as exc:
                    logger.debug("File parse skip: %s", exc)
            code = GeneratedCode(
                generator_type=parsed.get("generator_type", "e2e"),
                files=files,
            )

        output_root = self._output_dir(state.get("run_id", "run"))
        for cf in code.files:
            try:
                cf.write_to_disk(output_root)
            except Exception as exc:
                logger.warning("Coder yazım: %s", exc)

        state["generated_code"] = code.to_state_dict()
        logger.info(
            "Coder tamam — %d dosya (%d spec, %d PO)",
            len(code.files), len(code.spec_files()), len(code.page_object_files()),
        )
        return state

    def _read_feature(self, scenario_entry: dict) -> str:
        if not isinstance(scenario_entry, dict):
            return ""
        path = scenario_entry.get("feature_path")
        if path:
            try:
                return Path(path).read_text(encoding="utf-8")
            except Exception:
                pass
        return scenario_entry.get("raw", "")

    def _output_dir(self, run_id: str) -> Path:
        base = Path("e2e/generated") / f"agent-v2-{run_id[:8]}"
        if not Path("e2e").exists():
            base = Path("/tmp/twai_generated_code") / run_id[:8]  # nosec B108
        base.mkdir(parents=True, exist_ok=True)
        return base


_agent = CoderAgent()


async def coder_node(state: AgentState) -> AgentState:
    return await _agent(state)
