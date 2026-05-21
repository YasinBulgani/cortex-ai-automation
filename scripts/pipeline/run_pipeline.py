#!/usr/bin/env python3
"""
run_pipeline.py — Paralel pipeline executor.

Tüm waiting stage'leri HuggingFace LLM ile eş zamanlı koşturur.
Dep graph sayesinde yeni aşamalar açılınca onları da yakalayıp çalıştırır.

Modes:
    - once: bir tur koş (tüm waiting'ler bitene kadar), sonra çık
    - watch: state.json'u izle, her yeni waiting için agent başlat (daemon)
    - single: tek bir item için full pipeline (analyzer → retrospective)

Concurrency limit: aynı anda en fazla N agent (HF rate-limit için).
Default: 4.

CLI:
    python3 run_pipeline.py once
    python3 run_pipeline.py watch --max-concurrent 3
    python3 run_pipeline.py single --item GAP-001
    python3 run_pipeline.py once --filter-role analyzer,validator
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "pipeline"))

from llm import get_client, get_provider  # noqa: E402
from agent_runner import run_agent, AgentResult  # noqa: E402

STATE_PATH = REPO_ROOT / "docs" / "ai" / "pipeline" / "state.json"
EVENTS_DIR = REPO_ROOT / "docs" / "ai" / "pipeline" / "events"
RUN_LOG = REPO_ROOT / "docs" / "ai" / "pipeline" / "run.log"

logger = logging.getLogger(__name__)


@dataclass
class PipelineRun:
    """Bir koşunun özeti."""

    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    items_touched: Set[str] = field(default_factory=set)
    agents_ran: int = 0
    agents_succeeded: int = 0
    agents_failed: int = 0
    agents: List[Dict[str, Any]] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        return {
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_s": (self.ended_at or time.time()) - self.started_at,
            "items_touched": list(self.items_touched),
            "agents_ran": self.agents_ran,
            "agents_succeeded": self.agents_succeeded,
            "agents_failed": self.agents_failed,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# STATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"items": []}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def find_waiting_stages(
    state: dict,
    role_filter: Optional[Set[str]] = None,
    item_filter: Optional[Set[str]] = None,
    skip_in_progress: bool = True,
) -> List[Tuple[str, str]]:
    """(item_id, role) listesi — waiting aşamalar."""
    out: List[Tuple[str, str]] = []
    for item in state.get("items", []):
        iid = item.get("id")
        if item_filter and iid not in item_filter:
            continue
        if item.get("needs_human"):
            continue
        stages = item.get("stages", {}) or {}
        for role, sdata in stages.items():
            if role_filter and role not in role_filter:
                continue
            status = (sdata or {}).get("status")
            if status == "waiting":
                out.append((iid, role))
            elif status == "in_progress" and not skip_in_progress:
                out.append((iid, role))
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# EVENT EMITTER (for dashboard)
# ═══════════════════════════════════════════════════════════════════════════════


def emit_event(event_type: str, payload: Dict[str, Any]) -> None:
    """Dashboard'un watch edebilmesi için event dosyası yaz."""
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    event = {"ts": ts, "type": event_type, **payload}
    event_file = EVENTS_DIR / f"{ts}-{event_type}.json"
    event_file.write_text(json.dumps(event, default=str), encoding="utf-8")
    # Also append to run.log for tail-following
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with RUN_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, default=str) + "\n")
    # Prune old events (keep last 200)
    all_events = sorted(EVENTS_DIR.glob("*.json"))
    if len(all_events) > 200:
        for old in all_events[:-200]:
            try:
                old.unlink()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
# CORE
# ═══════════════════════════════════════════════════════════════════════════════


