"""Shared HTTP client singleton with connection pooling.

This module provides reusable httpx.Client and httpx.AsyncClient instances
to avoid creating new clients for every request (which exhausts sockets and
wastes connection pool reuse).

Instead of:
  async with httpx.AsyncClient(timeout=30) as client:
    await client.get(...)

Use:
  from app.infra.http_client import get_async_client
  client = get_async_client(timeout=30)  # singleton per timeout
  await client.get(...)
"""

import threading
from typing import Optional, Union

import httpx

# Thread-safe singletons per timeout configuration
_sync_clients: dict[tuple, httpx.Client] = {}
_async_clients: dict[tuple, httpx.AsyncClient] = {}
_lock = threading.Lock()


def _normalize_timeout(timeout: Optional[Union[float, httpx.Timeout]]) -> tuple:
    """Convert timeout to a hashable key."""
    if isinstance(timeout, httpx.Timeout):
        return (
            timeout.timeout,
            timeout.connect,
            timeout.read,
            timeout.write,
            timeout.pool,
        )
    return (timeout,)


def get_sync_client(
    timeout: Optional[Union[float, httpx.Timeout]] = 30.0,
    follow_redirects: bool = False,
    verify: bool = True,
) -> httpx.Client:
    """Get or create a sync HTTP client singleton with connection pooling.

    Args:
        timeout: Connection timeout in seconds (default 30s)
        follow_redirects: Whether to follow HTTP redirects
        verify: Whether to verify SSL certificates

    Returns:
        Shared httpx.Client instance for the given configuration
    """
    key = (_normalize_timeout(timeout), follow_redirects, verify)
    if key not in _sync_clients:
        with _lock:
            if key not in _sync_clients:  # Double-check pattern
                _sync_clients[key] = httpx.Client(
                    timeout=timeout,
                    follow_redirects=follow_redirects,
                    verify=verify,
                    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                )
    return _sync_clients[key]


def get_async_client(
    timeout: Optional[Union[float, httpx.Timeout]] = 30.0,
    follow_redirects: bool = False,
    verify: bool = True,
) -> httpx.AsyncClient:
    """Get or create an async HTTP client singleton with connection pooling.

    Args:
        timeout: Connection timeout in seconds (default 30s)
        follow_redirects: Whether to follow HTTP redirects
        verify: Whether to verify SSL certificates

    Returns:
        Shared httpx.AsyncClient instance for the given configuration
    """
    key = (_normalize_timeout(timeout), follow_redirects, verify)
    if key not in _async_clients:
        with _lock:
            if key not in _async_clients:  # Double-check pattern
                _async_clients[key] = httpx.AsyncClient(
                    timeout=timeout,
                    follow_redirects=follow_redirects,
                    verify=verify,
                    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                )
    return _async_clients[key]


async def cleanup_async_clients() -> None:
    """Close all async client instances (call during app shutdown)."""
    for client in _async_clients.values():
        await client.aclose()
    _async_clients.clear()


def cleanup_sync_clients() -> None:
    """Close all sync client instances (call during app shutdown)."""
    for client in _sync_clients.values():
        client.close()
    _sync_clients.clear()
