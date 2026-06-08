"""Otomasyon Süiti iş mantığı.

Sorumluluklar:
  * Engine (Flask :5001) çağrıları (async httpx)
  * Kalıcı koşum kaydı (SQL ``automation_suite_runs``; DB erişilemezse
    in-memory fallback) — pod restart'ında koşum geçmişi kaybolmaz
  * Üretilen Gherkin'i DSL kataloğuyla eşleştirip bilinen/bilinmeyen
    cümlecik raporu üretme
"""
from __future__ import annotations

import asyncio
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone as _tz
from threading import RLock
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.domains.automation_suite.schemas import (
    Framework,
    RunStatus,
    SuiteCatalogSuggestItem,
    SuiteCatalogSuggestResponse,
    SuiteGenerateRequest,
    SuiteGenerateResponse,
    SuiteHealthResponse,
    SuiteRunRequest,
    SuiteRunResponse,
    SuiteRunStatus,
)
from app.domains.dsl import service as dsl_service

logger = logging.getLogger(__name__)

_INTERNAL_KEY_HEADER = "X-Internal-Key"

# Engine'deki orkestrasyon endpoint'leri
_ENGINE_PIPELINE_PATH = "/api/pipeline/manual-to-automation"
_ENGINE_RUN_FEATURE_PATH = "/api/runner/run-feature"
_ENGINE_HEALTH_PATH = "/health"


def _engine_base() -> str:
    return settings.engine_base_url.rstrip("/")


def _engine_internal_key() -> str:
    # Not: Oncelikle ENGINE_INTERNAL_KEY env degiskeni okunur (eski davranis),
    # yoksa Settings icindeki engine_internal_key (.env + default) kullanilir.
    import os

    return os.environ.get("ENGINE_INTERNAL_KEY") or settings.engine_internal_key


def _engine_headers() -> dict[str, str]:
    return {_INTERNAL_KEY_HEADER: _engine_internal_key()}


# ── Run Registry (SQL-backed) ─────────────────────────────────────────────────

_MAX_LOG_LINES = 200


@dataclass
class _RunRecord:
    run_id: str
    status: RunStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    feature_path: Optional[str] = None
    framework: Optional[Framework] = None
    passed: Optional[int] = None
    failed: Optional[int] = None
    error: Optional[str] = None
    report_url: Optional[str] = None
    logs: List[str] = field(default_factory=list)


