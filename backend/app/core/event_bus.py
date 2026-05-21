"""Domain Event Bus — modüller arası publish/subscribe omurgası.

Kullanım:
  from app.core.event_bus import bus, DomainEvent

  bus.subscribe("scenario.created", on_scenario_created)
  bus.publish(DomainEvent(name="scenario.created", payload={"id": "..."}))

Production'da Redis Streams veya RabbitMQ üzerinde aynı interface.
Şu an in-memory + son N event persisted (debug/replay için).
"""
from __future__ import annotations

import logging
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DomainEvent:
    name: str  # ör: "scenario.created", "execution.failed"
    payload: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: "evt-" + uuid.uuid4().hex[:12])
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    project_id: Optional[str] = None
    actor_id: Optional[str] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "ts": self.ts,
            "project_id": self.project_id,
            "actor_id": self.actor_id,
            "correlation_id": self.correlation_id,
            "payload": dict(self.payload),
        }


Handler = Callable[[DomainEvent], None]


class EventBus:
    """Thread-safe in-memory event bus with wildcard + history.

    Wildcards: "scenario.*" tüm scenario.X event'lerine bağlanır.
    """

    def __init__(self, history_size: int = 500):
        self._exact: Dict[str, List[Handler]] = {}
        self._wildcard: List[tuple[str, Handler]] = []  # prefix without dot
        self._history: deque[DomainEvent] = deque(maxlen=history_size)
        self._lock = threading.RLock()

    def subscribe(self, pattern: str, handler: Handler) -> Callable[[], None]:
        """Pattern'e handler bağlar. Çıkartmak için döndürülen unsubscribe çağrılır."""
        with self._lock:
            if pattern.endswith(".*"):
                prefix = pattern[:-2]
                self._wildcard.append((prefix, handler))
            else:
                self._exact.setdefault(pattern, []).append(handler)

        def unsubscribe() -> None:
            with self._lock:
                if pattern.endswith(".*"):
                    prefix = pattern[:-2]
                    self._wildcard[:] = [
                        (p, h) for (p, h) in self._wildcard if not (p == prefix and h is handler)
                    ]
                else:
                    if pattern in self._exact:
                        self._exact[pattern] = [h for h in self._exact[pattern] if h is not handler]

        return unsubscribe

    def publish(self, event: DomainEvent) -> int:
        """Event'i tüm uygun handler'lara yayınlar. Çağrılan handler sayısını döner.

        Handler hatası diğerlerini engellemez — log'lanır.
        """
        with self._lock:
            self._history.append(event)
            handlers = list(self._exact.get(event.name, []))
            for prefix, h in self._wildcard:
                if event.name == prefix or event.name.startswith(prefix + "."):
                    handlers.append(h)

        called = 0
        for h in handlers:
            try:
                h(event)
                called += 1
            except Exception:
                logger.exception("EventBus handler hatası (event=%s)", event.name)
        return called

    def history(self, *, name: Optional[str] = None, project_id: Optional[str] = None, limit: int = 100) -> List[DomainEvent]:
        with self._lock:
            items = list(self._history)
        if name:
            items = [e for e in items if e.name == name or (name.endswith(".*") and e.name.startswith(name[:-2] + "."))]
        if project_id:
            items = [e for e in items if e.project_id == project_id]
        return items[-limit:]

    def clear(self) -> None:
        """Test helper."""
        with self._lock:
            self._exact.clear()
            self._wildcard.clear()
            self._history.clear()

    def stats(self) -> dict:
        with self._lock:
            return {
                "exact_subscriptions": sum(len(v) for v in self._exact.values()),
                "wildcard_subscriptions": len(self._wildcard),
                "history_size": len(self._history),
            }


# Singleton
bus = EventBus()


# Sık kullanılan event isimleri — typo'yu önlemek için sabit.
class EventName:
    SCENARIO_CREATED = "scenario.created"
    SCENARIO_UPDATED = "scenario.updated"
    SCENARIO_DELETED = "scenario.deleted"
    EXECUTION_STARTED = "execution.started"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_FAILED = "execution.failed"
    LOCATOR_HEALED = "locator.healed"
    FLAKY_DETECTED = "flaky.detected"
    REQUIREMENT_INGESTED = "requirement.ingested"
    PIPELINE_STAGE_COMPLETED = "pipeline.stage.completed"
    DEFECT_OPENED = "defect.opened"
    DEFECT_VERIFIED = "defect.verified"
