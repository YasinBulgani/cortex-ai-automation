"""Unit tests for app.domains.api_testing.network_security pure helpers.

Tests are fully self-contained: no DB, no HTTP.
Covers:
  - _is_blocked_ip: private/loopback/link-local/multicast/reserved IPs
  - UnsafeTargetError exception class
  - validate_outbound_url: scheme validation and blocked IP detection
"""
from __future__ import annotations

import pytest

try:
    from app.domains.api_testing.network_security import (
        _is_blocked_ip,
        UnsafeTargetError,
        validate_outbound_url,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="network_security import failed")


# ---------------------------------------------------------------------------
# _is_blocked_ip
# ---------------------------------------------------------------------------

class TestIsBlockedIp:
    def test_loopback_blocked(self):
        assert _is_blocked_ip("127.0.0.1") is True

    def test_loopback_ipv6_blocked(self):
        assert _is_blocked_ip("::1") is True

    def test_private_10_blocked(self):
        assert _is_blocked_ip("10.0.0.1") is True

    def test_private_192_168_blocked(self):
        assert _is_blocked_ip("192.168.1.100") is True

    def test_private_172_16_blocked(self):
        assert _is_blocked_ip("172.16.0.1") is True

    def test_link_local_blocked(self):
        assert _is_blocked_ip("169.254.0.1") is True

    def test_multicast_blocked(self):
        assert _is_blocked_ip("224.0.0.1") is True

    def test_public_ip_not_blocked(self):
        assert _is_blocked_ip("8.8.8.8") is False

    def test_public_ip_1_1_1_1(self):
        assert _is_blocked_ip("1.1.1.1") is False

    def test_public_ipv6_not_blocked(self):
        # 2001:4860:4860::8888 is Google's public DNS
        assert _is_blocked_ip("2001:4860:4860::8888") is False

    def test_unspecified_ip_blocked(self):
        assert _is_blocked_ip("0.0.0.0") is True

    def test_localhost_127_0_0_2(self):
        assert _is_blocked_ip("127.0.0.2") is True


# ---------------------------------------------------------------------------
# UnsafeTargetError
# ---------------------------------------------------------------------------

class TestUnsafeTargetError:
    def test_is_value_error(self):
        exc = UnsafeTargetError("test message")
        assert isinstance(exc, ValueError)

    def test_message_preserved(self):
        exc = UnsafeTargetError("blocked")
        assert "blocked" in str(exc)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(UnsafeTargetError):
            raise UnsafeTargetError("test")

    def test_can_be_caught_as_value_error(self):
        with pytest.raises(ValueError):
            raise UnsafeTargetError("test")


# ---------------------------------------------------------------------------
# validate_outbound_url
# ---------------------------------------------------------------------------

class TestValidateOutboundUrl:
    def test_ftp_scheme_raises(self):
        with pytest.raises(UnsafeTargetError, match="http"):
            validate_outbound_url("ftp://example.com/file")

    def test_file_scheme_raises(self):
        with pytest.raises(UnsafeTargetError):
            validate_outbound_url("file:///etc/passwd")

    def test_loopback_url_raises(self):
        with pytest.raises(UnsafeTargetError):
            validate_outbound_url("http://127.0.0.1/api")

    def test_private_ip_url_raises(self):
        with pytest.raises(UnsafeTargetError):
            validate_outbound_url("http://192.168.1.1/api")

    def test_10_net_raises(self):
        with pytest.raises(UnsafeTargetError):
            validate_outbound_url("https://10.0.0.1/endpoint")

    def test_no_host_raises(self):
        with pytest.raises(UnsafeTargetError):
            validate_outbound_url("http:///path")
