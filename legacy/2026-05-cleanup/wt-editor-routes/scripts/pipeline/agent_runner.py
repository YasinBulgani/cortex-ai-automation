#!/usr/bin/env python3
"""
agent_runner.py — Tek bir rolü HuggingFace LLM ile çalıştırır.

Akış:
    1. state.json'dan item'ı bul
    2. Rol kartını + önceki artifact'leri topla
    3. HF LLM'e prompt gönder
    4. Yanıtı ilgili artifact dosyasına yaz
    5. Decision rol ise JSON çıktısını state.json'a yansıt (complete/approve/reject)
    6. stage.sh complete çağrısı

CLI:
    python3 agent_runner.py --item GAP-001 --role analyzer
    python3 agent_runner.py --item GAP-001 --role validator --dry-run
    python3 agent_runner.py --item GAP-001 --role analyzer --stream
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "pipeline"))

from llm import get_client, get_provider  # noqa: E402
from llm.hf_client import HFClient  # noqa: E402 (type hint)
from llm.ollama_client import OllamaClient  # noqa: E402 (type hint)
from llm.prompts import PromptBuilder, ROLE_OUTPUT  # noqa: E402

LLMClient = object  # duck-typed; HFClient veya OllamaClient

STATE_PATH = REPO_ROOT / "docs" / "ai" / "pipeline" / "state.json"
ITEMS_DIR = REPO_ROOT / "docs" / "ai" / "pipeline" / "items"
LOGS_DIR = REPO_ROOT / "docs" / "ai" / "pipeline" / "logs"
STAGE_SH = REPO_ROOT / "scripts" / "pipeline" / "stage.sh"

logger = logging.getLogger(__name__)


# Decision roller — JSON output zorunlu, state.sh complete --approve/--reject yapılır
DECISION_ROLES = {
    "validator",
    "approver",
    "product_validator",
    "code_reviewer",
    "security_reviewer",
    "a11y_auditor",
    "performance_tester",
    "observer",
}


@dataclass
class AgentResult:
    """Agent çalışma sonucu."""

    item_id: str
    role: str
    ok: bool
    artifact_path: Optional[str] = None
    artifact_bytes: int = 0
    decision: Optional[str] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None
    model: Optional[str] = None
    latency_s: Optional[float] = None
    tokens_used: Optional[int] = None
    error: Optional[str] = None
    log_path: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# CORE
# ═══════════════════════════════════════════════════════════════════════════════


async def run_agent(
    item_id: str,
    role: str,
    client=None,
    dry_run: bool = False,
    auto_complete: bool = True,
    max_tokens: int = 3000,
    temperature: float = 0.3,
) -> AgentResult:
    """Rolü çalıştır, artifact yaz, stage.sh complete çağır."""
    result = AgentResult(item_id=item_id, role=role, ok=False)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"{item_id}-{role}-{int(time.time())}.log"
    result.log_path = str(log_path.relative_to(REPO_ROOT))

    # Logger setup (file + stderr)
    file_h = logging.FileHandler(log_path)
    file_h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(file_h)

    try:
        provider = get_provider()
        logger.info("=== Starting agent role=%s item=%s provider=%s ===", role, item_id, provider)

        client = client or get_client()

        # 1. Build prompt
        builder = PromptBuilder(role=role, item_id=item_id)
        messages = builder.build()
        logger.info("Prompt built: %d system chars, %d user chars",
                    len(messages[0]["content"]), len(messages[1]["content"]))

        if dry_run:
            print("=== DRY RUN — would send prompt ===")
            print(f"\n--- system ({len(messages[0]['content'])} chars) ---\n")
            print(messages[0]["content"][:2000])
            print(f"\n--- user ({len(messages[1]['content'])} chars) ---\n")
            print(messages[1]["content"][:3000])
            result.ok = True
            return result

        # 2. Call LLM
        logger.info("Calling HF LLM...")
        start = time.time()
        hf_resp = await client.achat(
            messages=messages,
            role=role,
            max_tokens=max_tokens,
            temperature=temperature,
            parse_json=(role in DECISION_ROLES),
        )
        result.latency_s = hf_resp.latency_s
        result.tokens_used = hf_resp.tokens_used
        result.model = hf_resp.model
        logger.info("LLM done: %s, %.2fs, %s tokens",
                    hf_resp.model, hf_resp.latency_s or 0, hf_resp.tokens_used)

        # 3. Write artifact
        content = hf_resp.content.strip()
        if not content:
            raise RuntimeError("Empty LLM response")

        # Strip potential code fences that wrap whole output
        content = _strip_wrapping_fence(content)

        artifact_path: Optional[Path] = None
        out_file = builder.output_file()
        if out_file:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(content + "\n", encoding="utf-8")
            artifact_path = out_file
            result.artifact_path = str(out_file.relative_to(REPO_ROOT))
            result.artifact_bytes = len(content)
            logger.info("Artifact written: %s (%d bytes)", result.artifact_path, len(content))

        # 4. Extract decision (for decision roles)
        if role in DECISION_ROLES:
            decision_data = hf_resp.parsed_json or {}
            result.decision = decision_data.get("decision")
            confidence_raw = decision_data.get("confidence")
            try:
                result.confidence = float(confidence_raw) if confidence_raw is not None else None
            except (TypeError, ValueError):
                result.confidence = None
            result.reason = decision_data.get("reason")
            logger.info("Decision: %s (confidence=%s)", result.decision, result.confidence)

        # 5. Call stage.sh complete
        if auto_complete:
            _invoke_stage_complete(item_id, role, result, artifact_path)

        result.ok = True
        return result

    except Exception as e:
        logger.exception("Agent failed: %s", e)
        result.error = str(e)
        return result
    finally:
        logging.getLogger().removeHandler(file_h)


def _strip_wrapping_fence(text: str) -> str:
    """LLM bazen tüm yanıtı ```markdown ... ``` ile sarar, temizle."""
    lines = text.splitlines()
    if len(lines) >= 2 and lines[0].strip().startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1])
    return text


def _invoke_stage_complete(
    item_id: str,
    role: str,
    result: AgentResult,
    artifact_path: Optional[Path],
) -> None:
    """stage.sh complete çalıştır."""
    if not STAGE_SH.exists():
        logger.warning("stage.sh not found — skipping state update")
        return

    cmd = [str(STAGE_SH), "complete", item_id, role]

    if artifact_path:
        cmd += ["--artifact", str(artifact_path.relative_to(REPO_ROOT))]

    if result.latency_s:
        notes = f"agent=hf model={result.model} latency={result.latency_s:.1f}s"
        cmd += ["--notes", notes]

    # Decision args
    if role in DECISION_ROLES:
        if result.decision == "approve":
            cmd.append("--approve")
        elif result.decision == "reject":
            cmd.append("--reject")
        elif result.decision == "revise":
            cmd.append("--revise")
        if result.confidence is not None:
            cmd += ["--confidence", f"{result.confidence:.2f}"]
        if result.reason:
            # Trim reason
            cmd += ["--reason", result.reason[:200]]

    logger.info("Invoking: %s", " ".join(cmd[:5]) + " ...")
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if p.returncode != 0:
            logger.error("stage.sh failed: %s", p.stderr[:500])
        else:
            logger.info("stage.sh ok: %s", p.stdout[:200])
    except Exception as e:
        logger.error("stage.sh invocation error: %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item", required=True, help="Item ID (e.g. GAP-001)")
    parser.add_argument("--role", required=True, help="Role slug")
    parser.add_argument("--dry-run", action="store_true", help="Only print prompt, don't call LLM")
    parser.add_argument("--no-auto-complete", action="store_true", help="Don't call stage.sh complete")
    parser.add_argument("--max-tokens", type=int, default=3000)
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")

    result = asyncio.run(run_agent(
        item_id=args.item,
        role=args.role,
        dry_run=args.dry_run,
        auto_complete=not args.no_auto_complete,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    ))

    if args.json:
        print(json.dumps(asdict(result), indent=2, default=str))
    else:
        if result.ok:
            print(f"\n✓ {args.role} done for {args.item}")
            if result.artifact_path:
                print(f"  artifact: {result.artifact_path} ({result.artifact_bytes} bytes)")
            if result.decision:
                print(f"  decision: {result.decision} (confidence={result.confidence})")
            if result.model:
                print(f"  model: {result.model}, latency: {result.latency_s:.1f}s")
        else:
            print(f"\n✗ {args.role} FAILED for {args.item}")
            print(f"  error: {result.error}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