class _RunRegistry:
    """Koşum registry'si — SQL (``automation_suite_runs``) kaynak-of-truth.

    Koşum kayıtları kalıcıdır: pod restart'ında geçmiş kaybolmaz. DB bir
    nedenle erişilemezse thread-safe in-memory dict'e graceful düşülür, böylece
    koşum yine de yürür (yalnızca o kayıt kalıcı olmaz).
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._store: Dict[str, _RunRecord] = {}  # DB erişilemezse fallback

    @staticmethod
    def _row_to_record(row: Any) -> _RunRecord:
        return _RunRecord(
            run_id=row.run_id,
            status=row.status,
            started_at=row.started_at,
            completed_at=row.completed_at,
            feature_path=row.feature_path,
            framework=row.framework,
            passed=row.passed,
            failed=row.failed,
            error=row.error,
            report_url=row.report_url,
            logs=list(row.logs or []),
        )

    def create(self, *, feature_path: Optional[str], framework: Optional[Framework]) -> _RunRecord:
        run_id = uuid.uuid4().hex[:16]
        rec = _RunRecord(
            run_id=run_id,
            status="queued",
            started_at=datetime.now(_tz.utc),
            feature_path=feature_path,
            framework=framework,
        )
        try:
            from app.domains.automation_suite.models import AutomationSuiteRun
            from app.infra.database import SessionLocal

            with SessionLocal() as db:
                db.add(AutomationSuiteRun(
                    run_id=rec.run_id,
                    status=rec.status,
                    started_at=rec.started_at,
                    feature_path=rec.feature_path,
                    framework=rec.framework,
                    logs=[],
                ))
                db.commit()
            return rec
        except Exception as exc:  # noqa: BLE001
            logger.warning("AutomationSuite: DB create başarısız, in-memory fallback (%s)", exc)
            with self._lock:
                self._store[run_id] = rec
            return rec

    def update(self, run_id: str, **fields: Any) -> Optional[_RunRecord]:
        try:
            from app.domains.automation_suite.models import AutomationSuiteRun
            from app.infra.database import SessionLocal

            with SessionLocal() as db:
                row = db.get(AutomationSuiteRun, run_id)
                if row is not None:
                    for key, value in fields.items():
                        if hasattr(row, key):
                            setattr(row, key, value)
                    db.commit()
                    return self._row_to_record(row)
        except Exception as exc:  # noqa: BLE001
            logger.warning("AutomationSuite: DB update başarısız (%s)", exc)
        with self._lock:
            rec = self._store.get(run_id)
            if rec is None:
                return None
            for key, value in fields.items():
                if hasattr(rec, key):
                    setattr(rec, key, value)
            return rec

    def append_log(self, run_id: str, line: str) -> None:
        try:
            from app.domains.automation_suite.models import AutomationSuiteRun
            from app.infra.database import SessionLocal

            with SessionLocal() as db:
                row = db.get(AutomationSuiteRun, run_id)
                if row is not None:
                    logs = list(row.logs or [])
                    logs.append(line)
                    if len(logs) > _MAX_LOG_LINES:
                        logs = logs[-_MAX_LOG_LINES:]
                    row.logs = logs  # reassign → JSONB dirty tracking
                    db.commit()
                    return
        except Exception as exc:  # noqa: BLE001
            logger.warning("AutomationSuite: DB append_log başarısız (%s)", exc)
        with self._lock:
            rec = self._store.get(run_id)
            if rec is None:
                return
            rec.logs.append(line)
            if len(rec.logs) > _MAX_LOG_LINES:
                rec.logs = rec.logs[-_MAX_LOG_LINES:]

    def get(self, run_id: str) -> Optional[_RunRecord]:
        try:
            from app.domains.automation_suite.models import AutomationSuiteRun
            from app.infra.database import SessionLocal

            with SessionLocal() as db:
                row = db.get(AutomationSuiteRun, run_id)
                if row is not None:
                    return self._row_to_record(row)
        except Exception as exc:  # noqa: BLE001
            logger.warning("AutomationSuite: DB get başarısız (%s)", exc)
        with self._lock:
            return self._store.get(run_id)


_registry = _RunRegistry()


# ── Generate ────────────────────────────────────────────────────────────────

async def generate_from_manual_test(req: SuiteGenerateRequest) -> SuiteGenerateResponse:
    """Engine pipeline'ını çağırıp sonucu DSL ile zenginleştirir."""
    payload = {
        "test_id": req.manual_test_id,
        "target_url": req.target_url or "",
        "framework": req.framework,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{_engine_base()}{_ENGINE_PIPELINE_PATH}",
                json=payload,
                headers=_engine_headers(),
            )
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("Engine pipeline hata: %s %s", exc.response.status_code, exc.response.text[:200])
        raise RuntimeError(
            f"Engine pipeline HTTP {exc.response.status_code}: {exc.response.text[:200]}"
        ) from exc
    except httpx.RequestError as exc:
        logger.error("Engine pipeline ulaşılamıyor: %s", exc)
        raise RuntimeError(f"Engine ulaşılamıyor: {exc}") from exc

    gherkin = str(data.get("gherkin") or "")
    generated_code = (
        data.get("playwright_code")
        or data.get("generated_code")
        or data.get("code")
    )

    matched, unknown = _match_gherkin_with_dsl(gherkin)

    run_id: Optional[str] = None
    if req.auto_run and data.get("feature_path"):
        run = await start_run(
            SuiteRunRequest(
                feature_path=str(data["feature_path"]),
                framework=req.framework,
                headless=True,
                tags=[],
            )
        )
        run_id = run.run_id

    return SuiteGenerateResponse(
        ok=bool(data.get("ok", True)),
        test_title=str(data.get("test_title") or ""),
        steps_count=int(data.get("steps_count") or 0),
        gherkin=gherkin,
        framework=req.framework,
        generated_code=generated_code if isinstance(generated_code, str) else None,
        feature_path=data.get("feature_path"),
        locators=data.get("locators"),
        model=data.get("model"),
        dsl_matched_actions=matched,
        dsl_unknown_steps=unknown,
        run_id=run_id,
    )


