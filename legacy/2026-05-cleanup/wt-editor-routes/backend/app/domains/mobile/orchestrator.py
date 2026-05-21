"""Session Orchestrator — paralel mobil session koşusu.

MVP: In-memory, tek süreç. F4'te Redis Streams + Celery worker'a taşınır.

Akış:
  1. LLM Stepper adımları üretir.
  2. Device Broker N cihaz seçer.
  3. Her cihazda ayrı asyncio task'i ile adımlar yürütülür.
  4. Her adımdan sonra SSE event yayımlanır.
  5. Fail olursa SelfHealing devreye girer.
  6. verifyVisible varsa VisualVerifier çağrılır.
  7. Bitişte result + artifact URL kaydedilir.

MVP simülasyon: Gerçek Appium bağlantısı yok — pass_rate / heal_rate
parametrelerine göre olasılıklı simülasyon.
"""
from __future__ import annotations

import asyncio
import logging
import random
import threading
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from .device_broker import get_broker
from .llm_stepper import generate_steps
from .schemas import (
    AppiumAction,
    Session,
    SessionCreate,
    SessionEvent,
    Step,
)
from .self_healing import HealRequest, suggest as heal_suggest

_logger = logging.getLogger(__name__)


class SessionStore:
    """Thread-safe in-memory session store + SSE queue."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, Session] = {}
        self._queues: dict[str, asyncio.Queue] = {}

    def create(self, device_id: str, scenario_name: str, steps: list[AppiumAction]) -> Session:
        sid = f"s_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        sess = Session(
            id=sid,
            device_id=device_id,
            scenario_name=scenario_name,
            status="running",
            started_at=now,
            steps=[
                Step(seq=i, action=s.action, locator=s.model_dump(exclude_none=True))
                for i, s in enumerate(steps)
            ],
        )
        with self._lock:
            self._sessions[sid] = sess
            self._queues[sid] = asyncio.Queue(maxsize=500)
        return sess

    def get(self, sid: str) -> Optional[Session]:
        with self._lock:
            return self._sessions.get(sid)

    def list_recent(self, limit: int = 40) -> list[Session]:
        with self._lock:
            items = sorted(
                self._sessions.values(),
                key=lambda s: s.started_at,
                reverse=True,
            )
            return items[:limit]

    def update(self, sid: str, **fields) -> Optional[Session]:
        with self._lock:
            s = self._sessions.get(sid)
            if not s:
                return None
            updated = s.model_copy(update=fields)
            self._sessions[sid] = updated
            return updated

    def update_step(self, sid: str, seq: int, **fields) -> None:
        with self._lock:
            s = self._sessions.get(sid)
            if not s:
                return
            new_steps = []
            for step in s.steps:
                if step.seq == seq:
                    new_steps.append(step.model_copy(update=fields))
                else:
                    new_steps.append(step)
            self._sessions[sid] = s.model_copy(update={"steps": new_steps})

    def queue(self, sid: str) -> Optional[asyncio.Queue]:
        with self._lock:
            return self._queues.get(sid)

    async def publish(self, sid: str, event: SessionEvent) -> None:
        q = self.queue(sid)
        if q is not None:
            try:
                await q.put(event)
            except asyncio.QueueFull:
                _logger.warning("SSE queue dolu, event atlandı: %s", sid)


_store: Optional[SessionStore] = None
_store_lock = threading.Lock()


def get_store() -> SessionStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = SessionStore()
    return _store


# ── Session execution ─────────────────────────────────────────
async def _run_single_session(
    session_id: str,
    device_id: str,
    steps: list[AppiumAction],
    pass_rate: int,
    heal_rate: int,
) -> None:
    broker = get_broker()
    store = get_store()
    dev = broker.get(device_id)
    if not dev:
        return

    broker.update_status(
        device_id, "running",
        steps_done=0, steps_total=len(steps),
        current_step=steps[0].action if steps else None,
    )
    healed_count = 0
    failed_at: Optional[int] = None

    for i, step in enumerate(steps):
        # Random per-step delay: 300–1000ms
        await asyncio.sleep(random.uniform(0.3, 1.0))

        # Self-heal olayı — olasılıklı
        if step.action == "find" and random.random() * 100 < heal_rate / max(1, len(steps)):
            heal_req = HealRequest(failed_action=step.model_dump(exclude_none=True), retry_count=0)
            decision = heal_suggest(heal_req)
            healed_count += 1
            store.update_step(
                session_id, i,
                status="healed",
                llm_reason=f"{decision.decision}: {decision.reason}",
            )
            await store.publish(session_id, SessionEvent(
                type="heal",
                session_id=session_id,
                device_id=device_id,
                payload={"seq": i, "decision": decision.decision, "reason": decision.reason},
            ))
            await asyncio.sleep(0.4)
        else:
            store.update_step(session_id, i, status="running")

        # Adım tamamlandı
        store.update_step(session_id, i, status="passed", duration_ms=int(random.uniform(300, 1000)))
        broker.update_status(
            device_id, "running",
            steps_done=i + 1, steps_total=len(steps),
            current_step=step.action, heal_streak=healed_count,
        )
        await store.publish(session_id, SessionEvent(
            type="step",
            session_id=session_id,
            device_id=device_id,
            payload={"seq": i, "action": step.action, "done": i + 1, "total": len(steps)},
        ))

    # Bitiş kararı — pass_rate kumarı
    passed = random.random() * 100 < pass_rate
    if not passed and steps:
        failed_at = random.randint(max(0, len(steps) - 3), len(steps) - 1)
        store.update_step(session_id, failed_at, status="failed")

    store.update(
        session_id,
        status="passed" if passed else "failed",
        finished_at=datetime.now(timezone.utc),
        healed=healed_count,
    )
    broker.update_status(
        device_id, "idle",
        steps_done=0, steps_total=0, current_step=None,
    )
    await store.publish(session_id, SessionEvent(
        type="done",
        session_id=session_id,
        device_id=device_id,
        payload={
            "status": "passed" if passed else "failed",
            "healed": healed_count,
            "failed_at": failed_at,
        },
    ))


async def start_suite(req: SessionCreate) -> list[Session]:
    """N cihazda paralel senaryo başlat.

    Döner: oluşturulan session listesi. Çalışmalar background task'lerde
    devam eder; client SSE stream ile izler.
    """
    gen = generate_steps(prompt=req.prompt, platform=("android" if req.platform != "ios" else "ios"))
    broker = get_broker()
    plat = req.platform if req.platform != "both" else "both"
    devices = broker.pick_available(platform=plat, count=req.parallel)

    if not devices:
        return []

    store = get_store()
    created: list[Session] = []
    for dev in devices:
        sess = store.create(
            device_id=dev.id,
            scenario_name=req.scenario_name,
            steps=gen.steps,
        )
        created.append(sess)
        # Arka plan task'i başlat
        asyncio.create_task(
            _run_single_session(
                session_id=sess.id,
                device_id=dev.id,
                steps=gen.steps,
                pass_rate=req.pass_rate,
                heal_rate=req.heal_rate,
            )
        )
    return created


async def stream_events(session_id: str) -> AsyncIterator[SessionEvent]:
    """SSE event üreteci — session bitene kadar yayımlar."""
    store = get_store()
    q = store.queue(session_id)
    if q is None:
        return
    while True:
        try:
            event = await asyncio.wait_for(q.get(), timeout=60.0)
        except asyncio.TimeoutError:
            # Session bitti mi kontrol et
            s = store.get(session_id)
            if s and s.status in ("passed", "failed", "cancelled"):
                return
            continue
        yield event
        if event.type == "done":
            return
