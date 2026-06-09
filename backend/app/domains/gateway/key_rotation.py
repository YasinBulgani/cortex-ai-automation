"""AI Gateway internal key rotation and lifecycle management.

Manages GATEWAY_INTERNAL_KEY rotation to prevent unauthorized access.
Supports key versioning and graceful migration.
"""

from datetime import datetime, timedelta, timezone as _tz
from typing import Optional
import secrets
import hashlib


class GatewayKeyRotation:
    """Manages gateway internal key lifecycle."""

    # Key rotation history kept in memory (production: use database)
    # Format: {version: {"key": "...", "created_at": datetime, "rotated_at": datetime}}
    _key_history: dict[int, dict] = {}
    _current_version: int = 0
    _max_history: int = 5

    @classmethod
    def generate_key(cls) -> str:
        """Generate new secure gateway internal key."""
        return f"gw_{secrets.token_urlsafe(40)}"

    @classmethod
    def rotate_key(cls, old_key: str, new_key: Optional[str] = None) -> tuple[str, int]:
        """Rotate gateway key with history tracking.

        Args:
            old_key: Current key being rotated
            new_key: Optional pre-generated key (testing)

        Returns:
            (new_key, version)
        """
        new_key = new_key or cls.generate_key()
        cls._current_version += 1
        version = cls._current_version

        cls._key_history[version] = {
            "key": new_key,
            "key_hash": cls._hash_key(new_key),
            "created_at": datetime.now(_tz.utc),
            "rotated_at": None,
            "rotated_from": cls._hash_key(old_key) if old_key else None,
        }

        # Cleanup old entries beyond max_history
        if len(cls._key_history) > cls._max_history:
            oldest = min(cls._key_history.keys())
            del cls._key_history[oldest]

        return new_key, version

    @classmethod
    def verify_key(cls, provided_key: str) -> bool:
        """Verify key against current and recent versions."""
        provided_hash = cls._hash_key(provided_key)

        # Check current version first (most common)
        if cls._current_version in cls._key_history:
            if cls._key_history[cls._current_version]["key_hash"] == provided_hash:
                return True

        # Check recent history (grace period for migration)
        for version in sorted(cls._key_history.keys(), reverse=True):
            if cls._key_history[version]["key_hash"] == provided_hash:
                # Still valid (within rotation window)
                return True

        return False

    @classmethod
    def get_current_key_version(cls) -> int:
        """Get current key version."""
        return cls._current_version

    @classmethod
    def get_key_status(cls) -> dict:
        """Get gateway key rotation status."""
        return {
            "current_version": cls._current_version,
            "total_versions": len(cls._key_history),
            "created_at": cls._key_history[cls._current_version]["created_at"].isoformat()
            if cls._current_version in cls._key_history
            else None,
            "last_rotation": max(
                (v["created_at"] for v in cls._key_history.values() if v["created_at"]),
                default=None,
            ),
        }

    @staticmethod
    def _hash_key(key: str) -> str:
        """Hash key for secure comparison."""
        return hashlib.sha256(key.encode()).hexdigest()

    @classmethod
    def export_key_for_deployment(cls, key: str) -> str:
        """Export key in safe format for deployment.

        Returns environment variable assignment.
        """
        return f"GATEWAY_INTERNAL_KEY={key}"

    @classmethod
    def validate_rotation_schedule(cls) -> dict:
        """Suggest rotation schedule based on key age."""
        if not cls._key_history:
            return {"status": "no_keys", "action": "initialize_key"}

        current_info = cls._key_history.get(cls._current_version, {})
        created_at = current_info.get("created_at")

        if created_at is None:
            return {"status": "unknown", "action": "check_deployment"}

        age_days = (datetime.now(_tz.utc) - created_at).days
        max_age_days = 90

        if age_days > max_age_days:
            return {
                "status": "overdue",
                "action": "rotate_immediately",
                "age_days": age_days,
                "max_age_days": max_age_days,
            }
        elif age_days > max_age_days * 0.8:
            return {
                "status": "aging",
                "action": "rotate_soon",
                "age_days": age_days,
                "max_age_days": max_age_days,
            }
        else:
            return {
                "status": "fresh",
                "action": "no_action_needed",
                "age_days": age_days,
                "max_age_days": max_age_days,
            }
