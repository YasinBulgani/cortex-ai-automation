"""Prompts REST API.

Endpoints:
    Registry:
        GET    /prompts                          → liste
        GET    /prompts/{id}                     → detay
        PUT    /prompts/{id}                     → meta upsert
        POST   /prompts/{id}/archive             → archived=True
        POST   /prompts/{id}/unarchive           → archived=False

    Versions:
        GET    /prompts/{id}/versions            → versiyon listesi
        GET    /prompts/{id}/versions/{v}        → tek versiyon
        POST   /prompts/{id}/versions            → yeni versiyon (monotonik)

    Rollouts:
        GET    /prompts/{id}/rollouts            → tüm env'ler
        GET    /prompts/{id}/rollouts/{env}      → tek env
        PUT    /prompts/{id}/rollouts/{env}      → upsert

    Resolve (caller sıcak yolu):
        GET    /prompts/{id}/resolve?tenant=X&env=prod
               → çözülmüş prompt + decision_reason
"""
from __future__ import annotations

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import get_current_user, require_permission
from app.infra.models import User

from .schemas import (
    Env,
    PromptIn,
    PromptOut,
    PromptVersionIn,
    PromptVersionOut,
    ResolvedPrompt,
    RolloutIn,
    RolloutOut,
)
from .service import (
    add_version,
    archive_prompt,
    get_prompt,
    get_rollout,
    get_version,
    list_prompts,
    list_rollouts,
    list_versions,
    resolve,
    upsert_prompt,
    upsert_rollout,
)

router = APIRouter(prefix="/prompts", tags=["prompts"])


_ADMIN_PERM = "admin.prompts"


def _actor(user: User) -> str:
    return getattr(user, "email", None) or str(user.id)


# ── Registry ─────────────────────────────────────────────────────────────


@router.get("", response_model=List[PromptOut])
def _list(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
    include_archived: bool = Query(default=False),
) -> List[PromptOut]:
    return list_prompts(include_archived=include_archived)


@router.get("/{prompt_id}", response_model=PromptOut)
def _get(
    prompt_id: str,
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> PromptOut:
    out = get_prompt(prompt_id)
    if out is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt yok")
    return out


@router.put("/{prompt_id}", response_model=PromptOut)
def _upsert(
    prompt_id: str,
    payload: PromptIn,
    user: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> PromptOut:
    try:
        return upsert_prompt(prompt_id, payload, actor=_actor(user))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post("/{prompt_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
def _archive(
    prompt_id: str,
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> None:
    if not archive_prompt(prompt_id, True):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt yok")


@router.post("/{prompt_id}/unarchive", status_code=status.HTTP_204_NO_CONTENT)
def _unarchive(
    prompt_id: str,
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> None:
    if not archive_prompt(prompt_id, False):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt yok")


# ── Versions ─────────────────────────────────────────────────────────────


@router.get("/{prompt_id}/versions", response_model=List[PromptVersionOut])
def _list_versions(
    prompt_id: str,
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
    limit: int = Query(default=100, ge=1, le=500),
) -> List[PromptVersionOut]:
    return list_versions(prompt_id, limit=limit)


@router.get("/{prompt_id}/versions/{version}", response_model=PromptVersionOut)
def _get_version(
    prompt_id: str,
    version: int,
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> PromptVersionOut:
    out = get_version(prompt_id, version)
    if out is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Versiyon yok")
    return out


@router.post(
    "/{prompt_id}/versions",
    response_model=PromptVersionOut,
    status_code=status.HTTP_201_CREATED,
)
def _add_version(
    prompt_id: str,
    payload: PromptVersionIn,
    user: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> PromptVersionOut:
    # Var olup olmadığını garanti et — FK constraint de yakalar ama user-friendly
    if get_prompt(prompt_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt önce oluşturulmalı",
        )
    return add_version(prompt_id, payload, actor=_actor(user))


# ── Rollouts ─────────────────────────────────────────────────────────────


@router.get("/{prompt_id}/rollouts", response_model=List[RolloutOut])
def _list_rollouts(
    prompt_id: str,
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> List[RolloutOut]:
    return list_rollouts(prompt_id)


@router.get("/{prompt_id}/rollouts/{env}", response_model=RolloutOut)
def _get_rollout(
    prompt_id: str,
    env: Env,
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> RolloutOut:
    out = get_rollout(prompt_id, env)
    if out is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rollout yok")
    return out


@router.put("/{prompt_id}/rollouts/{env}", response_model=RolloutOut)
def _upsert_rollout(
    prompt_id: str,
    env: Env,
    payload: RolloutIn,
    user: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> RolloutOut:
    try:
        return upsert_rollout(prompt_id, env, payload, actor=_actor(user))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


# ── Resolve ─────────────────────────────────────────────────────────────


@router.get("/{prompt_id}/resolve", response_model=ResolvedPrompt)
def _resolve(
    prompt_id: str,
    user: Annotated[User, Depends(get_current_user)],
    tenant: Optional[str] = Query(default=None),
    env: Env = Query(default="prod"),
) -> ResolvedPrompt:
    resolved_tenant = tenant or getattr(user, "tenant_id", None) or str(user.id)
    out = resolve(prompt_id, tenant_id=str(resolved_tenant), env=env)
    if out is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt/versiyon bulunamadı",
        )
    return out
