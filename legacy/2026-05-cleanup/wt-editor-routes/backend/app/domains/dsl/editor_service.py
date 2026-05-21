"""DSL sözlüğü düzenleme iş mantığı.

Sorumluluklar:
    * Action payload'unu doğrula (JSON Schema ile)
    * YAML yazıcıya CRUD operasyonları yönlendir
    * `DslEditProposal` kaydı oluştur / onayla / reddet
    * Git client ile commit/PR aşamasını orkestra et
    * Başarılı merge'lerde `DslCatalogAudit` izini bırak
    * Loader cache'ini ve semantic index'i tetikle

Bu modül HTTP katmanını bilmez; router sadece fonksiyonlara çağırır.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

import jsonschema  # type: ignore[import-untyped]

from app.domains.dsl import yaml_writer
from app.domains.dsl.embedding_index import alias_index
from app.domains.dsl.loader import catalog_cache
from app.domains.dsl.schemas import DslAction
from app.infra import git_client
from app.infra.git_client import CommitResult, GitClientError, GitConfig
from app.infra.models import DslCatalogAudit, DslEditProposal, User

logger = logging.getLogger(__name__)

# ── JSON Schema (packages/dsl/schema/action.schema.json) ────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_SCHEMA_PATH = _PROJECT_ROOT / "packages" / "dsl" / "schema" / "action.schema.json"

_schema_cache: Optional[dict[str, Any]] = None
_schema_lock = threading.Lock()


def _load_schema() -> dict[str, Any]:
    global _schema_cache
    with _schema_lock:
        if _schema_cache is not None:
            return _schema_cache
        if not _SCHEMA_PATH.exists():
            raise FileNotFoundError(
                f"DSL schema dosyası bulunamadı: {_SCHEMA_PATH}"
            )
        with _SCHEMA_PATH.open("r", encoding="utf-8") as f:
            _schema_cache = json.load(f)
        return _schema_cache


# ── Hata türleri ────────────────────────────────────────────────────────────


class EditorError(ValueError):
    """Doğrulama / iş kuralı hatası. Router 400/409 olarak çevirir."""

    def __init__(self, message: str, *, details: Any = None):
        super().__init__(message)
        self.details = details


class NotFoundError(EditorError):
    pass


class ConflictError(EditorError):
    pass


# ── Doğrulama ───────────────────────────────────────────────────────────────


def validate_action_payload(payload: dict[str, Any]) -> None:
    """JSON Schema'ya göre doğrula. Hata varsa `EditorError` yükseltir."""
    schema = _load_schema()
    try:
        jsonschema.validate(payload, schema)
    except jsonschema.ValidationError as exc:
        raise EditorError(
            f"Şema doğrulaması başarısız: {exc.message}",
            details={
                "path": list(exc.absolute_path),
                "validator": exc.validator,
                "schema_path": list(exc.schema_path),
            },
        ) from exc


# ── Diff üretimi ────────────────────────────────────────────────────────────


def compute_diff(
    before: Optional[dict[str, Any]], after: Optional[dict[str, Any]]
) -> dict[str, Any]:
    """(before, after) → alan seviyesi diff.

    `changed_fields`: hangi top-level alanlar değişti — UI'da vurgulamak için.
    """
    b = before or {}
    a = after or {}
    changed: list[str] = []
    for key in set(b.keys()) | set(a.keys()):
        if b.get(key) != a.get(key):
            changed.append(key)
    op = (
        "create"
        if before is None
        else "delete"
        if after is None
        else "update"
    )
    return {
        "op": op,
        "before": b or None,
        "after": a or None,
        "changed_fields": sorted(changed),
    }


# ── Ana akış ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ApplyResult:
    proposal_id: str
    status: str
    commit_sha: Optional[str]
    branch: Optional[str]
    pr_url: Optional[str]
    file_paths: list[str]
    action_id: str
    mode: str  # "direct_commit" | "pr" | "disabled"


def _strip_source_yaml(raw: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in raw.items() if k != "source_yaml"}


def _current_action_raw(action_id: str) -> Optional[dict[str, Any]]:
    action = catalog_cache.get(action_id)
    if action is None:
        return None
    return _strip_source_yaml(action.model_dump(mode="json", exclude_none=True))


