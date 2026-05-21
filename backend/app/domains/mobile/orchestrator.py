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

Varsayılan mod geriye uyumluluk için simülasyondur. Gerçek koşum için
SessionCreate.mode="appium" kullanılır; bu mod AppiumRunner ile gerçek
WebDriver komutları çalıştırır ve hata saklamaz.
"""
from __future__ import annotations

import asyncio
import logging
import random
import threading
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from .appium_runner import AppiumRunner
from .device_broker import get_broker
from .llm_stepper import generate_steps
from .schemas import (
    AppiumAction,
    RunMode,
    Session,
    SessionCreate,
    SessionEvent,
    Step,
    VisualVerifyRequest,
)
from .self_healing import HealRequest, suggest as heal_suggest
from .visual_verifier import verify as visual_verify

_logger = logging.getLogger(__name__)


class SessionStore:
    """Thread-safe in-memory session store + SSE queue."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, Session] = {}
        self._queues: dict[str, asyncio.Queue | None] = {}
        self._events: dict[str, list[SessionEvent]] = {}
        self._event_ids: dict[str, int] = {}

    def create(
        self,
        device_id: str,
        scenario_name: str,
        steps: list[AppiumAction],
        *,
        mode: RunMode = "simulation",
    ) -> Session:
        sid = f"s_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        sess = Session(
            id=sid,
            device_id=device_id,
            scenario_name=scenario_name,
            status="running",
            started_at=now,
            mode=mode,
            steps=[
                Step(seq=i, action=s.action, locator=s.model_dump(exclude_none=True))
                for i, s in enumerate(steps)
            ],
        )
        with self._lock:
            self._sessions[sid] = sess
            try:
                asyncio.get_running_loop()
                self._queues[sid] = asyncio.Queue(maxsize=500)
            except RuntimeError:
                self._queues[sid] = None
            self._events[sid] = []
            self._event_ids[sid] = 0
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
        with self._lock:
            next_id = self._event_ids.get(sid, 0) + 1
            self._event_ids[sid] = next_id
            event = event.model_copy(update={"id": next_id})
            self._events.setdefault(sid, []).append(event)
        if q is not None:
            try:
                await q.put(event)
            except asyncio.QueueFull:
                _logger.warning("SSE queue dolu, event atlandı: %s", sid)

    def events_since(self, sid: str, last_event_id: int = 0) -> list[SessionEvent]:
        with self._lock:
            return [e for e in self._events.get(sid, []) if e.id > last_event_id]


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


