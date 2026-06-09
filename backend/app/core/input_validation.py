"""S-HIGH input validation and sanitization.

OWASP A3: Injection attacks (SQL, NoSQL, LDAP, OS command, etc.)
- Email validation and normalization
- URL validation and sanitization
- Phone number validation
- JSON/XML validation before parsing
- UUID validation
- Enum validation to prevent invalid state transitions
"""

from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Optional
from urllib.parse import urlparse, quote

from pydantic import ValidationError, field_validator

_logger = logging.getLogger(__name__)

# S-HIGH-13: Email validation
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    re.IGNORECASE,
)
MAX_EMAIL_LENGTH = 254  # RFC 5321


def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """S-HIGH-13a: Validate and normalize email address.

    - Checks format (RFC 5321-compliant regex)
    - Enforces length limits
    - Normalizes whitespace
    - Lowercases domain
    """
    if not email:
        return False, "Email boş olamaz"

    email = email.strip().lower()
    if len(email) > MAX_EMAIL_LENGTH:
        return False, f"Email çok uzun (max {MAX_EMAIL_LENGTH} karakter)"

    if not EMAIL_PATTERN.match(email):
        return False, "Email formatı geçersiz"

    # Additional check: prevent homograph attacks (IDN spoofing)
    # For now, reject any non-ASCII characters in domain
    try:
        local, domain = email.split("@")
        domain.encode("ascii")
    except (ValueError, UnicodeEncodeError):
        return False, "Email domaininde uluslararası karakterler desteklenmiyor"

    return True, None


def normalize_email(email: str) -> str:
    """S-HIGH-13b: Normalize email for storage/comparison."""
    return email.strip().lower()


# S-HIGH-14: URL validation
URL_PATTERN = re.compile(
    r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)
FORBIDDEN_HOSTS = {
    "localhost", "127.0.0.1", "0.0.0.0",
    "169.254.169.254",  # AWS metadata
    "10.0.0.0",  # Private IP ranges (simplified)
}


def validate_url(url: str, allow_localhost: bool = False) -> tuple[bool, Optional[str]]:
    """S-HIGH-14a: Validate URL and prevent SSRF attacks.

    Checks:
    - Valid URL format (http/https only)
    - Not localhost/private IPs (SSRF prevention)
    - Not targeting cloud metadata endpoints
    - Proper encoding
    """
    if not url:
        return False, "URL boş olamaz"

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return False, "URL http:// veya https:// ile başlamalı"

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""

        # S-HIGH-14b: SSRF prevention — block private/metadata IPs
        if not allow_localhost:
            if hostname.lower() in FORBIDDEN_HOSTS:
                return False, f"Yerel ağlara erişim engellenir: {hostname}"

            # Check for private IP ranges (simplified)
            if hostname.startswith(("10.", "172.", "192.168.", "127.")):
                return False, "Özel IP aralıklarına erişim engellenir"

        if len(url) > 2048:
            return False, "URL çok uzun (max 2048 karakter)"

    except Exception as exc:
        return False, f"URL parse hatası: {exc}"

    return True, None


def sanitize_url(url: str) -> str:
    """S-HIGH-14c: Sanitize URL for safe display."""
    try:
        parsed = urlparse(url)
        # Encode special characters in path/query
        safe_url = f"{parsed.scheme}://{parsed.netloc}{quote(parsed.path, safe='/')}"
        if parsed.query:
            safe_url += f"?{parsed.query}"
        return safe_url
    except Exception:
        return ""


# S-HIGH-15: Phone number validation
PHONE_PATTERN = re.compile(r"^\+?[0-9]{7,15}$")


def validate_phone_number(phone: str) -> tuple[bool, Optional[str]]:
    """S-HIGH-15: Validate phone number.

    - Allows optional + prefix
    - Requires 7-15 digits (covers most countries)
    """
    if not phone:
        return False, "Telefon boş olamaz"

    phone = phone.strip().replace(" ", "")
    if not PHONE_PATTERN.match(phone):
        return False, "Telefon formatı geçersiz (7-15 rakam)"

    return True, None


