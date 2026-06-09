"""S-HIGH security logging and audit trail.

OWASP A9: Insufficient logging & monitoring
- Centralized security event logging
- Sensitive data redaction in logs
- Audit trail for sensitive operations
- Failed authentication tracking
- Unauthorized access attempts
- Rate limit violation logging
- Data modification audit log
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Optional

_logger = logging.getLogger(__name__)


class SecurityEventType(str, Enum):
    """S-HIGH-22: Security event classification."""

    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGIN_LOCKOUT = "login_lockout"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET = "password_reset"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    SESSION_TERMINATED = "session_terminated"

    # Authorization events
    PERMISSION_DENIED = "permission_denied"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"

    # Data access events
    DATA_ACCESSED = "data_accessed"
    DATA_MODIFIED = "data_modified"
    DATA_DELETED = "data_deleted"
    DATA_EXPORTED = "data_exported"

    # Security events
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    CSRF_TOKEN_INVALID = "csrf_token_invalid"
    FILE_UPLOAD_REJECTED = "file_upload_rejected"
    VULNERABILITY_DETECTED = "vulnerability_detected"

    # Administrative events
    CONFIGURATION_CHANGED = "configuration_changed"
    SECURITY_POLICY_VIOLATED = "security_policy_violated"
    AUDIT_LOG_ACCESSED = "audit_log_accessed"


class SecurityLogger:
    """S-HIGH-22: Centralized security event logger with sensitive data redaction."""

    # Sensitive field patterns to redact
    SENSITIVE_FIELDS = {
        "password", "passwd", "pwd",
        "token", "access_token", "refresh_token",
        "secret", "api_secret", "api_key",
        "auth", "authorization", "bearer",
        "credential", "credentials",
        "hmac", "signature",
        "key", "private_key", "public_key",
        "ssn", "credit_card", "card_number",
        "cvv", "pin", "otp",
    }

    REDACTION_MARKER = "[REDACTED]"

    @staticmethod
    def log_security_event(
        event_type: SecurityEventType,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        severity: str = "INFO",
    ) -> None:
        """S-HIGH-22a: Log security event with structured data.

        All sensitive fields are automatically redacted.

        Args:
            event_type: Type of security event
            user_id: User who triggered event
            ip_address: Client IP address
            resource: Resource affected (e.g., "user:123", "project:abc")
            action: Action performed
            details: Additional structured data
            severity: Log level (INFO, WARNING, ERROR, CRITICAL)
        """
        # Redact sensitive data from details
        safe_details = SecurityLogger._redact_sensitive_fields(details or {})

        event_data = {
            "event_type": event_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id or "anonymous",
            "ip_address": ip_address or "unknown",
            "resource": resource,
            "action": action,
            **safe_details,
        }

        log_message = json.dumps(event_data, default=str)

        if severity == "CRITICAL":
            _logger.critical(log_message)
        elif severity == "ERROR":
            _logger.error(log_message)
        elif severity == "WARNING":
            _logger.warning(log_message)
        else:
            _logger.info(log_message)

    @staticmethod
    def log_failed_login(
        username: str,
        ip_address: str,
        reason: str = "invalid_credentials",
    ) -> None:
        """S-HIGH-22b: Log failed login attempt."""
        SecurityLogger.log_security_event(
            event_type=SecurityEventType.LOGIN_FAILED,
            user_id=username,
            ip_address=ip_address,
            action="login",
            details={"reason": reason},
            severity="WARNING",
        )

    @staticmethod
    def log_successful_login(user_id: str, ip_address: str) -> None:
        """S-HIGH-22c: Log successful login."""
        SecurityLogger.log_security_event(
            event_type=SecurityEventType.LOGIN_SUCCESS,
            user_id=user_id,
            ip_address=ip_address,
            action="login",
            severity="INFO",
        )

    @staticmethod
    def log_permission_denied(
        user_id: str,
        permission: str,
        resource: str,
        ip_address: Optional[str] = None,
    ) -> None:
        """S-HIGH-22d: Log unauthorized permission access."""
        SecurityLogger.log_security_event(
            event_type=SecurityEventType.PERMISSION_DENIED,
            user_id=user_id,
            ip_address=ip_address,
            resource=resource,
            action=f"denied_{permission}",
            severity="WARNING",
        )

    @staticmethod
    def log_data_access(
        user_id: str,
        resource: str,
        action: str = "read",
        details: Optional[dict] = None,
    ) -> None:
        """S-HIGH-22e: Log data access for audit trail."""
        SecurityLogger.log_security_event(
            event_type=SecurityEventType.DATA_ACCESSED,
            user_id=user_id,
            resource=resource,
            action=action,
            details=details,
            severity="INFO",
        )

    @staticmethod
    def log_data_modification(
        user_id: str,
        resource: str,
        action: str,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
    ) -> None:
        """S-HIGH-22f: Log data modifications with before/after values."""
        details = {}
        if old_value is not None:
            details["old_value"] = SecurityLogger._safe_repr(old_value)
        if new_value is not None:
            details["new_value"] = SecurityLogger._safe_repr(new_value)

        SecurityLogger.log_security_event(
            event_type=SecurityEventType.DATA_MODIFIED,
            user_id=user_id,
            resource=resource,
            action=action,
            details=details,
            severity="WARNING",
        )

    @staticmethod
    def log_suspicious_activity(
        user_id: Optional[str],
        reason: str,
        ip_address: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        """S-HIGH-22g: Log suspicious activity for investigation."""
        SecurityLogger.log_security_event(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            user_id=user_id,
            ip_address=ip_address,
            action=reason,
            details=details,
            severity="ERROR",
        )

    @staticmethod
    def log_rate_limit_exceeded(
        user_id: Optional[str],
        endpoint: str,
        ip_address: Optional[str] = None,
        limit: int = 0,
        window_seconds: int = 0,
    ) -> None:
        """S-HIGH-22h: Log rate limit violations."""
        SecurityLogger.log_security_event(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            user_id=user_id,
            ip_address=ip_address,
            resource=endpoint,
            details={
                "limit": limit,
                "window_seconds": window_seconds,
            },
            severity="WARNING",
        )

    @staticmethod
    def _redact_sensitive_fields(data: dict[str, Any]) -> dict[str, Any]:
        """S-HIGH-22i: Redact sensitive fields from log data."""
        redacted = {}
        for key, value in data.items():
            if key.lower() in SecurityLogger.SENSITIVE_FIELDS:
                redacted[key] = SecurityLogger.REDACTION_MARKER
            elif isinstance(value, dict):
                redacted[key] = SecurityLogger._redact_sensitive_fields(value)
            elif isinstance(value, list):
                redacted[key] = [
                    SecurityLogger._redact_sensitive_fields(item)
                    if isinstance(item, dict)
                    else SecurityLogger.REDACTION_MARKER
                    if isinstance(item, str) and key.lower() in SecurityLogger.SENSITIVE_FIELDS
                    else item
                    for item in value
                ]
            else:
                redacted[key] = value
        return redacted

    @staticmethod
    def _safe_repr(value: Any) -> str:
        """S-HIGH-22j: Safe string representation of value."""
        try:
            if isinstance(value, (dict, list)):
                return json.dumps(value, default=str)[:500]  # Truncate long values
            return str(value)[:500]
        except Exception:
            return "<unable to serialize>"


# S-HIGH-23: Performance logging for slow queries/requests
class PerformanceLogger:
    """S-HIGH-23: Track slow queries and requests for security review."""

    SLOW_QUERY_THRESHOLD_MS = 1000
    SLOW_REQUEST_THRESHOLD_MS = 5000

    @staticmethod
    def log_slow_query(
        query: str,
        duration_ms: float,
        user_id: Optional[str] = None,
    ) -> None:
        """S-HIGH-23a: Log queries that take too long (potential DoS)."""
        if duration_ms > PerformanceLogger.SLOW_QUERY_THRESHOLD_MS:
            SecurityLogger.log_security_event(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                user_id=user_id,
                action="slow_query",
                details={
                    "duration_ms": round(duration_ms, 2),
                    "query_hash": _hash_query(query),
                },
                severity="WARNING",
            )

    @staticmethod
    def log_slow_request(
        endpoint: str,
        method: str,
        duration_ms: float,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """S-HIGH-23b: Log slow HTTP requests."""
        if duration_ms > PerformanceLogger.SLOW_REQUEST_THRESHOLD_MS:
            SecurityLogger.log_security_event(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                user_id=user_id,
                ip_address=ip_address,
                resource=f"{method} {endpoint}",
                action="slow_request",
                details={"duration_ms": round(duration_ms, 2)},
                severity="WARNING",
            )


def _hash_query(query: str) -> str:
    """Hash query to reduce log size while maintaining uniqueness."""
    import hashlib
    return hashlib.md5(query.encode()).hexdigest()[:8]