def _write_yaml_for_op(
    operation: str, payload_after: Optional[dict[str, Any]], action_id: str
) -> list[Path]:
    """YAML'e yaz ve etkilenen dosya yollarını döner."""
    if operation in {"create", "update", "deprecate"}:
        if payload_after is None:
            raise EditorError(f"{operation} için after payload zorunlu")
        yaml_writer.upsert_action(payload_after)
    elif operation == "delete":
        deleted = yaml_writer.delete_action(action_id)
        if deleted is None:
            raise NotFoundError(f"Silinecek action bulunamadı: {action_id}")
    else:
        raise EditorError(f"Bilinmeyen operasyon: {operation}")

    # Etkilenen dosyalar: yeni kategori + (varsa) eski kategori
    category = (payload_after or {}).get("category")
    return yaml_writer.files_touched_by_action(action_id, new_category=category)


def _commit_message(operation: str, action_id: str, actor: User | None) -> str:
    who = actor.email if actor and getattr(actor, "email", None) else "unknown"
    verb = {
        "create": "add",
        "update": "update",
        "delete": "remove",
        "deprecate": "deprecate",
    }.get(operation, operation)
    return (
        f"dsl: {verb} {action_id} (via UI)\n\n"
        f"Change-Proposed-By: {who}\n"
        "Auto-generated from DSL editor. Review carefully before merge.\n"
    )


def _reload_catalog_and_index() -> None:
    """YAML yazıldıktan sonra cache'i ve embedding index'i tazele."""
    try:
        catalog_cache.load()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Catalog reload başarısız: %s", exc)
    try:
        # Thread kullan — gateway yavaş olabilir
        threading.Thread(
            target=lambda: alias_index.rebuild(),
            name="dsl-embed-rebuild-post-edit",
            daemon=True,
        ).start()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Index rebuild tetiklenemedi: %s", exc)


