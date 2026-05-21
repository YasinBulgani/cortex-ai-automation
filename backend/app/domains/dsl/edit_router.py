"""DSL Sözlüğü düzenleme API'si.

Endpoint'ler:
    POST   /dsl/actions                         — yeni cümlecik oluştur
    PATCH  /dsl/actions/{id}                    — mevcut cümleciği güncelle
    DELETE /dsl/actions/{id}                    — cümleciği sil
    POST   /dsl/actions/{id}/deprecate          — deprecated işaretle
    GET    /dsl/proposals                       — öneri listesi (status, action_id)
    GET    /dsl/proposals/{id}                  — öneri detayı
    POST   /dsl/proposals/{id}/approve          — admin onayı
    POST   /dsl/proposals/{id}/reject           — admin reddi
    GET    /dsl/audit                           — katalog değişiklik geçmişi
    GET    /dsl/editor/config                   — git mode / strict_clean / enabled

Yetki:
    Tüm yazma endpoint'leri `dsl.edit` permission'ına sahip kullanıcıya açıktır;
    approve/reject ek olarak `dsl.approve` gerektirir.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.deps import get_current_user, require_permission
from app.domains.dsl import ai_assist, editor_service
from app.domains.dsl.editor_service import ApplyResult, ConflictError, EditorError, NotFoundError
from app.domains.dsl.schemas import DslAction
from app.infra.database import get_db
from app.infra.git_client import GitConfig
from app.infra.models import DslCatalogAudit, DslEditProposal, User

router = APIRouter(prefix="/dsl", tags=["dsl-edit"])


# ── Yetki dependency'leri ──────────────────────────────────────────────────

EditorUser = Annotated[User, Depends(require_permission("dsl.edit"))]
ApproverUser = Annotated[User, Depends(require_permission("dsl.approve"))]
ReaderUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


# ── Request/response şemaları ──────────────────────────────────────────────


class EditOptions(BaseModel):
    """Düzenleme sırasında opsiyonel ayarlar."""

    require_review: bool = Field(
        default=False,
        description="True ise YAML'e yazılmaz, pending bir proposal oluşturulur.",
    )
    git_mode: Optional[str] = Field(
        default=None,
        pattern="^(direct_commit|pr)$",
        description="Override — yoksa DSL_GIT_MODE env değeri kullanılır.",
    )
    commit_message: Optional[str] = Field(default=None, max_length=2000)


class CreateActionRequest(BaseModel):
    action: dict[str, Any]
    options: EditOptions = Field(default_factory=EditOptions)


class UpdateActionRequest(BaseModel):
    action: dict[str, Any]
    options: EditOptions = Field(default_factory=EditOptions)


class DeleteActionRequest(BaseModel):
    options: EditOptions = Field(default_factory=EditOptions)


class DeprecateActionRequest(BaseModel):
    replacement: str = Field(..., min_length=1, max_length=128)
    reason: Optional[str] = Field(default=None, max_length=500)
    since: Optional[str] = Field(
        default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    options: EditOptions = Field(default_factory=EditOptions)


class ApplyResponse(BaseModel):
    proposal_id: str
    status: str           # "pending" | "merged" | "error"
    mode: str             # "direct_commit" | "pr" | "disabled" | "review"
    action_id: str
    commit_sha: Optional[str] = None
    branch: Optional[str] = None
    pr_url: Optional[str] = None
    file_paths: List[str] = Field(default_factory=list)


class ProposalOut(BaseModel):
    id: str
    action_id: str
    proposer_kind: str
    operation: str
    status: str
    diff: dict[str, Any]
    ai_reasoning: Optional[str] = None
    base_commit_sha: Optional[str] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    pr_url: Optional[str] = None
    error_message: Optional[str] = None
    reviewer_note: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None


class ProposalListResponse(BaseModel):
    items: List[ProposalOut]
    total: int


class ReviewRequest(BaseModel):
    note: Optional[str] = Field(default=None, max_length=2000)
    git_mode: Optional[str] = Field(
        default=None, pattern="^(direct_commit|pr)$"
    )


class AuditOut(BaseModel):
    id: str
    action_id: str
    operation: str
    commit_sha: Optional[str] = None
    pr_url: Optional[str] = None
    created_at: datetime
    proposal_id: Optional[str] = None


class EditorConfigOut(BaseModel):
    git_enabled: bool
    git_mode: str
    base_branch: str
    provider: str
    remote: str
    strict_clean: bool


class AiAliasRequest(BaseModel):
    lang: str = Field(..., pattern="^(tr|en)$")
    count: int = Field(default=3, ge=1, le=10)


class AiAliasResponse(BaseModel):
    accepted: List[str]
    rejected: List[str]
    proposals: List[str] = Field(default_factory=list)
    lang: Optional[str] = None
    action_id: Optional[str] = None
    reason: Optional[str] = None


# ── Yardımcı: service hatalarını HTTP'e çevir ──────────────────────────────


def _http_from_editor_error(exc: EditorError) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(
        status_code=400,
        detail={"message": str(exc), "details": getattr(exc, "details", None)},
    )


def _to_out(result: ApplyResult) -> ApplyResponse:
    return ApplyResponse(
        proposal_id=result.proposal_id,
        status=result.status,
        mode=result.mode,
        action_id=result.action_id,
        commit_sha=result.commit_sha,
        branch=result.branch,
        pr_url=result.pr_url,
        file_paths=result.file_paths,
    )


def _proposal_to_out(p: DslEditProposal) -> ProposalOut:
    return ProposalOut(
        id=p.id,
        action_id=p.action_id,
        proposer_kind=p.proposer_kind,
        operation=p.operation,
        status=p.status,
        diff=p.diff or {},
        ai_reasoning=p.ai_reasoning,
        base_commit_sha=p.base_commit_sha,
        branch=p.branch,
        commit_sha=p.commit_sha,
        pr_url=p.pr_url,
        error_message=p.error_message,
        reviewer_note=p.reviewer_note,
        created_at=p.created_at,
        reviewed_at=p.reviewed_at,
    )


def _audit_to_out(a: DslCatalogAudit) -> AuditOut:
    return AuditOut(
        id=a.id,
        action_id=a.action_id,
        operation=a.operation,
        commit_sha=a.commit_sha,
        pr_url=a.pr_url,
        created_at=a.created_at,
        proposal_id=a.proposal_id,
    )


# ── CRUD endpoint'leri ─────────────────────────────────────────────────────


@router.post("/actions", response_model=ApplyResponse, status_code=status.HTTP_201_CREATED)
def create_action(
    body: CreateActionRequest,
    db: DbSession,
    actor: EditorUser,
) -> ApplyResponse:
    """Yeni bir DSL cümleciği oluştur."""
    action_id = body.action.get("id")
    if not isinstance(action_id, str) or not action_id.strip():
        raise HTTPException(status_code=400, detail="action.id zorunlu")
    try:
        result = editor_service.apply_edit(
            db,
            operation="create",
            payload=body.action,
            action_id=action_id,
            actor=actor,
            require_review=body.options.require_review,
            git_mode=body.options.git_mode,
            commit_message=body.options.commit_message,
        )
    except EditorError as exc:
        raise _http_from_editor_error(exc) from exc
    return _to_out(result)


@router.patch("/actions/{action_id}", response_model=ApplyResponse)
def update_action(
    action_id: str,
    body: UpdateActionRequest,
    db: DbSession,
    actor: EditorUser,
) -> ApplyResponse:
    try:
        result = editor_service.apply_edit(
            db,
            operation="update",
            payload=body.action,
            action_id=action_id,
            actor=actor,
            require_review=body.options.require_review,
            git_mode=body.options.git_mode,
            commit_message=body.options.commit_message,
        )
    except EditorError as exc:
        raise _http_from_editor_error(exc) from exc
    return _to_out(result)


@router.delete("/actions/{action_id}", response_model=ApplyResponse)
def delete_action(
    action_id: str,
    db: DbSession,
    actor: EditorUser,
    body: Optional[DeleteActionRequest] = None,
) -> ApplyResponse:
    options = body.options if body else EditOptions()
    try:
        result = editor_service.apply_edit(
            db,
            operation="delete",
            payload=None,
            action_id=action_id,
            actor=actor,
            require_review=options.require_review,
            git_mode=options.git_mode,
            commit_message=options.commit_message,
        )
    except EditorError as exc:
        raise _http_from_editor_error(exc) from exc
    return _to_out(result)


@router.post("/actions/{action_id}/deprecate", response_model=ApplyResponse)
def deprecate_action(
    action_id: str,
    body: DeprecateActionRequest,
    db: DbSession,
    actor: EditorUser,
) -> ApplyResponse:
    """Bir cümleciği deprecated olarak işaretle (replacement zorunlu)."""
    current = editor_service._current_action_raw(action_id)  # type: ignore[attr-defined]
    if current is None:
        raise HTTPException(status_code=404, detail=f"Action bulunamadı: {action_id}")
    updated = dict(current)
    updated["deprecated"] = {
        "replacement": body.replacement,
        **({"reason": body.reason} if body.reason else {}),
        **({"since": body.since} if body.since else {}),
    }
    try:
        result = editor_service.apply_edit(
            db,
            operation="deprecate",
            payload=updated,
            action_id=action_id,
            actor=actor,
            require_review=body.options.require_review,
            git_mode=body.options.git_mode,
            commit_message=body.options.commit_message,
        )
    except EditorError as exc:
        raise _http_from_editor_error(exc) from exc
    return _to_out(result)


# ── Proposal inceleme ──────────────────────────────────────────────────────


@router.get("/proposals", response_model=ProposalListResponse)
def list_proposals(
    _: ReaderUser,
    db: DbSession,
    status_q: Optional[str] = Query(
        default=None,
        alias="status",
        pattern="^(pending|approved|rejected|merged|error)$",
    ),
    action_id: Optional[str] = Query(default=None, max_length=128),
    limit: int = Query(default=50, ge=1, le=200),
) -> ProposalListResponse:
    items = editor_service.list_proposals(
        db, status=status_q, action_id=action_id, limit=limit
    )
    return ProposalListResponse(
        items=[_proposal_to_out(p) for p in items],
        total=len(items),
    )


@router.get("/proposals/{proposal_id}", response_model=ProposalOut)
def get_proposal(
    proposal_id: str,
    _: ReaderUser,
    db: DbSession,
) -> ProposalOut:
    try:
        prop = editor_service.get_proposal(db, proposal_id)
    except EditorError as exc:
        raise _http_from_editor_error(exc) from exc
    return _proposal_to_out(prop)


@router.post("/proposals/{proposal_id}/approve", response_model=ApplyResponse)
def approve_proposal(
    proposal_id: str,
    body: ReviewRequest,
    db: DbSession,
    actor: ApproverUser,
) -> ApplyResponse:
    try:
        result = editor_service.approve_proposal(
            db,
            proposal_id=proposal_id,
            actor=actor,
            note=body.note,
            git_mode=body.git_mode,
        )
    except EditorError as exc:
        raise _http_from_editor_error(exc) from exc
    return _to_out(result)


@router.post("/proposals/{proposal_id}/reject", response_model=ProposalOut)
def reject_proposal(
    proposal_id: str,
    body: ReviewRequest,
    db: DbSession,
    actor: ApproverUser,
) -> ProposalOut:
    try:
        prop = editor_service.reject_proposal(
            db, proposal_id=proposal_id, actor=actor, note=body.note
        )
    except EditorError as exc:
        raise _http_from_editor_error(exc) from exc
    return _proposal_to_out(prop)


# ── Audit + config ─────────────────────────────────────────────────────────


@router.get("/audit", response_model=List[AuditOut])
def list_audit(
    _: ReaderUser,
    db: DbSession,
    action_id: Optional[str] = Query(default=None, max_length=128),
    limit: int = Query(default=100, ge=1, le=500),
) -> List[AuditOut]:
    items = editor_service.list_audit(db, action_id=action_id, limit=limit)
    return [_audit_to_out(a) for a in items]


@router.post(
    "/actions/{action_id}/ai-aliases",
    response_model=AiAliasResponse,
)
def generate_ai_aliases(
    action_id: str,
    body: AiAliasRequest,
    db: DbSession,
    actor: EditorUser,
) -> AiAliasResponse:
    """Mevcut cümleciğe AI ile yeni TR/EN alias önerileri üret.

    Sonuç doğrudan YAML'e yazılmaz — her kabul edilen aday `pending`
    proposal olarak kaydedilir ve admin `/dsl-catalog/review` sayfasında
    onayladığında katalog'a eklenir.
    """
    try:
        result = ai_assist.generate_aliases(
            db,
            action_id=action_id,
            lang=body.lang,
            count=body.count,
            actor=actor,
        )
    except EditorError as exc:
        raise _http_from_editor_error(exc) from exc
    return AiAliasResponse(
        accepted=result.get("accepted", []),
        rejected=result.get("rejected", []),
        proposals=result.get("proposals", []),
        lang=result.get("lang"),
        action_id=result.get("action_id"),
        reason=result.get("reason"),
    )


@router.get("/editor/config", response_model=EditorConfigOut)
def editor_config(_: ReaderUser) -> EditorConfigOut:
    """Frontend'in git akışını doğru göstermesi için aktif ayarlar."""
    cfg = GitConfig.from_env()
    return EditorConfigOut(
        git_enabled=cfg.enabled,
        git_mode=cfg.mode,
        base_branch=cfg.base_branch,
        provider=cfg.provider,
        remote=cfg.remote,
        strict_clean=cfg.strict_clean,
    )
