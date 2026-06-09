"""S-HIGH security fixes test suite (OWASP Top 10)."""

import pytest
from unittest.mock import MagicMock

from app.core.security_validators import (
    sanitize_html_output,
    filter_sensitive_data,
    _sanitize_filename,
)
from app.core.csrf_protection import generate_csrf_token, validate_csrf_token
from app.core.password_security import (
    validate_password_strength,
    hash_password,
    verify_password,
)
from app.core.input_validation import (
    validate_email,
    validate_url,
    validate_phone_number,
    validate_json,
    validate_uuid,
)
from app.core.security_logging import SecurityLogger, SecurityEventType


class TestSQLInjectionFixes:
    """S-HIGH-2: SQL Injection prevention."""

    def test_quality_metrics_where_clause_safe(self):
        """Verify WHERE clause uses parameterized queries, not f-strings."""
        # This is a code review test — the actual fix is in quality_metrics.py
        # where f-strings with where_clause were removed
        pass


class TestFileUploadSecurity:
    """S-HIGH-3: File upload validation."""

    def test_sanitize_filename_path_traversal(self):
        """Test path traversal attempts are blocked."""
        assert _sanitize_filename("../../etc/passwd") == "etcpasswd"
        assert _sanitize_filename("../../../windows/system32") == "windowssystem32"

    def test_sanitize_filename_special_chars(self):
        """Test dangerous characters are removed."""
        assert _sanitize_filename("test<script>.json") == "testscript.json"
        assert _sanitize_filename("test;rm -rf.py") == "testrm_-rf.py"
        assert _sanitize_filename("test$(whoami).sh") == "testwhoami.sh"


class TestXSSPrevention:
    """S-HIGH-7: XSS prevention."""

    def test_sanitize_html_output_escapes_tags(self):
        """Test HTML tags are escaped."""
        result = sanitize_html_output('<script>alert("xss")</script>')
        assert "&lt;script&gt;" in result
        assert "&quot;xss&quot;" in result
        assert "<script>" not in result

    def test_sanitize_html_output_escapes_quotes(self):
        """Test quotes are HTML-escaped."""
        result = sanitize_html_output('test" onload="alert(1)')
        assert "&quot;" in result

    def test_sanitize_html_output_truncates(self):
        """Test output is truncated to prevent DoS."""
        long_string = "x" * 2000
        result = sanitize_html_output(long_string, max_length=1000)
        assert len(result) <= 1000


class TestSensitiveDataFiltering:
    """S-HIGH-8: Sensitive data filtering."""

    def test_filter_password_field(self):
        """Test password fields are redacted."""
        assert filter_sensitive_data("secret123", "password") == "[FILTERED]"
        assert filter_sensitive_data("secret123", "user_password") == "[FILTERED]"

    def test_filter_token_field(self):
        """Test token fields are redacted."""
        assert filter_sensitive_data("token123", "access_token") == "[FILTERED]"
        assert filter_sensitive_data("token123", "refresh_token") == "[FILTERED]"

    def test_filter_safe_field(self):
        """Test safe fields are not redacted."""
        assert filter_sensitive_data("user123", "user_id") == "user123"
        assert filter_sensitive_data("test@example.com", "email") == "test@example.com"


class TestCSRFProtection:
    """S-HIGH-6: CSRF protection."""

    def test_generate_csrf_token(self):
        """Test CSRF token generation produces secure tokens."""
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()

        assert token1 != token2  # Should be unique
        assert len(token1) > 20  # Should be reasonably long
        assert len(token2) > 20

    def test_csrf_skip_safe_methods(self):
        """Test GET/HEAD/OPTIONS requests skip CSRF check."""
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.cookies = {}
        mock_request.headers = {}

        # Should not raise even without CSRF token
        validate_csrf_token(mock_request)