async def _run_appium_session(
    session_id: str,
    device_id: str,
    steps: list[AppiumAction],
    app: Optional[dict] = None,
) -> None:
    broker = get_broker()
    store = get_store()
    dev = broker.get(device_id)
    if not dev:
        store.update(
            session_id,
            status="failed",
            finished_at=datetime.now(timezone.utc),
            failure_category="device",
            failure_message=f"Cihaz bulunamadı: {device_id}",
        )
        return

    broker.update_status(
        device_id,
        "running",
        steps_done=0,
        steps_total=len(steps),
        current_step=steps[0].action if steps else None,
    )

    loop = asyncio.get_running_loop()

    def _publish_from_runner(event_name: str, payload: dict) -> None:
        if event_name.startswith("step."):
            event_type = "step"
        elif event_name.startswith("artifact."):
            event_type = "artifact"
        elif event_name == "log":
            event_type = "log"
        else:
            event_type = "status"

        event = SessionEvent(
            type=event_type,  # type: ignore[arg-type]
            session_id=session_id,
            device_id=device_id,
            payload={"event": event_name, **payload},
        )
        loop.call_soon_threadsafe(lambda: asyncio.create_task(store.publish(session_id, event)))

    try:
        await store.publish(session_id, SessionEvent(
            type="status",
            session_id=session_id,
            device_id=device_id,
            payload={"state": "appium_starting"},
        ))
        runner = AppiumRunner()
        result = await asyncio.to_thread(
            runner.run,
            session_id=session_id,
            device=dev,
            steps=steps,
            app=app,
            on_event=_publish_from_runner,
        )

        screenshot_by_step: dict[int, str] = {}
        screenshot_b64_by_step: dict[int, str] = {}
        import base64, pathlib
        for artifact in result.artifacts:
            if artifact.kind == "screenshot" and artifact.step_seq is not None:
                screenshot_by_step[artifact.step_seq] = artifact.path
                try:
                    raw = pathlib.Path(artifact.path).read_bytes()
                    screenshot_b64_by_step[artifact.step_seq] = base64.b64encode(raw).decode()
                except Exception:
                    pass

        for step_result in result.steps:
            step_status = step_result.status
            # verifyVisible adımları için VisualVerifier çağır
            if (
                step_status == "passed"
                and step_result.seq < len(steps)
                and steps[step_result.seq].action == "verifyVisible"
                and step_result.seq in screenshot_b64_by_step
            ):
                try:
                    assertion = steps[step_result.seq].value or "Element görünür"
                    vr = visual_verify(VisualVerifyRequest(
                        screenshot_base64=screenshot_b64_by_step[step_result.seq],
                        assertion=assertion,
                    ))
                    if not vr.passed:
                        step_status = "failed"
                        await store.publish(session_id, SessionEvent(
                            type="log",
                            session_id=session_id,
                            device_id=device_id,
                            payload={"message": f"VisualVerifier fail (conf={vr.confidence:.2f}): {vr.reason}"},
                        ))
                except Exception as ve:
                    _logger.warning("VisualVerifier hatası: %s", ve)

            store.update_step(
                session_id,
                step_result.seq,
                status=step_status,
                duration_ms=step_result.duration_ms,
                screenshot_url=screenshot_by_step.get(step_result.seq),
                error_message=step_result.error_message,
            )
            broker.update_status(
                device_id,
                "running",
                steps_done=step_result.seq + 1,
                steps_total=len(steps),
                current_step=steps[step_result.seq].action if step_result.seq < len(steps) else None,
            )

        final_status = "passed" if result.status == "passed" else "failed"
        store.update(
            session_id,
            status=final_status,
            finished_at=datetime.now(timezone.utc),
            failure_category=result.failure_category,
            failure_message=result.failure_message,
        )
        await store.publish(session_id, SessionEvent(
            type="done",
            session_id=session_id,
            device_id=device_id,
            payload={
                "status": final_status,
                "failure_category": result.failure_category,
                "failure_message": result.failure_message,
                "artifact_count": len(result.artifacts),
            },
        ))
    except Exception as exc:
        _logger.exception("Appium mobile session hatası: %s", session_id)
        store.update(
            session_id,
            status="failed",
            finished_at=datetime.now(timezone.utc),
            failure_category="infrastructure",
            failure_message=str(exc),
        )
        await store.publish(session_id, SessionEvent(
            type="done",
            session_id=session_id,
            device_id=device_id,
            payload={
                "status": "failed",
                "failure_category": "infrastructure",
                "failure_message": str(exc),
            },
        ))
    finally:
        broker.update_status(device_id, "idle", steps_done=0, steps_total=0, current_step=None)


async def start_suite(req: SessionCreate) -> list[Session]:
    """N cihazda paralel senaryo başlat.

    Döner: oluşturulan session listesi. Çalışmalar background task'lerde
    devam eder; client SSE stream ile izler.
    """
    steps = req.steps
    if steps is None:
        gen = generate_steps(prompt=req.prompt, platform=("android" if req.platform != "ios" else "ios"))
        steps = gen.steps
    broker = get_broker()
    if req.device_ids:
        requested = [broker.get(device_id) for device_id in req.device_ids]
        devices = [
            dev
            for dev in requested
            if dev is not None
            and dev.status == "idle"
            and (req.platform == "both" or dev.platform == req.platform)
        ]
    else:
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
            steps=steps,
            mode=req.mode,
        )
        created.append(sess)
        if req.mode == "appium":
            asyncio.create_task(
                _run_appium_session(
                    session_id=sess.id,
                    device_id=dev.id,
                    steps=steps,
                    app=req.app,
                )
            )
        else:
            # Arka plan task'i başlat
            asyncio.create_task(
                _run_single_session(
                    session_id=sess.id,
                    device_id=dev.id,
                    steps=steps,
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
