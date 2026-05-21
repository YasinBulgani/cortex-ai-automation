"""Self-healing webhook router + LLM bind.

Endpoints:
    POST /coverup/heal/events     → FailureEvent al, orchestrator'ı tetikle
                                    (sync yanıt — HealingRun özeti)
    GET  /coverup/heal/runs       → son N heal run'ı (in-memory history)
    GET  /coverup/heal/runs/{id}  → tek run detayı
    GET  /coverup/heal/status     → bağlı servislerin durumu (LLM, GitHub)
    POST /coverup/heal/bind-llm   → runtime'da LLM wiring (admin)

In-memory run history:
    * Thread-safe ring buffer (son 200)
    * Persist E3.3 (audit) entegrasyonunda; şimdilik dashboard için yeter

LLM bind stratejisi:
    * Startup'ta main.py çağırır `wire_llm_to_gateway()` — ai-gateway
      üstünden qwen2.5 coder'ı kullanacak şekilde bind eder
    * Test'te bind olmaz; orchestrator "no_proposal" döner
"""
from __future__ import annotations

import logging
import os
import threading
from collections import deque
from pathlib import Path
from typing import Annotated, Deque, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import get_current_user, require_permission
from app.infra.models import User

from .healing.github_client import GitHubClient, TokenAuth
from .healing.locator_healer import LlmCallable, locator_healer
from .healing.orchestrator import HealingConfig, HealingOrchestrator
from .healing.schemas import FailureEvent, HealingRun

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/coverup/heal", tags=["coverup-healing"])


_ADMIN_PERM = "admin.coverup"


# ── In-memory history ─────────────────────────────────────────────────────


_HISTORY_MAX = 200
_history: Deque[HealingRun] = deque(maxlen=_HISTORY_MAX)
_history_lock = threading.RLock()


def _record(run: HealingRun) -> None:
    with _history_lock:
        _history.append(run)


def _recent(limit: int, status_filter: Optional[str] = None) -> List[HealingRun]:
    with _history_lock:
        items = list(_history)
    if status_filter:
        items = [r for r in items if r.status == status_filter]
    items.reverse()  # en yeni başta
    return items[:limit]


def _by_id(run_id: str) -> Optional[HealingRun]:
    with _history_lock:
        for r in _history:
            if r.id == run_id:
                return r
    return None


# ── Orchestrator lazy factory ─────────────────────────────────────────────


_orch_lock = threading.RLock()
_orchestrator: Optional[HealingOrchestrator] = None


def _default_repo_root() -> Path:
    # backend/app/domains/coverup/healing_router.py → ../../../../../ (5 parents)
    return Path(__file__).resolve().parents[4]


def _resolve_github_client() -> Optional[GitHubClient]:
    """GitHub env'i varsa client kur, yoksa None (dry-run)."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("COVERUP_GITHUB_TOKEN")
    owner = os.environ.get("COVERUP_GITHUB_OWNER")
    repo = os.environ.get("COVERUP_GITHUB_REPO")
    if not (token and owner and repo):
        return None
    try:
        return GitHubClient(auth=TokenAuth(token=token), owner=owner, repo=repo)
    except Exception as exc:  # pragma: no cover - boot guard
        logger.warning("GitHub client kurulamadı: %s", exc)
        return None


def _get_orchestrator() -> HealingOrchestrator:
    global _orchestrator
    with _orch_lock:
        if _orchestrator is None:
            _orchestrator = HealingOrchestrator(
                config=HealingConfig(
                    repo_root=Path(
                        os.environ.get("COVERUP_REPO_ROOT") or _default_repo_root()
                    ),
                    base_branch=os.environ.get("COVERUP_BASE_BRANCH", "main"),
                ),
                healer=locator_healer,
                github=_resolve_github_client(),
            )
        return _orchestrator


def reset_orchestrator_for_testing() -> None:
    """Test-only — enjeksiyon sonrası yeniden kurulum tetikler."""
    global _orchestrator
    with _orch_lock:
        _orchestrator = None


# ── LLM bind ─────────────────────────────────────────────────────────────


def _gateway_llm_callable(
    *, model: str = "qwen2.5-coder", temperature: float = 0.2
) -> LlmCallable:
    """ai-gateway üstünden LLM çağırıcısı üretir.

    Healing özelinde düşük sıcaklık (deterministik JSON) ve coder modeli
    tercih edilir — selector üretimi yaratıcılık değil, DOM okuma.
    """
    from .healing.locator_healer import LlmCallable  # re-export hatırlatma
    from app.domains.ai import gateway_client as _gc

    def _call(system_prompt: str, user_prompt: str) -> str:
        return _gc.gateway_complete(
            task_type="code_generation",
            user_message=user_prompt,
            system_message=system_prompt,
            temperature=temperature,
            max_tokens=1200,
            model_override=model,
        )

    return _call


def wire_llm_to_gateway() -> bool:
    """Startup'ta main.py'dan çağrılır; healer'a LLM bind eder."""
    try:
        locator_healer.bind_llm(_gateway_llm_callable())
        logger.info("coverup.healing: LLM ai-gateway'e bağlandı")
        return True
    except Exception as exc:  # pragma: no cover - boot guard
        logger.warning("coverup.healing: LLM bind başarısız (%s)", exc)
        return False


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.post("/events", response_model=HealingRun)
def ingest_failure_event(
    event: FailureEvent,
    user: Annotated[User, Depends(get_current_user)],
) -> HealingRun:
    # Event'in tenant_id'si yoksa user'dan düş (budget + flag kapsamı için)
    if not event.tenant_id:
        event = event.model_copy(
            update={"tenant_id": str(getattr(user, "tenant_id", None) or user.id)}
        )
    orch = _get_orchestrator()
    run = orch.run(event)
    _record(run)
    return run


@router.get("/runs", response_model=List[HealingRun])
def list_runs(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
    limit: int = Query(default=50, ge=1, le=200),
    status_filter: Optional[str] = Query(default=None, alias="status"),
) -> List[HealingRun]:
    return _recent(limit, status_filter)


@router.get("/runs/{run_id}", response_model=HealingRun)
def get_run(
    run_id: str,
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> HealingRun:
    out = _by_id(run_id)
    if out is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run yok")
    return out


@router.get("/status")
def service_status(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> Dict[str, object]:
    orch = _get_orchestrator()
    return {
        "llm_bound": locator_healer._call_llm is not None,  # noqa: SLF001
        "github_configured": orch._gh is not None,  # noqa: SLF001
        "repo_root": str(orch._cfg.repo_root),  # noqa: SLF001
        "base_branch": orch._cfg.base_branch,  # noqa: SLF001
        "history_size": len(_history),
        "feature_flag_key": "coverup.auto_heal.enabled",
    }
