"""Runtime bootstrap helpers for FastAPI app startup."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
import subprocess
import threading
import time
from typing import Any, Optional, Tuple

from fastapi import FastAPI

from app.config import settings
from app.domains.tspm.scheduler import shutdown_scheduler, start_scheduler

logger = logging.getLogger(__name__)
_SHUTDOWN_TIMEOUT_SEC = 5.0


def _background_feature_enabled(feature_name: str, enabled: bool) -> bool:
    """Gate optional startup side effects for test/CI and explicit flags."""
    if not enabled:
        logger.info("%s devre disi: ilgili runtime flag kapali.", feature_name)
        return False
    if settings.is_test_like:
        logger.info("%s atlandi: test/CI benzeri ortam algilandi.", feature_name)
        return False
    return True


def initialize_sentry() -> None:
    """Initialize Sentry once when configured."""
    sentry_dsn = os.getenv("SENTRY_DSN", "")
    if not sentry_dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                RedisIntegration(),
                LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR),
            ],
            send_default_pii=False,
            before_send=lambda event, hint: event,
        )
        logger.info(
            "Sentry aktif: environment=%s",
            os.getenv("SENTRY_ENVIRONMENT", "production"),
        )
    except ImportError:
        logger.info("sentry-sdk kurulu değil, hata izleme devre dışı.")


def build_rate_limiter() -> Tuple[Optional[Any], bool, Optional[type], Optional[Any]]:
    """Create optional slowapi rate limiter components."""
    require_rate_limit = settings.is_production_like or os.getenv(
        "RATE_LIMIT_REQUIRED",
        "",
    ).lower() in {"1", "true", "yes"}
    if require_rate_limit:
        ensure_redis_available(required=True)
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.util import get_remote_address

        limiter = Limiter(
            key_func=get_remote_address,
            default_limits=[settings.rate_limit_default],
            storage_uri=settings.redis_url,
        )
        return limiter, True, RateLimitExceeded, _rate_limit_exceeded_handler
    except ImportError as exc:
        if require_rate_limit:
            raise RuntimeError(
                "slowapi bagimliligi bulunamadi. Production/strict modda rate limiting zorunlu."
            ) from exc
        logger.warning("slowapi bulunamadi, rate limiting devre disi.")
        return None, False, None, None
    except Exception:
        if require_rate_limit:
            raise
        logger.warning("Rate limiter baslatilamadi, rate limiting devre disi.", exc_info=True)
        return None, False, None, None


def _redis_required() -> bool:
    forced = os.getenv("REDIS_REQUIRED", "").lower() in {"1", "true", "yes"}
    return forced or settings.is_production_like


def ensure_redis_available(*, required: bool | None = None) -> bool:
    must_have = _redis_required() if required is None else required
    if not must_have:
        return False

    try:
        import redis
    except ImportError as exc:
        raise RuntimeError(
            "Redis client bagimliligi bulunamadi. Production/strict modda redis zorunlu."
        ) from exc

    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return True
    except Exception as exc:
        raise RuntimeError(
            "Redis baglantisi basarisiz. Production/strict modda calisir bir redis zorunlu."
        ) from exc


def configure_prometheus(app: FastAPI) -> None:
    """Enable Prometheus metrics when the feature flag is on."""
    if os.getenv("PROMETHEUS_ENABLED", "false").lower() not in ("1", "true", "yes"):
        return

    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            excluded_handlers=["/health", "/ready", "/metrics"],
        ).instrument(app).expose(app, endpoint="/metrics")
        logger.info("Prometheus metrikleri aktif: /metrics")
    except ImportError:
        logger.info("prometheus-fastapi-instrumentator kurulu değil, /metrics devre dışı.")


def _startup_index_project() -> None:
    """Index repo context into the KnowledgeStore in the background."""
    time.sleep(5)
    try:
        from app.domains.ai.knowledge_store import KnowledgeStore

        store = KnowledgeStore(project_id="__system__")
        total = store.stats(project_id="__system__").get("total", 0)
        if total > 100:
            logger.info(
                "KnowledgeStore zaten %d kayıt içeriyor, startup indexleme atlanıyor.",
                total,
            )
            return

        project_root = Path(__file__).resolve().parent.parent.parent
        logger.info("Startup proje indexleme başlıyor... (root: %s)", project_root)
        count = 0

        for base in [project_root / "engine" / "features", project_root / "e2e"]:
            if not base.exists():
                continue
            for file_path in sorted(base.rglob("*.feature")):
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                if len(text.strip()) <= 20:
                    continue
                store.ingest(
                    text=text[:4000],
                    source="feature_file",
                    metadata={"file": str(file_path.relative_to(project_root))},
                    project_id="__system__",
                )
                count += 1

        docs_dir = project_root / "docs"
        if docs_dir.exists():
            for file_path in sorted(docs_dir.rglob("*.md")):
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                if len(text.strip()) <= 30:
                    continue
                store.ingest(
                    text=text[:4000],
                    source="docs",
                    metadata={"file": str(file_path.relative_to(project_root))},
                    project_id="__system__",
                )
                count += 1

        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-30", "--no-merges", "--format=%h %s"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                store.ingest(
                    text="Son commit'ler:\n" + result.stdout.strip(),
                    source="code_change",
                    metadata={"type": "startup_git_log"},
                    project_id="__system__",
                )
                count += 1
        except Exception:
            logger.debug("Git log ingest atlandı.", exc_info=True)

        logger.info("Startup indexleme tamamlandı: %d kayıt eklendi.", count)
    except Exception as exc:
        logger.warning("Startup indexleme hatası: %s", exc)


def _start_banking_scheduler() -> None:
    try:
        from app.domains.agents.banking_team.scheduler_agent import (
            start_scheduler as start_banking_scheduler,
        )

        start_banking_scheduler()
    except Exception as exc:
        logger.warning("Banking scheduler başlatılamadı: %s", exc)


def _start_file_watcher() -> None:
    try:
        from app.domains.ai.file_watcher import start_file_watcher

        start_file_watcher()
    except Exception as exc:
        logger.warning("File watcher başlatılamadı: %s", exc)


def _stop_file_watcher() -> None:
    try:
        from app.domains.ai.file_watcher import stop_file_watcher

        stop_file_watcher()
    except Exception:
        logger.debug("File watcher kapatılırken hata oluştu.", exc_info=True)


def _stop_banking_scheduler() -> None:
    try:
        from app.domains.agents.banking_team.scheduler_agent import stop_banking_scheduler

        stop_banking_scheduler()
    except ImportError:
        logger.debug("Banking scheduler modulu bulunamadi, shutdown atlandi.")
    except Exception:
        logger.debug("Banking scheduler kapatilirken hata olustu.", exc_info=True)


async def _shutdown_playwright_sessions() -> None:
    try:
        from app.domains.playwright_mcp.browser_manager import get_browser_manager

        await asyncio.wait_for(get_browser_manager().shutdown(), timeout=_SHUTDOWN_TIMEOUT_SEC)
        logger.info("Playwright sessions kapatildi.")
    except Exception:
        logger.debug("Playwright shutdown atlandi.", exc_info=True)


async def _shutdown_async_ai_clients() -> None:
    try:
        from app.domains.ai.service import shutdown_async_clients

        await asyncio.wait_for(shutdown_async_clients(), timeout=_SHUTDOWN_TIMEOUT_SEC)
        logger.info("Async LLM client'lari kapatildi.")
    except Exception:
        logger.debug("Async LLM client shutdown atlandi.", exc_info=True)


@asynccontextmanager
async def app_lifespan(_app: FastAPI):
    """Manage startup and shutdown side effects."""
    started_scheduler = False
    started_banking_scheduler = False
    started_file_watcher = False

    Path(settings.artifacts_dir).mkdir(parents=True, exist_ok=True)
    ensure_redis_available()
    if _background_feature_enabled("Ana scheduler", settings.runtime_scheduler_enabled):
        start_scheduler()
        started_scheduler = True

    if _background_feature_enabled(
        "Banking scheduler",
        settings.runtime_banking_scheduler_enabled,
    ):
        _start_banking_scheduler()
        started_banking_scheduler = True

    if _background_feature_enabled(
        "Startup proje indexleme",
        settings.runtime_startup_index_enabled,
    ):
        threading.Thread(target=_startup_index_project, daemon=True).start()

    if _background_feature_enabled("File watcher", settings.runtime_file_watcher_enabled):
        _start_file_watcher()
        started_file_watcher = True

    yield

    logger.info("BGTS backend kapatiliyor...")

    await _shutdown_playwright_sessions()

    if started_file_watcher:
        try:
            await asyncio.wait_for(asyncio.to_thread(_stop_file_watcher), timeout=_SHUTDOWN_TIMEOUT_SEC)
        except Exception:
            logger.debug("File watcher shutdown atlandi.", exc_info=True)

    if started_banking_scheduler:
        try:
            await asyncio.wait_for(asyncio.to_thread(_stop_banking_scheduler), timeout=_SHUTDOWN_TIMEOUT_SEC)
        except Exception:
            logger.debug("Banking scheduler shutdown atlandi.", exc_info=True)

    if started_scheduler:
        try:
            await asyncio.wait_for(asyncio.to_thread(shutdown_scheduler), timeout=_SHUTDOWN_TIMEOUT_SEC)
        except Exception:
            logger.debug("Ana scheduler shutdown atlandi.", exc_info=True)

    await _shutdown_async_ai_clients()

    logger.info("BGTS backend kapatildi.")
