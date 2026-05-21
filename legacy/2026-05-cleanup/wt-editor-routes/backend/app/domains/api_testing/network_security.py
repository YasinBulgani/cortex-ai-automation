"""Outbound network security guards for API testing."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeTargetError(ValueError):
    """Raised when an outbound URL targets an unsafe destination."""


_BLOCKED_HOSTS = {
    "localhost",
    "metadata.google.internal",
    "metadata.google",
    "host.docker.internal",
}
_SAFE_TEST_SUFFIXES = (".test", ".example", ".invalid")


def _is_blocked_ip(ip_text: str) -> bool:
    ip_obj = ipaddress.ip_address(ip_text)
    return any(
        (
            ip_obj.is_private,
            ip_obj.is_loopback,
            ip_obj.is_link_local,
            ip_obj.is_multicast,
            ip_obj.is_reserved,
            ip_obj.is_unspecified,
        )
    )


def _resolve_host_ips(hostname: str) -> set[str]:
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeTargetError("Hostname cozumlenemedi") from exc

    return {info[4][0] for info in infos}


def validate_outbound_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeTargetError("Yalnizca http/https URL'leri desteklenir")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeTargetError("Gecerli bir hedef host gerekli")

    lowered = hostname.lower().strip(".")
    if lowered in _BLOCKED_HOSTS or lowered.endswith(".localhost") or lowered.endswith(".internal"):
        raise UnsafeTargetError("Ic ag veya local hedeflere erisim engellendi")
    if lowered.endswith(_SAFE_TEST_SUFFIXES):
        return

    try:
        if _is_blocked_ip(lowered):
            raise UnsafeTargetError("Ic ag veya local IP adreslerine erisim engellendi")
        return
    except ValueError:
        pass

    for resolved_ip in _resolve_host_ips(lowered):
        if _is_blocked_ip(resolved_ip):
            raise UnsafeTargetError("Hedef host ic ag IP'lerine cozuluyor; istek engellendi")
