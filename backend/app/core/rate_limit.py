"""Shared slowapi limiter singleton for app and routers."""

from __future__ import annotations

from app.core.runtime import build_rate_limiter

limiter, has_rate_limit, rate_limit_exception, rate_limit_handler = build_rate_limiter()