def _record_proposal(
    db: Session,
    *,
    action_id: str,
    operation: str,
    diff: dict[str, Any],
    actor: User | None,
    proposer_kind: str = "human",
    ai_reasoning: Optional[str] = None,
    status: str = "pending",
) -> DslEditProposal:
    proposal = DslEditProposal(
        id=str(uuid.uuid4()),
        action_id=action_id,
        proposer_id=getattr(actor, "id", None),
        proposer_kind=proposer_kind,
        operation=operation,
        status=status,
        diff=diff,
        ai_reasoning=ai_reasoning,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


def _record_audit(
    db: Session,
    *,
    proposal: DslEditProposal,
    commit_sha: Optional[str],
    pr_url: Optional[str],
) -> None:
    entry = DslCatalogAudit(
        action_id=proposal.action_id,
        operation=proposal.operation,
        actor_id=proposal.reviewer_id or proposal.proposer_id,
        proposal_id=proposal.id,
        commit_sha=commit_sha,
        pr_url=pr_url,
        diff=proposal.diff,
    )
    db.add(entry)


# ── Publika API ────────────────────────────────────────────────────────────


def apply_edit(
    db: Session,
    *,
    operation: str,
    payload: Optional[dict[str, Any]],
    action_id: str,
    actor: User,
    require_review: bool = False,
    git_mode: Optional[str] = None,
    commit_message: Optional[str] = None,
) -> ApplyResult:
    """DSL düzenlemesini uygula.

    Akış:
      1. `before` = mevcut katalog snapshot'ı (varsa)
      2. Payload'ı doğrula (create/update)
      3. Proposal kaydı (`pending` veya direkt `merged`)
      4. `require_review=True` ise YAML'e yazmadan döner (admin onaylayacak)
      5. YAML'e yaz → catalog reload → git commit/PR
      6. Audit kaydı + proposal status güncellemesi
    """
    cfg = GitConfig.from_env()
    operation = operation.lower()
    effective_mode = (git_mode or cfg.mode).lower()

    if operation not in {"create", "update", "delete", "deprecate"}:
        raise EditorError(f"Bilinmeyen operasyon: {operation}")

    before = _current_action_raw(action_id)
    if operation == "create" and before is not None:
        raise ConflictError(
            f"'{action_id}' zaten mevcut — güncelleme mi yapmak istiyordunuz?"
        )
    if operation != "create" and before is None:
        raise NotFoundError(f"Action bulunamadı: {action_id}")

    after: Optional[dict[str, Any]]
    if operation == "delete":
        after = None
    else:
        if not payload:
            raise EditorError("payload zorunlu")
        payload = _strip_source_yaml(dict(payload))
        # Tutarlılık — payload.id ile path id uyuşmalı
        if payload.get("id") and payload["id"] != action_id:
            raise EditorError(
                f"payload.id ({payload['id']}) ile URL id ({action_id}) uyuşmuyor"
            )
        payload["id"] = action_id
        if operation == "deprecate":
            # Deprecate = update, ama mutlaka deprecated alanı olmalı
            if not payload.get("deprecated"):
                raise EditorError(
                    "deprecate operasyonu için payload.deprecated gerekli"
                )
        # deprecated default ise oluşan kaydın bozulmaması için sıkı şema
        validate_action_payload(payload)
        after = payload

    diff = compute_diff(before, after)

    # Review modunda YAML'e yazma — sadece proposal oluştur
    if require_review:
        proposal = _record_proposal(
            db,
            action_id=action_id,
            operation=operation,
            diff=diff,
            actor=actor,
            status="pending",
        )
        return ApplyResult(
            proposal_id=proposal.id,
            status="pending",
            commit_sha=None,
            branch=None,
            pr_url=None,
            file_paths=[],
            action_id=action_id,
            mode="review",
        )

    # Doğrudan uygulama — önce YAML, sonra git
    try:
        base_sha = git_client.head_sha(cfg) if cfg.enabled else None
    except GitClientError:
        base_sha = None

    proposal = _record_proposal(
        db,
        action_id=action_id,
        operation=operation,
        diff=diff,
        actor=actor,
        status="approved",
    )
    proposal.base_commit_sha = base_sha
    db.commit()

    file_paths: list[Path] = []
    commit_result: CommitResult = CommitResult(sha="", branch="", pushed=False)
    try:
        file_paths = _write_yaml_for_op(operation, after, action_id)
        _reload_catalog_and_index()

        if cfg.enabled and file_paths:
            msg = commit_message or _commit_message(operation, action_id, actor)
            commit_result = git_client.commit_dsl_change(
                cfg,
                paths=file_paths,
                message=msg,
                proposal_id=proposal.id,
                slug=f"{operation}-{action_id}",
                mode=effective_mode,
            )
    except (GitClientError, EditorError) as exc:
        proposal.status = "error"
        proposal.error_message = str(exc)[:1000]
        db.commit()
        raise
    except Exception as exc:  # noqa: BLE001
        proposal.status = "error"
        proposal.error_message = f"Beklenmeyen hata: {exc}"[:1000]
        db.commit()
        raise EditorError(f"DSL değişikliği uygulanamadı: {exc}") from exc

    # Başarılı
    proposal.status = "merged"
    proposal.branch = commit_result.branch or None
    proposal.commit_sha = commit_result.sha or None
    proposal.pr_url = commit_result.pr_url
    proposal.reviewer_id = getattr(actor, "id", None)
    proposal.reviewed_at = datetime.now(timezone.utc)
    _record_audit(
        db,
        proposal=proposal,
        commit_sha=commit_result.sha or None,
        pr_url=commit_result.pr_url,
    )
    db.commit()

    return ApplyResult(
        proposal_id=proposal.id,
        status="merged",
        commit_sha=commit_result.sha or None,
        branch=commit_result.branch or None,
        pr_url=commit_result.pr_url,
        file_paths=[str(p) for p in file_paths],
        action_id=action_id,
        mode="disabled" if not cfg.enabled else effective_mode,
    )


# ── Proposal yaşam döngüsü ─────────────────────────────────────────────────


def list_proposals(
    db: Session,
    *,
    status: Optional[str] = None,
    action_id: Optional[str] = None,
    limit: int = 50,
) -> list[DslEditProposal]:
    q = select(DslEditProposal).order_by(DslEditProposal.created_at.desc())
    if status:
        q = q.where(DslEditProposal.status == status)
    if action_id:
        q = q.where(DslEditProposal.action_id == action_id)
    q = q.limit(limit)
    return list(db.execute(q).scalars().all())


def get_proposal(db: Session, proposal_id: str) -> DslEditProposal:
    prop = db.get(DslEditProposal, proposal_id)
    if prop is None:
        raise NotFoundError(f"Proposal bulunamadı: {proposal_id}")
    return prop


def approve_proposal(
    db: Session,
    *,
    proposal_id: str,
    actor: User,
    note: Optional[str] = None,
    git_mode: Optional[str] = None,
) -> ApplyResult:
    """Pending önerisini onaylayıp YAML'e + git'e uygula."""
    prop = get_proposal(db, proposal_id)
    if prop.status != "pending":
        raise ConflictError(
            f"Onay için uygun değil (status={prop.status})"
        )

    operation = prop.operation
    after = (prop.diff or {}).get("after")
    # apply_edit'in require_review=False yolunu çağır — ama proposal'ı
    # yeniden oluşturmadan, mevcut satırı finalize ederek.
    cfg = GitConfig.from_env()
    effective_mode = (git_mode or cfg.mode).lower()

    file_paths: list[Path] = []
    commit_result: CommitResult = CommitResult(sha="", branch="", pushed=False)
    try:
        file_paths = _write_yaml_for_op(operation, after, prop.action_id)
        _reload_catalog_and_index()

        if cfg.enabled and file_paths:
            msg = _commit_message(operation, prop.action_id, actor)
            commit_result = git_client.commit_dsl_change(
                cfg,
                paths=file_paths,
                message=msg,
                proposal_id=prop.id,
                slug=f"{operation}-{prop.action_id}",
                mode=effective_mode,
            )
    except (GitClientError, EditorError) as exc:
        prop.status = "error"
        prop.error_message = str(exc)[:1000]
        db.commit()
        raise
    except Exception as exc:  # noqa: BLE001
        prop.status = "error"
        prop.error_message = f"Beklenmeyen hata: {exc}"[:1000]
        db.commit()
        raise EditorError(f"Proposal onaylanamadı: {exc}") from exc

    prop.status = "merged"
    prop.branch = commit_result.branch or None
    prop.commit_sha = commit_result.sha or None
    prop.pr_url = commit_result.pr_url
    prop.reviewer_id = getattr(actor, "id", None)
    prop.reviewer_note = (note or "")[:2000] or None
    prop.reviewed_at = datetime.now(timezone.utc)
    _record_audit(
        db,
        proposal=prop,
        commit_sha=commit_result.sha or None,
        pr_url=commit_result.pr_url,
    )
    db.commit()

    return ApplyResult(
        proposal_id=prop.id,
        status="merged",
        commit_sha=commit_result.sha or None,
        branch=commit_result.branch or None,
        pr_url=commit_result.pr_url,
        file_paths=[str(p) for p in file_paths],
        action_id=prop.action_id,
        mode="disabled" if not cfg.enabled else effective_mode,
    )


def reject_proposal(
    db: Session,
    *,
    proposal_id: str,
    actor: User,
    note: Optional[str] = None,
) -> DslEditProposal:
    prop = get_proposal(db, proposal_id)
    if prop.status != "pending":
        raise ConflictError(f"Reddetme için uygun değil (status={prop.status})")
    prop.status = "rejected"
    prop.reviewer_id = getattr(actor, "id", None)
    prop.reviewer_note = (note or "")[:2000] or None
    prop.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(prop)
    return prop


# ── Audit ──────────────────────────────────────────────────────────────────


def list_audit(
    db: Session, *, action_id: Optional[str] = None, limit: int = 100
) -> list[DslCatalogAudit]:
    q = select(DslCatalogAudit).order_by(DslCatalogAudit.created_at.desc())
    if action_id:
        q = q.where(DslCatalogAudit.action_id == action_id)
    q = q.limit(limit)
    return list(db.execute(q).scalars().all())
