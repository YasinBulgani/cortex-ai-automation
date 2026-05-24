"""Requirement ingestion service.

External source (Jira/Confluence/raw text/file) → IngestedRequirement
→ AcceptanceCriterion[] → "requirement.ingested" event publish.

LLM çağrısı yok; rule-based AC extraction (Türkçe + İngilizce desenler).
LLM eklendiğinde extract_acceptance_criteria() içine plug-in olarak gelir.
"""
from __future__ import annotations

import logging
import re
import secrets

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from app.core.event_bus import bus as _bus, DomainEvent as _DomainEvent
except Exception:  # pragma: no cover
    _bus = None
    _DomainEvent = None  # type: ignore


@dataclass
class AcceptanceCriterion:
    id: str
    text: str
    kind: str = "behavior"  # behavior | constraint | data | error
    source_span: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class IngestedRequirement:
    id: str
    project_id: str
    source: str  # "jira" | "confluence" | "text" | "file"
    source_ref: Optional[str]
    title: str
    body: str
    acceptance_criteria: List[AcceptanceCriterion] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        out = asdict(self)
        out["acceptance_criteria"] = [a.to_dict() for a in self.acceptance_criteria]
        return out


_STORE: Dict[str, IngestedRequirement] = {}


def _new_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_urlsafe(8)}"


# ── AC extraction ──────────────────────────────────────────────────────────

_AC_BULLET_PATTERN = re.compile(r"^[\s]*(?:[-*•·]|\d+[.)])\s+(.+)$", re.MULTILINE)
_GIVEN_WHEN_THEN = re.compile(
    r"(?:verildi[ğg]inde|given|eğer|when|o zaman|then|şu durumda)\s+([^.\n]+)",
    re.IGNORECASE,
)
_TURKISH_SHALL = re.compile(
    r"(?:kullanıcı|sistem|uygulama)\s+([^.\n]+?(?:meli|malı|yapmalı|edebilmeli|görmeli|göstermeli))",
    re.IGNORECASE,
)


