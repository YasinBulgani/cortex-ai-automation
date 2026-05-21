"""
Outbox Pattern — guaranteed event delivery.

Sorun: Aggregate save edip event publish ettiğin sırada crash olursa,
       event publish olmayabilir → integrity bozulur.

Çözüm: Event'leri DB'de "outbox" tablosuna yaz (aynı transaction'da),
       sonra background worker bunları broker'a (Redis Streams) iter.
       Idempotent processor + dead letter queue garantili delivery sağlar.
"""

from .outbox import InMemoryOutboxRepository, OutboxEntry, OutboxRepository, OutboxRelay

__all__ = ["InMemoryOutboxRepository", "OutboxEntry", "OutboxRepository", "OutboxRelay"]
