"""Event Schema Registry — Avro/Protobuf versioning, validation, evolution.

Ensures schema compatibility across versions.
Supports schema evolution with forward/backward compatibility.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

logger = logging.getLogger(__name__)


class CompatibilityMode(str, Enum):
    """Schema compatibility modes."""
    NONE = "NONE"
    BACKWARD = "BACKWARD"  # New schema can read old data
    FORWARD = "FORWARD"    # Old schema can read new data
    FULL = "FULL"          # Both backward + forward


@dataclass
class EventSchema:
    """Event schema definition with versioning."""

    namespace: str  # e.g., "com.neurex.auth"
    name: str  # e.g., "UserLoginEvent"
    version: int  # e.g., 1
    fields: Dict[str, Any]  # Field name -> type definition
    doc: str = ""
    compatibility: CompatibilityMode = CompatibilityMode.BACKWARD

    def to_avro(self) -> Dict[str, Any]:
        """Convert to Avro schema format."""
        return {
            "type": "record",
            "namespace": self.namespace,
            "name": self.name,
            "fields": [
                {"name": k, "type": v} for k, v in self.fields.items()
            ],
            "doc": self.doc,
        }

    def to_protobuf(self) -> str:
        """Convert to Protobuf schema format (simplified)."""
        lines = [
            f'syntax = "proto3";',
            f'package {self.namespace};',
            f'',
            f'message {self.name} {{',
        ]
        for idx, (name, typ) in enumerate(self.fields.items(), 1):
            # Simplified: assumes simple types or nested messages
            lines.append(f'  {typ} {name} = {idx};')
        lines.append('}')
        return '\n'.join(lines)

    def validate(self, event: Dict[str, Any]) -> bool:
        """Basic validation: check required fields present."""
        for field_name in self.fields.keys():
            if field_name not in event:
                logger.warning(
                    "Schema validation failed: missing field '%s' in %s.%s",
                    field_name, self.namespace, self.name
                )
                return False
        return True


@dataclass
class SchemaVersion:
    """Track schema version with metadata."""

    schema: EventSchema
    registered_at: str  # ISO timestamp
    compatible_with: List[int] = field(default_factory=list)  # Version IDs


class SchemaRegistry:
    """Central registry for event schemas with versioning & compatibility checks."""

    def __init__(self):
        self._schemas: Dict[str, Dict[int, SchemaVersion]] = {}  # topic -> {version -> schema}
        self._lock = None  # For thread-safety in production

    def register(
        self,
        topic: str,
        schema: EventSchema,
        force: bool = False,
    ) -> SchemaVersion:
        """Register schema for topic.

        Args:
            topic: Topic/stream name
            schema: EventSchema instance
            force: Skip compatibility check (unsafe)

        Returns:
            SchemaVersion with metadata

        Raises:
            ValueError: If schema incompatible with latest
        """
        from datetime import datetime, timezone

        if topic not in self._schemas:
            self._schemas[topic] = {}

        existing = self._schemas[topic]
        latest_version = max(existing.keys()) if existing else 0

        # Check compatibility
        if existing and not force:
            latest_schema = existing[latest_version].schema
            if not self._is_compatible(schema, latest_schema):
                raise ValueError(
                    f"Schema not compatible with v{latest_version} "
                    f"(mode={schema.compatibility})"
                )

        schema_version = SchemaVersion(
            schema=schema,
            registered_at=datetime.now(timezone.utc).isoformat(),
            compatible_with=list(existing.keys()),
        )
        self._schemas[topic][schema.version] = schema_version
        logger.info("Schema registered (topic=%s, version=%d)",
                   topic, schema.version)
        return schema_version

    def get(self, topic: str, version: Optional[int] = None) -> Optional[EventSchema]:
        """Get schema by topic and version.

        Args:
            topic: Topic name
            version: Schema version (latest if None)

        Returns:
            EventSchema or None if not found
        """
        if topic not in self._schemas:
            return None

        if version is None:
            # Return latest version
            latest_v = max(self._schemas[topic].keys())
            return self._schemas[topic][latest_v].schema

        return self._schemas[topic].get(version)?.schema

    def validate_event(self, topic: str, event: Dict[str, Any]) -> bool:
        """Validate event against latest schema.

        Args:
            topic: Topic name
            event: Event payload

        Returns:
            True if valid, False otherwise
        """
        schema = self.get(topic)
        if schema is None:
            logger.warning("Schema not found for topic: %s", topic)
            return False

        return schema.validate(event)

    def list_schemas(self, topic: Optional[str] = None) -> Dict[str, List[EventSchema]]:
        """List all registered schemas."""
        if topic:
            return {
                topic: [sv.schema for sv in self._schemas[topic].values()]
                if topic in self._schemas else []
            }
        return {
            t: [sv.schema for sv in versions.values()]
            for t, versions in self._schemas.items()
        }

    def _is_compatible(self, new_schema: EventSchema, old_schema: EventSchema) -> bool:
        """Check compatibility based on mode.

        Simplified: just checks that all old fields exist in new.
        """
        mode = new_schema.compatibility

        if mode == CompatibilityMode.NONE:
            return False

        old_fields = set(old_schema.fields.keys())
        new_fields = set(new_schema.fields.keys())

        if mode == CompatibilityMode.BACKWARD:
            # New schema can read old data: all old fields must exist
            return old_fields.issubset(new_fields)

        elif mode == CompatibilityMode.FORWARD:
            # Old schema can read new data: new must not add required fields
            return new_fields.issubset(old_fields)

        elif mode == CompatibilityMode.FULL:
            # Both directions
            return old_fields == new_fields

        return False


# Global registry instance
_registry = SchemaRegistry()


def get_schema_registry() -> SchemaRegistry:
    """Get global schema registry."""
    return _registry


# ─────────────────────────────────────────────────────────────
# Standard Event Schemas (Neurex domains)
# ─────────────────────────────────────────────────────────────

def build_standard_schemas() -> Dict[str, EventSchema]:
    """Build standard event schemas for core domains."""

    return {
        "auth.events": EventSchema(
            namespace="com.neurex.auth",
            name="AuthEvent",
            version=1,
            fields={
                "event_id": "string",
                "user_id": "string",
                "action": "string",  # login, logout, mfa_enabled, password_changed
                "tenant_id": "string",
                "ip_address": "string",
                "user_agent": "string",
                "timestamp": "string",  # ISO 8601
                "success": "boolean",
                "reason": "string",  # If failed
            },
            doc="Authentication events (login, logout, MFA)",
        ),
        "test_management.events": EventSchema(
            namespace="com.neurex.test_management",
            name="TestManagementEvent",
            version=1,
            fields={
                "event_id": "string",
                "project_id": "string",
                "scenario_id": "string",
                "action": "string",  # created, updated, executed, failed
                "user_id": "string",
                "status": "string",
                "execution_time_ms": "int",
                "timestamp": "string",
            },
            doc="Test scenario lifecycle events",
        ),
        "execution.events": EventSchema(
            namespace="com.neurex.execution",
            name="ExecutionEvent",
            version=1,
            fields={
                "event_id": "string",
                "execution_id": "string",
                "project_id": "string",
                "action": "string",  # started, completed, failed, skipped
                "status": "string",
                "duration_ms": "int",
                "test_count": "int",
                "passed": "int",
                "failed": "int",
                "skipped": "int",
                "timestamp": "string",
            },
            doc="Test execution lifecycle events",
        ),
        "defect.events": EventSchema(
            namespace="com.neurex.defect",
            name="DefectEvent",
            version=1,
            fields={
                "event_id": "string",
                "defect_id": "string",
                "project_id": "string",
                "action": "string",  # opened, assigned, resolved, reopened
                "severity": "string",  # critical, high, medium, low
                "user_id": "string",
                "timestamp": "string",
            },
            doc="Defect lifecycle events",
        ),
        "audit.events": EventSchema(
            namespace="com.neurex.audit",
            name="AuditEvent",
            version=1,
            fields={
                "event_id": "string",
                "tenant_id": "string",
                "user_id": "string",
                "action": "string",
                "resource_type": "string",
                "resource_id": "string",
                "changes": "string",  # JSON-encoded
                "timestamp": "string",
            },
            doc="Audit trail events",
        ),
    }