def extract_acceptance_criteria(text: str) -> List[AcceptanceCriterion]:
    """Metinden acceptance criteria çıkarır.

    Strateji: bullet/numbered list + Given-When-Then + Türkçe "...meli/malı" cümleleri.
    Üç havuz birleştirilir, dedupe'lanır.
    """
    candidates: list[tuple[str, str]] = []  # (text, kind)

    for m in _AC_BULLET_PATTERN.finditer(text):
        t = m.group(1).strip()
        if 8 <= len(t) <= 240:
            candidates.append((t, "behavior"))

    for m in _GIVEN_WHEN_THEN.finditer(text):
        t = m.group(0).strip()
        if 8 <= len(t) <= 240:
            candidates.append((t, "behavior"))

    for m in _TURKISH_SHALL.finditer(text):
        t = m.group(0).strip()
        if 8 <= len(t) <= 240:
            candidates.append((t, "behavior"))

    # Dedupe — text normalize
    seen: set[str] = set()
    out: List[AcceptanceCriterion] = []
    for txt, kind in candidates:
        key = re.sub(r"\s+", " ", txt.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        ac_id = "ac-" + secrets.token_urlsafe(6)
        # Kind heuristic
        low = txt.lower()
        if any(w in low for w in ("hata", "error", "fail", "exception", "geçersiz")):
            kind = "error"
        elif any(w in low for w in ("veri", "data", "alan", "format")):
            kind = "data"
        elif any(w in low for w in ("zorunlu", "must", "shall", "gerek", "sınır", "limit", "maks", "min")):
            kind = "constraint"
        out.append(AcceptanceCriterion(id=ac_id, text=txt, kind=kind, source_span=txt[:80]))
    return out


def _publish_ingested(req: IngestedRequirement) -> None:
    if _bus is None or _DomainEvent is None:
        return
    try:
        _bus.publish(_DomainEvent(
            name="requirement.ingested",
            payload={
                "requirement_id": req.id,
                "source": req.source,
                "source_ref": req.source_ref,
                "title": req.title,
                "ac_count": len(req.acceptance_criteria),
            },
            project_id=req.project_id,
        ))
    except Exception as _exc:
        logger.warning("requirement.ingested event publish edilemedi: %s", _exc)


# ── Public API ─────────────────────────────────────────────────────────────

def ingest_text(
    *,
    project_id: str,
    title: str,
    body: str,
    source: str = "text",
    source_ref: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> IngestedRequirement:
    if not body.strip():
        raise ValueError("body boş olamaz")
    rid = _new_id("req")
    req = IngestedRequirement(
        id=rid,
        project_id=project_id,
        source=source,
        source_ref=source_ref,
        title=title.strip() or "Untitled",
        body=body.strip(),
        acceptance_criteria=extract_acceptance_criteria(body),
        extra=extra or {},
    )
    _STORE[rid] = req
    _publish_ingested(req)
    return req


def ingest_jira_payload(project_id: str, payload: Dict[str, Any]) -> IngestedRequirement:
    """Jira webhook payload formatı.

    Beklenen şekil (sadeleştirilmiş):
      { "issue": { "key": "NEUREX-123",
                   "fields": { "summary": "...", "description": "..." } } }
    """
    issue = payload.get("issue") or payload  # bazen direkt issue gelir
    fields = issue.get("fields") or {}
    key = issue.get("key") or fields.get("key") or "JIRA-UNKNOWN"
    title = fields.get("summary") or key
    body_raw = fields.get("description") or ""
    # Jira ADF (Atlassian Document Format) — kaba düzleştirme
    if isinstance(body_raw, dict):
        body = _flatten_adf(body_raw)
    else:
        body = str(body_raw)
    return ingest_text(
        project_id=project_id,
        title=title,
        body=body or title,
        source="jira",
        source_ref=key,
        extra={"jira_key": key, "issue_type": (fields.get("issuetype") or {}).get("name")},
    )


def ingest_confluence_payload(project_id: str, payload: Dict[str, Any]) -> IngestedRequirement:
    page = payload.get("page") or payload
    page_id = page.get("id") or page.get("page_id") or "CONF-UNKNOWN"
    title = page.get("title") or f"Confluence-{page_id}"
    body = page.get("body") or page.get("content") or ""
    if isinstance(body, dict):
        body = body.get("storage", {}).get("value", "") or body.get("plain", "") or ""
    body = _strip_html(str(body))
    return ingest_text(
        project_id=project_id,
        title=title,
        body=body or title,
        source="confluence",
        source_ref=str(page_id),
        extra={"page_id": str(page_id), "space": page.get("space")},
    )


def list_ingested(project_id: Optional[str] = None) -> List[IngestedRequirement]:
    items = list(_STORE.values())
    if project_id:
        items = [i for i in items if i.project_id == project_id]
    items.sort(key=lambda i: i.created_at, reverse=True)
    return items


def get_ingested(req_id: str) -> Optional[IngestedRequirement]:
    return _STORE.get(req_id)


def clear() -> None:
    """Test helper."""
    _STORE.clear()


# ── Helpers ────────────────────────────────────────────────────────────────

def _flatten_adf(node: Any) -> str:
    """Jira ADF (Atlassian Document Format) ağacını düz metne çevirir."""
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        if node.get("type") == "text":
            return str(node.get("text", ""))
        parts = []
        for child in node.get("content", []) or []:
            parts.append(_flatten_adf(child))
        sep = "\n" if node.get("type") in ("paragraph", "bulletList", "orderedList", "heading") else " "
        return sep.join(p for p in parts if p)
    if isinstance(node, list):
        return "\n".join(_flatten_adf(c) for c in node)
    return ""


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", " ", s).replace("&nbsp;", " ").strip()
