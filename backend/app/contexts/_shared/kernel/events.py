"""
Domain Event base.

Her cross-context iletişim event'lerle olur. Direct cross-context call yok.
Events outbox pattern ile reliable delivery alır.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """
    Tüm domain event'lerinin base'i.

    Field'lar:
      - event_id: Unique event ID (idempotency için)
      - aggregate_id: Olayı tetikleyen aggregate
      - occurred_at: Olay zamanı (UTC)
      - event_version: Şema versiyonu (migration için)
      - metadata: actor, request_id, vs.

    Subclass'lar event-specific data ekler:
        @dataclass(frozen=True, slots=True)
        class UserRegistered(DomainEvent):
            email: str
            display_name: str
    """

    event_id: UUID = field(default_factory=uuid4)
    aggregate_id: UUID = field(default=None)  # type: ignore[assignment]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_version: int = 1
    metadata: dict = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        """`UserRegistered` → `"user.registered"` gibi snake_case kebab dotted."""
        cls_name = type(self).__name__
        # CamelCase → snake_case with dot at module boundary
        # Pragmatik: sadece lowercase'e çevir
        result = []
        for i, ch in enumerate(cls_name):
            if i > 0 and ch.isupper():
                result.append("_")
            result.append(ch.lower())
        return "".join(result).replace("_", ".", 1)  # ilk _ dot olur