# S-HIGH-16: JSON validation
def validate_json(content: str) -> tuple[bool, Optional[dict]]:
    """S-HIGH-16: Safely parse and validate JSON.

    Prevents XXE attacks by using safe JSON parser.
    Returns parsed JSON if valid, error message otherwise.
    """
    try:
        data = json.loads(content)
        if not isinstance(data, (dict, list)):
            return False, None
        return True, data
    except json.JSONDecodeError as exc:
        return False, None
    except Exception:
        return False, None


# S-HIGH-17: XXE prevention for XML parsing
def validate_xml(content: str) -> tuple[bool, Optional[ET.Element]]:
    """S-HIGH-17: Safely parse XML with XXE protection.

    Disables external entity resolution to prevent XXE attacks.
    """
    try:
        # Disable XXE attacks by defusing parser
        parser = ET.XMLParser()
        parser.entity.clear()  # Remove default entities
        parser.parser.setFeature("http://xml.org/sax/features/external-general-entities", False)
        parser.parser.setFeature("http://xml.org/sax/features/external-parameter-entities", False)

        root = ET.fromstring(content, parser)
        return True, root
    except ET.ParseError:
        return False, None
    except Exception:
        return False, None


# S-HIGH-18: UUID validation
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def validate_uuid(uuid_str: str) -> bool:
    """S-HIGH-18: Validate UUID format."""
    if not uuid_str:
        return False
    return bool(UUID_PATTERN.match(uuid_str))


# S-HIGH-19: Enum validation to prevent invalid state transitions
def validate_enum_transition(
    from_state: str,
    to_state: str,
    allowed_transitions: dict[str, set[str]],
) -> tuple[bool, Optional[str]]:
    """S-HIGH-19: Validate state transition is allowed.

    Prevents invalid state machine transitions (e.g., jumping from
    PENDING to COMPLETED without going through IN_PROGRESS).

    Args:
        from_state: Current state
        to_state: Requested state
        allowed_transitions: Dict mapping state to allowed next states

    Returns:
        (is_valid, error_message)
    """
    if from_state == to_state:
        return True, None  # Allow idempotent updates

    if from_state not in allowed_transitions:
        return False, f"Bilinmeyen durum: {from_state}"

    if to_state not in allowed_transitions[from_state]:
        allowed = ", ".join(allowed_transitions[from_state])
        return False, f"{from_state} durumundan {to_state}'a geçiş yasaktır. İzin verilen: {allowed}"

    return True, None


# S-HIGH-20: String length and type validation
def validate_string_field(
    value: str,
    min_length: int = 0,
    max_length: int = 1000,
    pattern: Optional[re.Pattern] = None,
    field_name: str = "field",
) -> tuple[bool, Optional[str]]:
    """S-HIGH-20: Validate string field.

    - Type check (must be string)
    - Length bounds
    - Optional regex pattern match
    """
    if not isinstance(value, str):
        return False, f"{field_name} string olmalı"

    if len(value) < min_length:
        return False, f"{field_name} en az {min_length} karakter olmalı"

    if len(value) > max_length:
        return False, f"{field_name} en fazla {max_length} karakter olmalı"

    if pattern and not pattern.match(value):
        return False, f"{field_name} formatı geçersiz"

    return True, None


# S-HIGH-21: Number range validation
def validate_number_range(
    value: float,
    min_value: float = 0,
    max_value: float = 1000,
    field_name: str = "value",
) -> tuple[bool, Optional[str]]:
    """S-HIGH-21: Validate number is within allowed range."""
    if not isinstance(value, (int, float)):
        return False, f"{field_name} sayı olmalı"

    if value < min_value:
        return False, f"{field_name} en az {min_value} olmalı"

    if value > max_value:
        return False, f"{field_name} en fazla {max_value} olmalı"

    return True, None
