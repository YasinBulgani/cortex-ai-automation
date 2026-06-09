"""Standardized timeout configuration for HTTP requests.

Provides centralized timeout definitions to avoid inconsistent timeout
values scattered across the codebase (10s vs 30s vs 60s for similar operations).

All HTTP clients should use these constants or derive from them.
"""

import httpx

# Fast operations (DNS lookup, health checks, webhooks)
TIMEOUT_FAST = httpx.Timeout(3.0, connect=2.0)

# Standard operations (API calls, sync requests)
TIMEOUT_STANDARD = httpx.Timeout(30.0, connect=5.0, read=25.0)

# Long operations (large uploads, batch operations, AI generation)
TIMEOUT_LONG = httpx.Timeout(120.0, connect=5.0, read=115.0)

# Extra long operations (data migration, heavy processing)
TIMEOUT_EXTRA_LONG = httpx.Timeout(300.0, connect=5.0, read=295.0)

# Default used by get_sync_client/get_async_client
TIMEOUT_DEFAULT = TIMEOUT_STANDARD

# Mapping by operation type (for documentation)
TIMEOUT_BY_OPERATION = {
    "health_check": TIMEOUT_FAST,
    "ping": TIMEOUT_FAST,
    "webhook": TIMEOUT_FAST,
    "api_call": TIMEOUT_STANDARD,
    "file_upload": TIMEOUT_LONG,
    "batch_import": TIMEOUT_LONG,
    "ai_generation": TIMEOUT_LONG,
    "data_migration": TIMEOUT_EXTRA_LONG,
}
