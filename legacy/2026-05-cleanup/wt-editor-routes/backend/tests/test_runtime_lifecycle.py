"""Lifecycle shutdown tests for backend runtime helpers."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi import FastAPI

from app.core import runtime
from app.domains.ai import service as ai_service


def test_app_lifespan_shutdown_order(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(runtime.settings, "artifacts_dir", str(tmp_path))
    monkeypatch.setattr(runtime, "start_scheduler", lambda: calls.append("start_scheduler"))
    monkeypatch.setattr(runtime, "_start_banking_scheduler", lambda: calls.append("start_banking"))
    monkeypatch.setattr(runtime, "_start_file_watcher", lambda: calls.append("start_file_watcher"))

    class _FakeThread:
        def __init__(self, target=None, daemon=None):
            self.target = target
            self.daemon = daemon

        def start(self):
            calls.append("startup_thread_started")

    async def _fake_wait_for(awaitable, timeout):
        return await awaitable

    async def _fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    async def _shutdown_playwright():
        calls.append("shutdown_playwright")

    async def _shutdown_ai_clients():
        calls.append("shutdown_ai_clients")

    monkeypatch.setattr(runtime.threading, "Thread", _FakeThread)
    monkeypatch.setattr(runtime.asyncio, "wait_for", _fake_wait_for)
    monkeypatch.setattr(runtime.asyncio, "to_thread", _fake_to_thread)
    monkeypatch.setattr(runtime, "_shutdown_playwright_sessions", _shutdown_playwright)
    monkeypatch.setattr(runtime, "_stop_file_watcher", lambda: calls.append("stop_file_watcher"))
    monkeypatch.setattr(runtime, "_stop_banking_scheduler", lambda: calls.append("stop_banking"))
    monkeypatch.setattr(runtime, "shutdown_scheduler", lambda: calls.append("shutdown_scheduler"))
    monkeypatch.setattr(runtime, "_shutdown_async_ai_clients", _shutdown_ai_clients)

    async def _exercise():
        async with runtime.app_lifespan(FastAPI()):
            calls.append("inside_lifespan")

    asyncio.run(_exercise())

    assert calls == [
        "start_scheduler",
        "start_banking",
        "startup_thread_started",
        "start_file_watcher",
        "inside_lifespan",
        "shutdown_playwright",
        "stop_file_watcher",
        "stop_banking",
        "shutdown_scheduler",
        "shutdown_ai_clients",
    ]


def test_app_lifespan_skips_background_side_effects_in_test_like_env(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(runtime.settings, "artifacts_dir", str(tmp_path))
    monkeypatch.setattr(runtime.settings, "testing", True)
    monkeypatch.setattr(runtime.settings, "ci", False)
    monkeypatch.setattr(runtime.settings, "app_env", "test")
    monkeypatch.setattr(runtime, "start_scheduler", lambda: calls.append("start_scheduler"))
    monkeypatch.setattr(runtime, "_start_banking_scheduler", lambda: calls.append("start_banking"))
    monkeypatch.setattr(runtime, "_start_file_watcher", lambda: calls.append("start_file_watcher"))

    class _FakeThread:
        def __init__(self, target=None, daemon=None):
            self.target = target
            self.daemon = daemon

        def start(self):
            calls.append("startup_thread_started")

    async def _fake_wait_for(awaitable, timeout):
        return await awaitable

    async def _fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    async def _shutdown_playwright():
        calls.append("shutdown_playwright")

    async def _shutdown_ai_clients():
        calls.append("shutdown_ai_clients")

    monkeypatch.setattr(runtime.threading, "Thread", _FakeThread)
    monkeypatch.setattr(runtime.asyncio, "wait_for", _fake_wait_for)
    monkeypatch.setattr(runtime.asyncio, "to_thread", _fake_to_thread)
    monkeypatch.setattr(runtime, "_shutdown_playwright_sessions", _shutdown_playwright)
    monkeypatch.setattr(runtime, "_stop_file_watcher", lambda: calls.append("stop_file_watcher"))
    monkeypatch.setattr(runtime, "_stop_banking_scheduler", lambda: calls.append("stop_banking"))
    monkeypatch.setattr(runtime, "shutdown_scheduler", lambda: calls.append("shutdown_scheduler"))
    monkeypatch.setattr(runtime, "_shutdown_async_ai_clients", _shutdown_ai_clients)

    async def _exercise():
        async with runtime.app_lifespan(FastAPI()):
            calls.append("inside_lifespan")

    asyncio.run(_exercise())

    assert calls == [
        "inside_lifespan",
        "shutdown_playwright",
        "shutdown_ai_clients",
    ]


def test_shutdown_async_clients_closes_and_clears_cached_clients():
    calls = []

    class _AsyncClient:
        def __init__(self, name):
            self.name = name

        async def close(self):
            calls.append(f"close:{self.name}")

    ai_service._async_openai_client = _AsyncClient("openai")
    ai_service._async_anthropic_client = _AsyncClient("anthropic")
    ai_service._async_ollama_client = _AsyncClient("ollama")

    asyncio.run(ai_service.shutdown_async_clients())

    assert calls == [
        "close:openai",
        "close:anthropic",
        "close:ollama",
    ]
    assert ai_service._async_openai_client is None
    assert ai_service._async_anthropic_client is None
    assert ai_service._async_ollama_client is None
