"""Event Streaming Infrastructure — Kafka/Redis foundation (Faz 3.5).

Kafka Topic per domain (auth.events, test_management.events, etc.)
Avro/Protobuf schema registry with versioning
Consumer groups with exactly-once semantics
Outbox → Kafka migration bridge
Downstream subscriptions (analytics, webhooks, audit logs)
Backpressure & lag monitoring
"""

from .broker import EventBroker, KafkaBroker, RedisBroker
from .consumer import ConsumerGroup, ExactlyOnceConsumer
from .schemas import EventSchema, SchemaRegistry
from .models import StreamEvent, ConsumerGroupMetrics

__all__ = [
    "EventBroker",
    "KafkaBroker",
    "RedisBroker",
    "ConsumerGroup",
    "ExactlyOnceConsumer",
    "EventSchema",
    "SchemaRegistry",
    "StreamEvent",
    "ConsumerGroupMetrics",
]
