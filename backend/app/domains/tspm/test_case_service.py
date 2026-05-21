"""
Nexus QA — Faz 3: AI Test Case Generation Service
AI Gateway üzerinden toplu test case üretir, DB'ye kaydeder,
bulk approve/reject/edit + scenaryo dönüşümü sağlar.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.domains.ai.gateway_client import gateway_complete, gateway_is_available
from app.domains.tspm.models import TspmAiBatch, TspmScenario, TspmTestCase, utcnow
from app.domains.tspm.schemas import (
    AiBatchOut,
    BulkReviewRequest,
    GenerateTestCasesRequest,
    GenerateTestCasesResponse,
    TestCaseOut,
    TestCaseReviewAction,
    TestCaseUpdate,
)

logger = logging.getLogger("nexusqa.test_case_service")

# ── Helpers ──────────────────────────────────────────────────────────────────

def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` markdown fences."""
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE).strip()


def _parse_test_cases_json(raw: str) -> list[dict[str, Any]]:
    """Parse AI response → list[dict]. Handles various wrapping patterns."""
    text = _strip_fences(raw)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for key in ("test_cases", "testCases", "cases", "scenarios", "tests"):
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key]
        return []
    except json.JSONDecodeError:
        logger.warning("JSON parse failed for AI test case response, attempting extraction")
        # Try to extract JSON array from within the text
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        return []


def _build_prompt_for_modules(
    analysis_text: str,
    modules: list[dict[str, Any]],
    extra_instructions: str = "",
) -> str:
    """Build the user message for AI test case generation."""
    module_summary = ""
    if modules:
        module_lines = []
        for m in modules[:10]:  # limit to 10 modules per request
            name = m.get("module_name", m.get("name", "?"))
            risk = m.get("risk_level", "medium")
            est = m.get("estimated_tests", 3)
            module_lines.append(f"  - {name} (risk: {risk}, tahmini test: {est})")
        module_summary = "\n\nTespit Edilen Modüller:\n" + "\n".join(module_lines)

    extra = f"\n\nEk Talimatlar: {extra_instructions}" if extra_instructions.strip() else ""

    return f"""Aşağıdaki sistem/uygulama dokümantasyonunu analiz ederek kapsamlı test case'leri üret.

Doküman Analizi:
{analysis_text[:6000]}{module_summary}{extra}

Her test case için şu JSON formatını kullan:
{{
  "title": "Test case başlığı",
  "description": "Kısa açıklama",
  "module_name": "Modül adı",
  "feature_area": "Özellik alanı",
  "test_type": "functional|regression|smoke|edge_case|negative",
  "priority": "critical|high|medium|low",
  "risk_level": "high|medium|low",
  "preconditions": ["Ön koşul 1", "Ön koşul 2"],
  "steps": [
    {{"order": 1, "action": "Kullanıcı X yapar", "expected": "Sistem Y gösterir"}},
    {{"order": 2, "action": "...", "expected": "..."}}
  ],
  "expected_result": "Genel beklenen sonuç",
  "tags": ["tag1", "tag2"]
}}

JSON array olarak yanıt ver: [ {{...}}, {{...}}, ... ]
Minimum 10, maksimum 30 test case üret.
Kritik riskli alanlar için daha fazla test ekle.
Negatif test ve edge case'leri unutma."""


