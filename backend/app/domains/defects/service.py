"""Defect feedback loop — closing the analyze→automate chain.

State machine:
  open → awaiting_fix → fix_merged → verifying → verified | rejected → closed

İlk MVP'de Jira/GitHub Issues entegrasyonu mocked (external_ref + external_url
alanları + integration_service üzerinden gerçekleştirilebilir).
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

try:
    from app.core.event_bus import bus as _bus, DomainEvent as _DomainEvent
except Exception:  # pragma: no cover
    _bus = None
    _DomainEvent = None  # type: ignore


DefectStatus = Literal[
    "open", "awaiting_fix", "fix_merged", "verifying", "verified", "rejected", "closed"
]
Severity = Literal["critical", "major", "minor", "trivial"]


@dataclass
class DefectTicket:
    id: str
    project_id: str
    title: str
    description: str
    status: DefectStatus = "open"
    severity: Severity = "major"
    scenario_id: Optional[str] = None
    execution_id: Optional[str] = None
    failure_signature: Optional[str] = None  # dedupe için (error_class + locator)
    external_ref: Optional[str] = None  # Jira key, GitHub issue #
    external_url: Optional[str] = None
    fix_commit: Optional[str] = None
    rerun_id: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    def transition(self, new_status: DefectStatus, *, note: str = "", actor: str = "system") -> None:
        self.history.append({
            "from": self.status,
            "to": new_status,
            "ts": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "note": note,
        })
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc).isoformat()


_STORE: Dict[str, DefectTicket] = {}
# failure_signature -> defect_id (dedupe)
_SIGNATURE_INDEX: Dict[str, str] = {}


def _new_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_urlsafe(8)}"


def _publish(name: str, defect: DefectTicket, extra: Optional[Dict[str, Any]] = None) -> None:
    if _bus is None or _DomainEvent is None:
        return
    payload = {"defect_id": defect.id, "status": defect.status, "severity": defect.severity}
    if defect.external_ref:
        payload["external_ref"] = defect.external_ref
    if extra:
        payload.update(extra)
    try:
        _bus.publish(_DomainEvent(name=name, payload=payload, project_id=defect.project_id))
    except Exception:
        pass


# ── Public API ─────────────────────────────────────────────────────────────

def _build_signature(scenario_id: Optional[str], error_class: str, locator: str) -> str:
    return f"{scenario_id or '-'}::{error_class}::{locator}"


def open_defect_from_execution(
    *,
    project_id: str,
    title: str,
    description: str,
    scenario_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    severity: Severity = "major",
    error_class: str = "AssertionError",
    locator: str = "",
    auto_jira: bool = False,
) -> DefectTicket:
    """Failed test'ten defect aç. Aynı imza varsa mevcut ticket'a ekle."""
    sig = _build_signature(scenario_id, error_class, locator)
    if sig in _SIGNATURE_INDEX:
        existing = _STORE.get(_SIGNATURE_INDEX[sig])
        if existing and existing.status not in ("closed", "verified"):
            existing.history.append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "actor": "system",
                "note": f"Tekrar tetiklendi (execution={execution_id})",
            })
            existing.updated_at = datetime.now(timezone.utc).isoformat()
            _publish("defect.recurred", existing)
            return existing

    did = _new_id("def")
    defect = DefectTicket(
        id=did,
        project_id=project_id,
        title=title,
        description=description,
        status="open",
        severity=severity,
        scenario_id=scenario_id,
        execution_id=execution_id,
        failure_signature=sig,
    )
    _STORE[did] = defect
    _SIGNATURE_INDEX[sig] = did

    if auto_jira:
        # Mock Jira creation — production'da integration_service.create_jira_issue()
        defect.external_ref = f"NEUREX-{secrets.randbelow(9000) + 1000}"
        defect.external_url = f"https://jira.example.com/browse/{defect.external_ref}"

    defect.transition("awaiting_fix", note="Auto-created from failed execution", actor="system")
    _publish("defect.opened", defect, extra={"scenario_id": scenario_id, "execution_id": execution_id})
    return defect


def mark_fix_merged(defect_id: str, commit_sha: str, *, actor: str = "ci") -> DefectTicket:
    """Fix merge edildi — auto re-run tetiklenir."""
    defect = _STORE.get(defect_id)
    if defect is None:
        raise ValueError(f"Defect bulunamadı: {defect_id}")
    if defect.status in ("closed", "verified"):
        return defect
    defect.fix_commit = commit_sha
    defect.transition("fix_merged", note=f"Commit: {commit_sha[:12]}", actor=actor)
    _publish("defect.fix.requested", defect, extra={"commit": commit_sha})
    defect.transition("verifying", note="Re-run kuyruğa alındı", actor="system")
    return defect


def verify_and_close(
    defect_id: str,
    *,
    rerun_id: str,
    rerun_passed: bool,
    actor: str = "system",
) -> DefectTicket:
    """Re-run sonucuyla defect kapanır veya reddedilir."""
    defect = _STORE.get(defect_id)
    if defect is None:
        raise ValueError(f"Defect bulunamadı: {defect_id}")
    defect.rerun_id = rerun_id
    if rerun_passed:
        defect.transition("verified", note=f"Rerun {rerun_id} passed", actor=actor)
        _publish("defect.verified", defect, extra={"rerun_id": rerun_id})
        defect.transition("closed", note="Auto-closed", actor="system")
        _publish("defect.closed", defect, extra={"rerun_id": rerun_id})
        # Signature index'i temizle ki aynı bug tekrar çıkarsa yeni ticket açılsın
        if defect.failure_signature and _SIGNATURE_INDEX.get(defect.failure_signature) == defect.id:
            del _SIGNATURE_INDEX[defect.failure_signature]
    else:
        defect.transition("rejected", note=f"Rerun {rerun_id} still failing", actor=actor)
        _publish("defect.rejected", defect, extra={"rerun_id": rerun_id})
        # Revert to awaiting_fix so loop continues
        defect.transition("awaiting_fix", note="Tekrar düzeltme bekleniyor", actor="system")
    return defect


def list_defects(
    project_id: Optional[str] = None,
    status: Optional[DefectStatus] = None,
) -> List[DefectTicket]:
    items = list(_STORE.values())
    if project_id:
        items = [d for d in items if d.project_id == project_id]
    if status:
        items = [d for d in items if d.status == status]
    items.sort(key=lambda d: d.updated_at, reverse=True)
    return items


def get_defect(defect_id: str) -> Optional[DefectTicket]:
    return _STORE.get(defect_id)


def clear() -> None:
    """Test helper."""
    _STORE.clear()
    _SIGNATURE_INDEX.clear()


# ── Event listeners — loop'u kendiliğinden döndüren tetikleyiciler ────────

_LISTENERS_INSTALLED = False


def install_listeners() -> None:
    """Event bus'a otomatik defect-açma + auto-close listener'ları bağlar.

    Idempotent — sadece bir kez bağlar.
    """
    global _LISTENERS_INSTALLED
    if _LISTENERS_INSTALLED or _bus is None:
        return

    def _on_execution_failed(evt) -> None:
        p = evt.payload or {}
        try:
            open_defect_from_execution(
                project_id=evt.project_id or p.get("project_id", "unknown"),
                title=p.get("title") or f"Execution failed: {p.get('execution_id', '')}",
                description=p.get("error") or "Otomatik açıldı (execution.failed)",
                scenario_id=p.get("scenario_id"),
                execution_id=p.get("execution_id"),
                severity=p.get("severity", "major"),
                error_class=p.get("error_class", "AssertionError"),
                locator=p.get("locator", ""),
                auto_jira=bool(p.get("auto_jira", False)),
            )
        except Exception:
            pass

    def _on_rerun_passed(evt) -> None:
        p = evt.payload or {}
        defect_id = p.get("defect_id")
        rerun_id = p.get("rerun_id") or p.get("execution_id") or "unknown"
        if defect_id:
            try:
                verify_and_close(defect_id, rerun_id=rerun_id, rerun_passed=True)
            except Exception:
                pass

    _bus.subscribe("execution.failed", _on_execution_failed)
    _bus.subscribe("scenario.rerun.passed", _on_rerun_passed)
    _LISTENERS_INSTALLED = True