_GHERKIN_STEP_RE = re.compile(
    r"^\s*(Given|When|Then|And|But)\s+(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _match_gherkin_with_dsl(gherkin: str) -> tuple[list[str], list[str]]:
    """Gherkin içindeki her adımı DSL search ile eşleştirir.

    Dönüş:
        matched_action_ids  — en az bir DSL cümleciği ile eşleşen adımların aksiyon ID'leri (tekil)
        unknown_steps       — hiçbir cümlecik ile eşleşmeyen adım metinleri
    """
    matched: list[str] = []
    unknown: list[str] = []
    seen: set[str] = set()

    if not gherkin:
        return matched, unknown

    for m in _GHERKIN_STEP_RE.finditer(gherkin):
        step_text = m.group(2).strip()
        if not step_text:
            continue
        # Tırnak içindeki parametreyi yer tutucu yap
        normalized = re.sub(r'"[^"]*"', "{text}", step_text)
        hits = dsl_service.search_actions(normalized, limit=1)
        if hits.items:
            aid = hits.items[0].action.id
            if aid not in seen:
                matched.append(aid)
                seen.add(aid)
        else:
            unknown.append(step_text)

    return matched, unknown


# ── Run ─────────────────────────────────────────────────────────────────────

async def start_run(req: SuiteRunRequest) -> SuiteRunResponse:
    """Feature dosyasını engine runner üzerinden koştur (async).

    Hemen bir `run_id` döner, koşum arka planda yürür. Durum sorgusu için
    `get_run_status(run_id)` kullanılır.
    """
    if not req.feature_path and not req.suite_id:
        raise ValueError("feature_path veya suite_id zorunludur")

    rec = _registry.create(
        feature_path=req.feature_path,
        framework=req.framework,
    )

    asyncio.create_task(_execute_run(rec.run_id, req))
    return SuiteRunResponse(
        run_id=rec.run_id,
        status=rec.status,
        message="Koşum kuyruğa alındı",
    )


async def _execute_run(run_id: str, req: SuiteRunRequest) -> None:
    _registry.update(run_id, status="running")
    _registry.append_log(run_id, f"[{_now()}] Koşum başlıyor: {req.feature_path}")

    payload: dict[str, Any] = {
        "feature_path": req.feature_path,
        "headless": req.headless,
        "framework": req.framework,
    }
    if req.tags:
        payload["tags"] = req.tags

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(
                f"{_engine_base()}{_ENGINE_RUN_FEATURE_PATH}",
                json=payload,
                headers=_engine_headers(),
            )
            resp.raise_for_status()
            body: Dict[str, Any] = resp.json()
    except httpx.HTTPStatusError as exc:
        _registry.update(
            run_id,
            status="error",
            completed_at=datetime.now(_tz.utc),
            error=f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
        )
        _registry.append_log(run_id, f"[{_now()}] HATA: {exc}")
        return
    except httpx.RequestError as exc:
        _registry.update(
            run_id,
            status="error",
            completed_at=datetime.now(_tz.utc),
            error=f"Engine ulaşılamıyor: {exc}",
        )
        _registry.append_log(run_id, f"[{_now()}] Engine bağlantı hatası: {exc}")
        return

    # Engine yanıtlarının biçimi zamanla değişebilir — savunmacı okuma
    passed = int(body.get("passed") or body.get("passed_count") or 0)
    failed = int(body.get("failed") or body.get("failed_count") or 0)
    report_url = body.get("report_url") or body.get("allure_url")
    ok = bool(body.get("ok", failed == 0))

    final_status: RunStatus = "passed" if ok and failed == 0 else "failed"
    _registry.update(
        run_id,
        status=final_status,
        completed_at=datetime.now(_tz.utc),
        passed=passed,
        failed=failed,
        report_url=report_url if isinstance(report_url, str) else None,
    )
    _registry.append_log(run_id, f"[{_now()}] Tamamlandı: passed={passed} failed={failed}")


def _now() -> str:
    return datetime.now(_tz.utc).strftime("%H:%M:%S")


def get_run_status(run_id: str) -> Optional[SuiteRunStatus]:
    rec = _registry.get(run_id)
    if rec is None:
        return None
    duration_ms: Optional[int] = None
    if rec.completed_at and rec.started_at:
        duration_ms = int((rec.completed_at - rec.started_at).total_seconds() * 1000)
    return SuiteRunStatus(
        run_id=rec.run_id,
        status=rec.status,
        started_at=rec.started_at,
        completed_at=rec.completed_at,
        duration_ms=duration_ms,
        feature_path=rec.feature_path,
        framework=rec.framework,
        passed=rec.passed,
        failed=rec.failed,
        error=rec.error,
        report_url=rec.report_url,
        logs_tail=rec.logs[-50:],
    )


# ── Catalog Suggest (DSL proxy + yüksek seviye format) ─────────────────────

def suggest_from_description(description: str, limit: int = 10) -> SuiteCatalogSuggestResponse:
    raw = dsl_service.suggest_actions(description, limit=limit)
    items = [
        SuiteCatalogSuggestItem(
            action_id=h.action.id,
            category=h.action.category,
            matched_language=h.matched_language,
            matched_alias=h.matched_alias,
            description=h.action.description,
        )
        for h in raw.items
    ]
    return SuiteCatalogSuggestResponse(
        query=raw.query,
        total=raw.total,
        items=items,
    )


# ── Health ──────────────────────────────────────────────────────────────────

async def health_snapshot() -> SuiteHealthResponse:
    """Backend + Engine + DSL sağlık özeti."""
    engine_info: dict[str, Any] = {"base_url": _engine_base(), "status": "unreachable"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{_engine_base()}{_ENGINE_HEALTH_PATH}",
                headers=_engine_headers(),
            )
            engine_info["http"] = resp.status_code
            if resp.status_code == 200:
                engine_info["status"] = "ok"
                engine_info["data"] = resp.json()
            else:
                engine_info["status"] = "degraded"
    except httpx.RequestError as exc:
        engine_info["status"] = "unreachable"
        engine_info["error"] = str(exc)[:120]

    stats = dsl_service.get_stats()
    dsl_info: dict[str, Any] = {
        "total_actions": stats.total,
        "loaded_at": stats.loaded_at,
    }

    overall = "ok" if engine_info["status"] == "ok" else "degraded"
    return SuiteHealthResponse(
        status=overall,
        engine=engine_info,
        dsl=dsl_info,
    )