async def run_one_agent(
    item_id: str,
    role: str,
    client,
    semaphore: asyncio.Semaphore,
    run: PipelineRun,
    max_tokens: int = 3000,
    temperature: float = 0.3,
) -> AgentResult:
    """Semaphore ile gated agent run."""
    async with semaphore:
        emit_event("agent_started", {"item_id": item_id, "role": role})
        try:
            result = await run_agent(
                item_id=item_id,
                role=role,
                client=client,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            run.agents_ran += 1
            run.items_touched.add(item_id)
            if result.ok:
                run.agents_succeeded += 1
                emit_event("agent_succeeded", {
                    "item_id": item_id, "role": role,
                    "model": result.model, "latency_s": result.latency_s,
                    "decision": result.decision, "confidence": result.confidence,
                })
            else:
                run.agents_failed += 1
                emit_event("agent_failed", {
                    "item_id": item_id, "role": role, "error": result.error,
                })
            run.agents.append(asdict(result))
            return result
        except Exception as e:
            run.agents_failed += 1
            emit_event("agent_failed", {"item_id": item_id, "role": role, "error": str(e)})
            logger.exception("Agent run exception")
            result = AgentResult(item_id=item_id, role=role, ok=False, error=str(e))
            run.agents.append(asdict(result))
            return result


async def run_once(
    max_concurrent: int = 4,
    role_filter: Optional[Set[str]] = None,
    item_filter: Optional[Set[str]] = None,
    max_rounds: int = 10,
    max_tokens: int = 3000,
    temperature: float = 0.3,
) -> PipelineRun:
    """Bir tur koş: tüm waiting'leri işle, yeni açılanları da yakala."""
    run = PipelineRun()
    client = get_client()
    semaphore = asyncio.Semaphore(max_concurrent)

    emit_event("run_started", {"mode": "once", "max_concurrent": max_concurrent})

    round_num = 0
    while round_num < max_rounds:
        round_num += 1
        state = load_state()
        waiting = find_waiting_stages(state, role_filter=role_filter, item_filter=item_filter)
        if not waiting:
            logger.info("No waiting stages; pipeline idle.")
            break
        emit_event("round_started", {"round": round_num, "waiting_count": len(waiting)})
        logger.info("Round %d: %d waiting stage(s)", round_num, len(waiting))

        tasks = [
            run_one_agent(iid, role, client, semaphore, run,
                          max_tokens=max_tokens, temperature=temperature)
            for iid, role in waiting
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
        emit_event("round_completed", {"round": round_num})

    run.ended_at = time.time()
    emit_event("run_completed", run.summary())
    return run


async def run_watch(
    max_concurrent: int = 3,
    poll_interval_s: float = 5.0,
    role_filter: Optional[Set[str]] = None,
    idle_exit_after_s: Optional[float] = None,
    max_tokens: int = 3000,
    temperature: float = 0.3,
) -> PipelineRun:
    """state.json'u poll et, her waiting için agent spawn. Duracak kadar dur."""
    run = PipelineRun()
    client = get_client()
    semaphore = asyncio.Semaphore(max_concurrent)
    seen: Set[Tuple[str, str]] = set()
    idle_since: Optional[float] = None

    emit_event("run_started", {"mode": "watch", "max_concurrent": max_concurrent})
    logger.info("Watch mode: polling every %.1fs", poll_interval_s)

    stop = False

    def _handle_signal(signum, frame):
        nonlocal stop
        stop = True
        logger.info("Signal received, stopping watch...")

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    active_tasks: List[asyncio.Task] = []
    while not stop:
        state = load_state()
        waiting = find_waiting_stages(state, role_filter=role_filter)
        new_items = [(iid, role) for iid, role in waiting if (iid, role) not in seen]
        for pair in new_items:
            seen.add(pair)

        if new_items:
            idle_since = None
            for iid, role in new_items:
                t = asyncio.create_task(run_one_agent(
                    iid, role, client, semaphore, run,
                    max_tokens=max_tokens, temperature=temperature,
                ))
                active_tasks.append(t)

        # Purge completed tasks + evict finished pairs from seen if their stage no longer waiting
        active_tasks = [t for t in active_tasks if not t.done()]

        # Forget stages that are now done/rejected/skipped so they can re-enter on loop-back
        state2 = load_state()
        to_forget: Set[Tuple[str, str]] = set()
        for item in state2.get("items", []):
            iid = item.get("id")
            for role, sdata in (item.get("stages", {}) or {}).items():
                if (iid, role) in seen and sdata.get("status") in {"done", "rejected", "skipped"}:
                    to_forget.add((iid, role))
        seen -= to_forget

        if not waiting and not active_tasks:
            if idle_since is None:
                idle_since = time.time()
            if idle_exit_after_s and (time.time() - idle_since) > idle_exit_after_s:
                logger.info("Idle for >%.0fs; exiting watch.", idle_exit_after_s)
                break

        await asyncio.sleep(poll_interval_s)

    # Wait remaining
    if active_tasks:
        await asyncio.gather(*active_tasks, return_exceptions=True)

    run.ended_at = time.time()
    emit_event("run_completed", run.summary())
    return run


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════


def _parse_set(s: Optional[str]) -> Optional[Set[str]]:
    if not s:
        return None
    return {x.strip() for x in s.split(",") if x.strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)

    p_once = sub.add_parser("once", help="Bir tur koş")
    p_once.add_argument("--max-concurrent", type=int, default=4)
    p_once.add_argument("--filter-role", help="comma-sep role slugs")
    p_once.add_argument("--filter-item", help="comma-sep item IDs")
    p_once.add_argument("--max-rounds", type=int, default=10)
    p_once.add_argument("--max-tokens", type=int, default=3000)
    p_once.add_argument("--temperature", type=float, default=0.3)
    p_once.add_argument("--json", action="store_true")

    p_watch = sub.add_parser("watch", help="Daemon mode (izle + spawn)")
    p_watch.add_argument("--max-concurrent", type=int, default=3)
    p_watch.add_argument("--poll-interval", type=float, default=5.0)
    p_watch.add_argument("--filter-role", help="comma-sep role slugs")
    p_watch.add_argument("--idle-exit-after", type=float, help="Idle süre (saniye) — sonra çık")
    p_watch.add_argument("--max-tokens", type=int, default=3000)
    p_watch.add_argument("--temperature", type=float, default=0.3)

    p_single = sub.add_parser("single", help="Tek item'ı full pipeline koş")
    p_single.add_argument("--item", required=True)
    p_single.add_argument("--max-concurrent", type=int, default=3)

    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")

    if args.mode == "once":
        run = asyncio.run(run_once(
            max_concurrent=args.max_concurrent,
            role_filter=_parse_set(args.filter_role),
            item_filter=_parse_set(args.filter_item),
            max_rounds=args.max_rounds,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        ))
        if args.json:
            print(json.dumps(run.summary(), indent=2, default=str))
        else:
            s = run.summary()
            print(f"\n{'='*60}")
            print(f"Pipeline run done in {s['duration_s']:.1f}s")
            print(f"  Agents ran: {s['agents_ran']} (ok={s['agents_succeeded']}, fail={s['agents_failed']})")
            print(f"  Items touched: {len(s['items_touched'])}")
        return 0 if run.agents_failed == 0 else 1

    if args.mode == "watch":
        run = asyncio.run(run_watch(
            max_concurrent=args.max_concurrent,
            poll_interval_s=args.poll_interval,
            role_filter=_parse_set(args.filter_role),
            idle_exit_after_s=args.idle_exit_after,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        ))
        s = run.summary()
        print(f"\nWatch ended. Agents ran: {s['agents_ran']}, succeeded: {s['agents_succeeded']}")
        return 0

    if args.mode == "single":
        # Only this item, run once repeatedly until done
        item = args.item
        run = asyncio.run(run_once(
            max_concurrent=args.max_concurrent,
            item_filter={item},
            max_rounds=30,
        ))
        s = run.summary()
        print(f"\nSingle pipeline for {item}: {s['agents_ran']} agents in {s['duration_s']:.1f}s")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