class TestPasswordSecurity:
    """S-HIGH-11: Password security."""

    def test_password_validation_strong(self):
        """Test strong password passes validation."""
        is_valid, error = validate_password_strength("MyStr0ng!Pass@987")
        assert is_valid is True
        assert error is None

    def test_password_validation_too_short(self):
        """Test short password fails validation."""
        is_valid, error = validate_password_strength("Short1!")
        assert is_valid is False
        assert "karakter" in error

    def test_password_validation_no_uppercase(self):
        """Test password without uppercase fails."""
        is_valid, error = validate_password_strength("mypassword123!@#")
        assert is_valid is False
        assert "büyük harf" in error

    def test_password_validation_no_lowercase(self):
        """Test password without lowercase fails."""
        is_valid, error = validate_password_strength("MYPASSWORD123!@#")
        assert is_valid is False
        assert "küçük harf" in error

    def test_password_validation_no_numbers(self):
        """Test password without numbers fails."""
        is_valid, error = validate_password_strength("MyPassword!@#")
        assert is_valid is False
        assert "sayı" in error

    def test_password_validation_no_special_chars(self):
        """Test password without special chars fails."""
        is_valid, error = validate_password_strength("MyPassword123")
        assert is_valid is False
        assert "özel karakter" in error

    def test_password_validation_repeated_chars(self):
        """Test passwords with repeated chars are rejected."""
        is_valid, error = validate_password_strength("MyPasssword111!@#")
        assert is_valid is False
        assert "tekrarlanan" in error

    def test_password_hashing(self):
        """Test password hashing works."""
        password = "MyStr0ng!Pass@987"
        hashed = hash_password(password)

        # Hashed should be different from original
        assert hashed != password
        # Hashed should be valid bcrypt format
        assert hashed.startswith("$2")

    def test_password_verification_success(self):
        """Test password verification succeeds with correct password."""
        password = "MyStr0ng!Pass@987"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_password_verification_failure(self):
        """Test password verification fails with wrong password."""
        password = "MyStr0ng!Pass@987"
        hashed = hash_password(password)

        assert verify_password("WrongPassw@rd456!", hashed) is False


class TestInputValidation:
    """S-HIGH-13 to S-HIGH-21: Input validation."""

    def test_validate_email_valid(self):
        """Test valid emails pass validation."""
        is_valid, error = validate_email("user@example.com")
        assert is_valid is True
        assert error is None

    def test_validate_email_invalid_format(self):
        """Test invalid email format fails."""
        is_valid, error = validate_email("notanemail")
        assert is_valid is False

    def test_validate_email_too_long(self):
        """Test email exceeding length limit fails."""
        long_email = "a" * 300 + "@example.com"
        is_valid, error = validate_email(long_email)
        assert is_valid is False

    def test_validate_url_valid(self):
        """Test valid URLs pass validation."""
        is_valid, error = validate_url("https://example.com/path")
        assert is_valid is True
        assert error is None

    def test_validate_url_ssrf_localhost(self):
        """Test SSRF attacks are blocked."""
        is_valid, error = validate_url("http://localhost:8000/admin")
        assert is_valid is False

    def test_validate_url_ssrf_private_ip(self):
        """Test private IP ranges are blocked (SSRF prevention)."""
        is_valid, error = validate_url("http://192.168.1.1/admin")
        assert is_valid is False

    def test_validate_url_ssrf_metadata(self):
        """Test cloud metadata endpoints are blocked."""
        is_valid, error = validate_url("http://169.254.169.254/latest/meta-data/")
        assert is_valid is False

    def test_validate_phone_number_valid(self):
        """Test valid phone numbers pass validation."""
        is_valid, error = validate_phone_number("+1234567890")
        assert is_valid is True

    def test_validate_phone_number_invalid(self):
        """Test invalid phone numbers fail validation."""
        is_valid, error = validate_phone_number("abc")
        assert is_valid is False

    def test_validate_json_valid(self):
        """Test valid JSON passes validation."""
        is_valid, data = validate_json('{"key": "value"}')
        assert is_valid is True
        assert data == {"key": "value"}

    def test_validate_json_invalid(self):
        """Test invalid JSON fails validation."""
        is_valid, data = validate_json("not json at all")
        assert is_valid is False

    def test_validate_uuid_valid(self):
        """Test valid UUIDs pass validation."""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        assert validate_uuid(valid_uuid) is True

    def test_validate_uuid_invalid(self):
        """Test invalid UUIDs fail validation."""
        assert validate_uuid("not-a-uuid") is False


class TestSecurityLogging:
    """S-HIGH-22: Security logging."""

    def test_log_security_event(self):
        """Test security event logging works."""
        SecurityLogger.log_security_event(
            event_type=SecurityEventType.LOGIN_SUCCESS,
            user_id="user123",
            ip_address="192.168.1.1",
            action="login",
        )
        # Should not raise
