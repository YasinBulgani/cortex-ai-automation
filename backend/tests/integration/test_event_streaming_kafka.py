"""Integration tests for Kafka event streaming (Faz 3.5).

Requires Kafka running locally (docker compose -f infra/kafka-docker-compose.yml up -d).
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone

from app.infra.event_streaming.broker import KafkaBroker
from app.infra.event_streaming.consumer import ExactlyOnceConsumer, ConsumerMessage
from app.infra.event_streaming.schemas import EventSchema, SchemaRegistry, get_schema_registry


@pytest.mark.integration
@pytest.mark.asyncio
class TestKafkaBroker:
    """Test Kafka producer functionality."""

    @pytest.fixture
    async def broker(self):
        """Create Kafka broker."""
        broker = KafkaBroker(bootstrap_servers="localhost:9092")
        yield broker
        await broker.close()

    async def test_publish_single_message(self, broker):
        """Test publishing single event."""
        topic = "test.events"
        event = {
            "event_id": "evt-123",
            "action": "created",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        msg_id = await broker.publish(topic, event)
        assert msg_id is not None
        assert "test.events" in msg_id

    async def test_publish_with_partition_key(self, broker):
        """Test publishing with partition key (ordering)."""
        topic = "auth.events"
        user_id = "user-456"

        for i in range(5):
            event = {
                "event_id": f"evt-{i}",
                "user_id": user_id,
                "action": f"action_{i}",
            }
            msg_id = await broker.publish(topic, event, partition_key=user_id)
            assert msg_id is not None

    async def test_publish_multiple_messages_idempotent(self, broker):
        """Test idempotent producer (exactly-once)."""
        topic = "test.idempotent"
        event_id = "evt-unique-123"

        event = {
            "event_id": event_id,
            "action": "test",
        }

        # Publish twice with same ID
        msg_id_1 = await broker.publish(topic, event)
        msg_id_2 = await broker.publish(topic, event)

        # Both should succeed (idempotent = no duplicates)
        assert msg_id_1 is not None
        assert msg_id_2 is not None

    async def test_create_topic(self, broker):
        """Test topic creation with config."""
        topic = "test.created.topic"

        await broker.create_topic(
            topic,
            num_partitions=3,
            replication_factor=2,
            retention_ms=86400000,  # 1 day
        )

        # Topic should exist (no error on second call)
        await broker.create_topic(
            topic,
            num_partitions=3,
            replication_factor=2,
        )


@pytest.mark.integration
@pytest.mark.asyncio
class TestExactlyOnceConsumer:
    """Test Kafka consumer with exactly-once semantics."""

    @pytest.fixture
    async def consumer(self):
        """Create consumer."""
        consumer = ExactlyOnceConsumer(
            group_id="test-consumer-group",
            bootstrap_servers="localhost:9092",
        )
        yield consumer
        await consumer.close()

    @pytest.fixture
    async def broker(self):
        """Create broker for publishing."""
        broker = KafkaBroker(bootstrap_servers="localhost:9092")
        yield broker
        await broker.close()

    async def test_subscribe_and_consume(self, consumer, broker):
        """Test subscribing and consuming messages."""
        topic = "test.consumer.topic"

        # Publish test event
        event = {
            "event_id": "evt-consumer-test",
            "data": "test_data",
        }
        await broker.publish(topic, event)

        # Subscribe
        await consumer.subscribe([topic])

        # Consume (in background)
        received = []

        async def handler(msg: ConsumerMessage):
            received.append(msg)

        # Run consume for short time
        async def consume_loop():
            try:
                await asyncio.wait_for(
                    consumer.consume(handler, timeout_ms=100),
                    timeout=2.0,
                )
            except asyncio.TimeoutError:
                pass  # Expected

        await consume_loop()

        # Verify
        assert len(received) > 0
        assert received[0].value["event_id"] == "evt-consumer-test"

    async def test_consumer_metrics(self, consumer, broker):
        """Test getting consumer metrics."""
        topic = "test.metrics.topic"

        # Publish events
        for i in range(5):
            await broker.publish(topic, {"event_id": f"evt-{i}"})

        # Subscribe
        await consumer.subscribe([topic])

        # Get metrics
        metrics = await consumer.get_metrics()

        # Note: Metrics might be empty until consumer has processed messages
        # This is a basic test of the API
        assert isinstance(metrics, list)


@pytest.mark.integration
@pytest.mark.asyncio
class TestSchemaRegistry:
    """Test event schema registry and validation."""

    def test_register_schema(self):
        """Test registering new schema."""
        registry = SchemaRegistry()

        schema = EventSchema(
            namespace="com.test",
            name="TestEvent",
            version=1,
            fields={
                "event_id": "string",
                "action": "string",
                "timestamp": "string",
            },
            doc="Test event schema",
        )

        version = registry.register("test.events", schema)
        assert version.schema.name == "TestEvent"
        assert version.schema.version == 1

    def test_backward_compatibility(self):
        """Test backward compatible schema evolution."""
        registry = SchemaRegistry()

        # V1: basic fields
        v1 = EventSchema(
            namespace="com.test",
            name="UserEvent",
            version=1,
            fields={
                "user_id": "string",
                "action": "string",
            },
            compatibility="BACKWARD",
        )
        registry.register("user.events", v1)

        # V2: add optional field (backward compatible)
        v2 = EventSchema(
            namespace="com.test",
            name="UserEvent",
            version=2,
            fields={
                "user_id": "string",
                "action": "string",
                "mfa_enabled": "boolean",  # NEW
            },
            compatibility="BACKWARD",
        )
        registry.register("user.events", v2)

        # V1 data should be valid for V2
        old_event = {"user_id": "123", "action": "login"}
        assert registry.validate_event("user.events", old_event)

    def test_forward_compatibility_rejected(self):
        """Test forward incompatible schema is rejected."""
        registry = SchemaRegistry()

        v1 = EventSchema(
            namespace="com.test",
            name="Event",
            version=1,
            fields={"id": "string", "data": "string"},
            compatibility="BACKWARD",
        )
        registry.register("events", v1)

        # V2: remove required field (NOT backward compatible with BACKWARD mode)
        v2 = EventSchema(
            namespace="com.test",
            name="Event",
            version=2,
            fields={"id": "string"},  # Removed 'data'
            compatibility="BACKWARD",
        )

        with pytest.raises(ValueError, match="not compatible"):
            registry.register("events", v2)

    def test_schema_validation(self):
        """Test event validation against schema."""
        registry = SchemaRegistry()

        schema = EventSchema(
            namespace="com.test",
            name="ValidatedEvent",
            version=1,
            fields={
                "event_id": "string",
                "status": "string",
            },
        )
        registry.register("validated.events", schema)

        # Valid event
        valid = {"event_id": "123", "status": "success"}
        assert registry.validate_event("validated.events", valid)

        # Invalid: missing required field
        invalid = {"event_id": "123"}
        assert not registry.validate_event("validated.events", invalid)

    def test_list_schemas(self):
        """Test listing registered schemas."""
        registry = SchemaRegistry()

        schema1 = EventSchema(
            namespace="com.test",
            name="Event1",
            version=1,
            fields={"id": "string"},
        )
        schema2 = EventSchema(
            namespace="com.test",
            name="Event2",
            version=1,
            fields={"id": "string"},
        )

        registry.register("topic1", schema1)
        registry.register("topic2", schema2)

        schemas = registry.list_schemas()
        assert "topic1" in schemas
        assert "topic2" in schemas
        assert len(schemas["topic1"]) == 1

    def test_avro_schema_format(self):
        """Test Avro schema export."""
        schema = EventSchema(
            namespace="com.neurex.auth",
            name="LoginEvent",
            version=1,
            fields={
                "user_id": "string",
                "timestamp": "string",
                "success": "boolean",
            },
        )

        avro = schema.to_avro()
        assert avro["type"] == "record"
        assert avro["namespace"] == "com.neurex.auth"
        assert avro["name"] == "LoginEvent"
        assert len(avro["fields"]) == 3

    def test_protobuf_schema_format(self):
        """Test Protobuf schema export."""
        schema = EventSchema(
            namespace="com.neurex.auth",
            name="LoginEvent",
            version=1,
            fields={
                "user_id": "string",
                "timestamp": "string",
            },
        )

        proto = schema.to_protobuf()
        assert "syntax" in proto
        assert "package com.neurex.auth" in proto
        assert "message LoginEvent" in proto


@pytest.mark.integration
@pytest.mark.asyncio
class TestOutboxRelayKafka:
    """Test Outbox → Kafka relay."""

    async def test_outbox_relay_publishes_to_kafka(self):
        """Test end-to-end outbox relay to Kafka."""
        from app.infra.event_streaming.outbox_relay_kafka import OutboxRelayKafka, OutboxEntry
        from unittest.mock import AsyncMock, MagicMock

        # Mock broker and repository
        broker = AsyncMock()
        broker.publish = AsyncMock(return_value="offset-123")

        repo = MagicMock()
        repo._get_session = MagicMock()

        relay = OutboxRelayKafka(broker=broker, repository=repo)

        # Create test entry
        entry = OutboxEntry(
            id="entry-1",
            event_type="auth.user_created",
            aggregate_id="user-123",
            payload={"email": "test@example.com"},
            metadata={},
            status="pending",
        )

        # Publish
        msg_id = await relay._publish_entry(entry)

        # Verify broker was called
        broker.publish.assert_called_once()
        call_args = broker.publish.call_args
        assert call_args[1]["topic"] == "auth.events"
        assert call_args[1]["partition_key"] == "user-123"
        assert msg_id == "offset-123"

    async def test_topic_mapping(self):
        """Test event_type to topic mapping."""
        from app.infra.event_streaming.outbox_relay_kafka import OutboxRelayKafka
        from unittest.mock import AsyncMock

        broker = AsyncMock()
        repo = AsyncMock()

        relay = OutboxRelayKafka(broker=broker, repository=repo)

        # Test default mapping
        assert relay._default_topic_mapper("auth.user_login") == "auth.events"
        assert relay._default_topic_mapper("test.scenario_created") == "test.events"
        assert relay._default_topic_mapper("defect.opened") == "defect.events"


@pytest.mark.integration
@pytest.mark.asyncio
class TestConsumerGroupCoordination:
    """Test consumer group coordination."""

    async def test_consumer_group_with_multiple_partitions(self):
        """Test consumer handles multiple partitions."""
        broker = KafkaBroker(bootstrap_servers="localhost:9092")
        consumer = ExactlyOnceConsumer(
            group_id="test-multi-partition",
            bootstrap_servers="localhost:9092",
        )

        try:
            # Create topic with 3 partitions
            await broker.create_topic("test.multipart", num_partitions=3)

            # Publish events to different partitions (via partition key)
            for i in range(9):
                await broker.publish(
                    "test.multipart",
                    {"event_id": f"evt-{i}"},
                    partition_key=f"key-{i % 3}",
                )

            # Subscribe and consume
            await consumer.subscribe(["test.multipart"])

            received = []

            async def handler(msg):
                received.append(msg)

            # Run for short time
            async def consume_loop():
                try:
                    await asyncio.wait_for(
                        consumer.consume(handler, timeout_ms=100),
                        timeout=3.0,
                    )
                except asyncio.TimeoutError:
                    pass

            await consume_loop()

            # Should receive events from all partitions
            assert len(received) > 0

        finally:
            await broker.close()
            await consumer.close()