def _normalize_analysis_text(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    return normalized


def _estimate_requirement_count(text: str) -> int:
    lines = [line.strip("-*0123456789. \t") for line in text.splitlines()]
    meaningful = [line for line in lines if len(line) >= 24]
    return min(max(len(meaningful), 1), 50) if text.strip() else 0


def _build_trace_links(
    *,
    source_type: str,
    source_name: str | None,
    source_checksum: str,
    total_generated: int = 0,
    approved_count: int = 0,
    rejected_count: int = 0,
) -> dict[str, Any]:
    return {
        "source": {
            "type": source_type,
            "name": source_name,
            "checksum": source_checksum,
        },
        "requirements": {
            "status": "derived",
        },
        "test_cases": {
            "status": "generated",
            "total": total_generated,
        },
        "approvals": {
            "status": "pending_review" if approved_count == 0 and rejected_count == 0 else "in_review",
            "approved": approved_count,
            "rejected": rejected_count,
        },
        "scenarios": {
            "status": "pending_creation" if approved_count == 0 else "partially_created",
            "created": approved_count,
        },
    }


# ── Core Service Functions ────────────────────────────────────────────────────

def generate_test_cases_for_project(
    db: Session,
    project_id: str,
    request: GenerateTestCasesRequest,
) -> GenerateTestCasesResponse:
    """
    Main entry: calls AI Gateway, saves batch + test cases to DB.
    Returns the batch ID and generated test cases.
    """
    # Create batch record
    normalized_analysis = _normalize_analysis_text(request.analysis_text)
    source_checksum = hashlib.sha256(normalized_analysis.encode("utf-8")).hexdigest()
    requirement_count = _estimate_requirement_count(request.analysis_text)
    candidate_scenario_count = min(max(requirement_count, len(request.modules) or 0, 1), 30)
    batch = TspmAiBatch(
        project_id=project_id,
        source_type=request.source_type,
        source_name=request.source_name,
        source_text_preview=request.analysis_text[:500],
        analysis_artifact_kind=f"{request.source_type}_analysis",
        source_checksum=source_checksum,
        normalized_source_excerpt=normalized_analysis[:1200],
        extracted_requirements_count=requirement_count,
        candidate_scenarios_count=candidate_scenario_count,
        trace_links=_build_trace_links(
            source_type=request.source_type,
            source_name=request.source_name,
            source_checksum=source_checksum,
        ),
        extra_instructions=request.extra_instructions,
        status="generating",
    )
    db.add(batch)
    db.flush()  # get batch.id

    try:
        prompt = _build_prompt_for_modules(
            request.analysis_text,
            request.modules,
            request.extra_instructions,
        )

        # Call AI Gateway
        raw_response, provider_used = _call_ai_for_test_cases(prompt)
        batch.ai_provider = provider_used

        # Parse response
        raw_cases = _parse_test_cases_json(raw_response)
        logger.info(f"AI returned {len(raw_cases)} test cases for batch {batch.id}")

        saved_cases: list[TspmTestCase] = []
        for idx, tc_data in enumerate(raw_cases):
            if not isinstance(tc_data, dict):
                continue
            title = tc_data.get("title", f"Test Case {idx + 1}")
            if not title or not title.strip():
                continue

            tc = TspmTestCase(
                project_id=project_id,
                batch_id=batch.id,
                title=title.strip(),
                description=tc_data.get("description", ""),
                module_name=tc_data.get("module_name"),
                feature_area=tc_data.get("feature_area"),
                test_type=_validate_enum(tc_data.get("test_type", "functional"), ["functional", "regression", "smoke", "edge_case", "negative"], "functional"),
                priority=_validate_enum(tc_data.get("priority", "medium"), ["critical", "high", "medium", "low"], "medium"),
                risk_level=_validate_enum(tc_data.get("risk_level", "medium"), ["high", "medium", "low"], "medium"),
                preconditions=tc_data.get("preconditions", []) or [],
                steps=_normalize_steps(tc_data.get("steps", [])),
                expected_result=tc_data.get("expected_result", ""),
                tags=tc_data.get("tags", []) or [],
                review_status="pending",
            )
            db.add(tc)
            saved_cases.append(tc)

        batch.total_generated = len(saved_cases)
        batch.status = "ready" if saved_cases else "error"
        batch.trace_links = _build_trace_links(
            source_type=batch.source_type,
            source_name=batch.source_name,
            source_checksum=source_checksum,
            total_generated=len(saved_cases),
            approved_count=batch.approved_count,
            rejected_count=batch.rejected_count,
        )
        if not saved_cases:
            batch.error_message = "AI yanıtı parse edilemedi veya test case üretilemedi."
        batch.completed_at = utcnow()

        db.commit()
        db.refresh(batch)
        for tc in saved_cases:
            db.refresh(tc)

        return GenerateTestCasesResponse(
            batch_id=batch.id,
            analysis_artifact=AiBatchOut.model_validate(batch),
            total_generated=len(saved_cases),
            ai_provider=provider_used,
            test_cases=[TestCaseOut.model_validate(tc) for tc in saved_cases],
            message=f"{len(saved_cases)} test case oluşturuldu ({provider_used or 'AI'} ile).",
        )

    except Exception as exc:
        logger.error(f"Test case generation failed: {exc}", exc_info=True)
        batch.status = "error"
        batch.error_message = str(exc)
        batch.completed_at = utcnow()
        batch.trace_links = _build_trace_links(
            source_type=batch.source_type,
            source_name=batch.source_name,
            source_checksum=batch.source_checksum or "",
            total_generated=batch.total_generated,
            approved_count=batch.approved_count,
            rejected_count=batch.rejected_count,
        )
        db.commit()
        raise


def _call_ai_for_test_cases(prompt: str) -> tuple[str, str]:
    """
    Calls AI Gateway for test case generation.
    Returns (raw_text, provider_name).
    """
    try:
        raw = gateway_complete(
            task_type="generate_test_cases",
            user_message=prompt,
            temperature=0.5,
            max_tokens=4000,
        )
        return raw, "ai_gateway"
    except Exception as e:
        logger.error(f"AI Gateway call failed: {e}")
        raise RuntimeError(f"AI Gateway erişilemiyor: {e}") from e


def _validate_enum(value: str, allowed: list[str], default: str) -> str:
    return value if value in allowed else default


def _normalize_steps(raw_steps: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_steps, list):
        return []
    normalized = []
    for i, step in enumerate(raw_steps):
        if isinstance(step, str):
            normalized.append({"order": i + 1, "action": step, "expected": ""})
        elif isinstance(step, dict):
            normalized.append({
                "order": step.get("order", i + 1),
                "action": step.get("action", step.get("step", step.get("description", ""))),
                "expected": step.get("expected", step.get("expected_result", "")),
            })
    return normalized


# ── CRUD Operations ───────────────────────────────────────────────────────────

def get_batch(db: Session, batch_id: str, project_id: str) -> Optional[TspmAiBatch]:
    return db.query(TspmAiBatch).filter_by(id=batch_id, project_id=project_id).first()


def list_batches(db: Session, project_id: str) -> list[TspmAiBatch]:
    return (
        db.query(TspmAiBatch)
        .filter_by(project_id=project_id)
        .order_by(TspmAiBatch.created_at.desc())
        .all()
    )


def list_test_cases(
    db: Session,
    project_id: str,
    batch_id: Optional[str] = None,
    review_status: Optional[str] = None,
) -> list[TspmTestCase]:
    q = db.query(TspmTestCase).filter_by(project_id=project_id)
    if batch_id:
        q = q.filter(TspmTestCase.batch_id == batch_id)
    if review_status:
        q = q.filter(TspmTestCase.review_status == review_status)
    return q.order_by(TspmTestCase.created_at.asc()).all()


def get_test_case(db: Session, tc_id: str, project_id: str) -> Optional[TspmTestCase]:
    return db.query(TspmTestCase).filter_by(id=tc_id, project_id=project_id).first()


def review_test_case(
    db: Session,
    tc: TspmTestCase,
    action: TestCaseReviewAction,
) -> TspmTestCase:
    """Approve / reject / edit a single test case."""
    if action.action == "approve":
        tc.review_status = "approved"
        if action.reviewer_note:
            tc.reviewer_note = action.reviewer_note
        # Create scenario from test case
        scenario = _test_case_to_scenario(tc)
        db.add(scenario)
        db.flush()
        tc.scenario_id = scenario.id
        _update_batch_counts(db, tc.batch_id)

    elif action.action == "reject":
        tc.review_status = "rejected"
        tc.reviewer_note = action.reviewer_note or ""
        _update_batch_counts(db, tc.batch_id)

    elif action.action == "edit":
        if action.edits:
            _apply_edits(tc, action.edits)
        tc.review_status = "edited"
        # Also approve if edits provided
        if action.action == "edit" and action.reviewer_note:
            tc.reviewer_note = action.reviewer_note

    db.commit()
    db.refresh(tc)
    return tc


def bulk_review(
    db: Session,
    project_id: str,
    req: BulkReviewRequest,
) -> dict[str, int]:
    """Bulk approve or reject multiple test cases. Returns counts."""
    cases = (
        db.query(TspmTestCase)
        .filter(TspmTestCase.project_id == project_id, TspmTestCase.id.in_(req.ids))
        .all()
    )

    approved = 0
    rejected = 0
    batch_ids: set[str] = set()

    for tc in cases:
        if tc.batch_id:
            batch_ids.add(tc.batch_id)
        if req.action == "approve" and tc.review_status == "pending":
            tc.review_status = "approved"
            if req.reviewer_note:
                tc.reviewer_note = req.reviewer_note
            scenario = _test_case_to_scenario(tc)
            db.add(scenario)
            db.flush()
            tc.scenario_id = scenario.id
            approved += 1
        elif req.action == "reject" and tc.review_status == "pending":
            tc.review_status = "rejected"
            tc.reviewer_note = req.reviewer_note or ""
            rejected += 1

    # Update batch counters
    for batch_id in batch_ids:
        _update_batch_counts(db, batch_id)

    db.commit()
    return {"approved": approved, "rejected": rejected, "total_processed": len(cases)}


def update_test_case(db: Session, tc: TspmTestCase, updates: TestCaseUpdate) -> TspmTestCase:
    _apply_edits(tc, updates)
    tc.review_status = "edited"
    db.commit()
    db.refresh(tc)
    return tc


def delete_test_case(db: Session, tc: TspmTestCase) -> None:
    db.delete(tc)
    db.commit()


def delete_batch(db: Session, batch: TspmAiBatch) -> None:
    db.delete(batch)
    db.commit()


# ── Private helpers ───────────────────────────────────────────────────────────

def _test_case_to_scenario(tc: TspmTestCase) -> TspmScenario:
    """Convert an approved TspmTestCase to a TspmScenario."""
    tags = list(tc.tags or [])
    if tc.test_type:
        tags.append(tc.test_type)
    if tc.priority:
        tags.append(f"priority:{tc.priority}")
    if tc.risk_level == "high":
        tags.append("high_risk")
    if tc.module_name:
        tags.append(tc.module_name.lower().replace(" ", "_"))

    # Build steps list in scenario format
    steps = []
    if tc.preconditions:
        for pre in tc.preconditions:
            steps.append({"keyword": "Given", "text": pre})
    if tc.steps:
        for i, s in enumerate(tc.steps):
            keyword = "When" if i == 0 else "And"
            steps.append({"keyword": keyword, "text": s.get("action", "")})
            if s.get("expected"):
                steps.append({"keyword": "Then", "text": s["expected"]})
    elif tc.expected_result:
        steps.append({"keyword": "Then", "text": tc.expected_result})

    description = tc.description or ""
    if tc.expected_result:
        description += f"\n\nBeklenen Sonuç: {tc.expected_result}"

    return TspmScenario(
        project_id=tc.project_id,
        title=tc.title,
        description=description.strip(),
        status="draft",
        steps=steps if steps else None,
        tags=list(set(tags)),
    )


def _apply_edits(tc: TspmTestCase, updates: TestCaseUpdate) -> None:
    for field, value in updates.model_dump(exclude_none=True).items():
        setattr(tc, field, value)


def _update_batch_counts(db: Session, batch_id: Optional[str]) -> None:
    if not batch_id:
        return
    batch = db.query(TspmAiBatch).filter_by(id=batch_id).first()
    if not batch:
        return
    approved = db.query(TspmTestCase).filter_by(batch_id=batch_id, review_status="approved").count()
    rejected = db.query(TspmTestCase).filter_by(batch_id=batch_id, review_status="rejected").count()
    batch.approved_count = approved
    batch.rejected_count = rejected
    existing_links = batch.trace_links or {}
    batch.trace_links = {
        **existing_links,
        "source": existing_links.get("source", {}),
        "requirements": existing_links.get("requirements", {"status": "derived"}),
        "test_cases": {
            "status": "generated",
            "total": batch.total_generated,
        },
        "approvals": {
            "status": "completed" if approved + rejected >= batch.total_generated and batch.total_generated > 0 else "in_review",
            "approved": approved,
            "rejected": rejected,
        },
        "scenarios": {
            "status": "created" if approved > 0 and approved == batch.approved_count else ("partially_created" if approved > 0 else "pending_creation"),
            "created": approved,
        },
    }
