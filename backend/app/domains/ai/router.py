"""AI Chat endpoints — sessions and messages."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.domains.ai.qa_nl_router import router as qa_nl_router
from app.domains.ai.router_shared import (
    CurrentUser,
    DB,
    check_llm_access as _check_llm_access,
    raise_structured_internal_error as _raise_structured_internal_error,
    record_llm_usage_safe as _record_llm_usage_safe,
    require_project_access as _require_project_access,
)
from app.domains.tspm.models import AiChatSession, AiChatMessage
from app.domains.ai.service import (
    # sync (backward compat)
    call_llm,
    chat_completion,
    chat_completion_stream,
    analyze_test_results,
    generate_scenarios,
    generate_test_data,
    _parse_json_response,
    # async
    async_call_llm,
    async_chat_completion,
    async_chat_completion_stream,
    async_analyze_test_results,
    async_generate_scenarios,
    async_generate_test_data,
)
from app.config import settings

import json
import json as _json
import logging
import threading
import uuid

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


def _reports_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "reports"


def _latest_workflow_signoff_report() -> dict[str, Any] | None:
    reports_dir = _reports_dir()
    files = sorted(
        reports_dir.glob("ai-workflow-signoff-*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for path in files:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(raw, dict):
            return {"path": str(path), "report": raw}
    return None


def _build_workflow_signoff_summary() -> dict[str, Any] | None:
    latest = _latest_workflow_signoff_report()
    if latest is None:
        return None

    report = latest["report"]
    checks = report.get("checks") if isinstance(report.get("checks"), list) else []
    latest_live_eval = next(
        (item for item in checks if isinstance(item, dict) and item.get("name") == "live_eval_contract_strict"),
        None,
    )

    if latest_live_eval is None:
        files = sorted(
            _reports_dir().glob("ai-workflow-signoff-*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in files[1:]:
            try:
                candidate = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(candidate, dict):
                continue
            candidate_checks = candidate.get("checks") if isinstance(candidate.get("checks"), list) else []
            latest_live_eval = next(
                (
                    item
                    for item in candidate_checks
                    if isinstance(item, dict) and item.get("name") == "live_eval_contract_strict"
                ),
                None,
            )
            if latest_live_eval is not None:
                latest_live_eval = {
                    **latest_live_eval,
                    "report_path": str(path),
                    "report_generated_at": candidate.get("generated_at"),
                }
                break

    summary = {
        "generated_at": report.get("generated_at"),
        "release_decision": report.get("release_decision"),
        "llm_quality_score": report.get("llm_quality_score"),
        "prompt_center_hash": report.get("prompt_center_hash"),
        "report_path": latest["path"],
        "failed_required_checks": report.get("failed_required_checks", []),
        "live_eval_gate": None,
    }

    if latest_live_eval is not None:
        summary["live_eval_gate"] = {
            "status": latest_live_eval.get("status"),
            "required": bool(latest_live_eval.get("required")),
            "message": latest_live_eval.get("message"),
            "started_at": latest_live_eval.get("started_at"),
            "duration_ms": latest_live_eval.get("duration_ms"),
            "report_path": latest_live_eval.get("report_path", latest["path"]),
            "report_generated_at": latest_live_eval.get("report_generated_at", report.get("generated_at")),
        }

    return summary


def _learn_from_chat(user_content: str, ai_response: str, session_id: str, project_id: str) -> None:
    """Background: ingest Q&A pair into KnowledgeStore for continuous learning."""
    try:
        from app.domains.ai.knowledge_store import KnowledgeStore
        store = KnowledgeStore(project_id=project_id)

        # Skip very short or error responses
        if len(ai_response) < 30 or ai_response.startswith("AI yanıt üretemedi"):
            store.close()
            return

        # Combine Q&A as a single learning record
        text = (
            f"Kullanıcı Sorusu: {user_content[:500]}\n"
            f"AI Yanıtı: {ai_response[:1000]}"
        )
        try:
            store.ingest(
                text=text,
                source="chat_history",
                metadata={"session_id": session_id, "q_len": len(user_content), "a_len": len(ai_response)},
                project_id=project_id,
            )
        finally:
            store.close()
    except Exception as e:
        _logger.debug("Chat learning hatası: %s", e)


class SessionCreate(BaseModel):
    project_id: str
    title: str = "Yeni Sohbet"

class SessionOut(BaseModel):
    id: str
    project_id: str
    title: str
    created_at: str
    updated_at: str
    model_config = {"from_attributes": True}

class MessageCreate(BaseModel):
    content: str = Field(min_length=1)

class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: str
    model_config = {"from_attributes": True}

class ChatResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut


@router.post("/chat/sessions", response_model=SessionOut, status_code=201)
def create_session(body: SessionCreate, db: DB, user: CurrentUser):
    _require_project_access(db, user, body.project_id)
    session = AiChatSession(
        project_id=body.project_id,
        user_id=user.id,
        title=body.title,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionOut(
        id=session.id, project_id=session.project_id,
        title=session.title,
        created_at=str(session.created_at), updated_at=str(session.updated_at),
    )


@router.get("/llm/usage")
def get_llm_usage(user: CurrentUser):
    """Kullanicinin güncel LLM kullanim durumunu dondurur (rate limit bilgisi)."""
    try:
        from app.domains.ai.llm_rate_limiter import get_user_usage
        return get_user_usage(str(user.id))
    except Exception as exc:
        _logger.warning("LLM usage lookup failed for user %s: %s", user.id, exc)
        return {
            "requests_this_minute": 0,
            "max_requests_per_minute": 30,
            "tokens_this_hour": 0,
            "max_tokens_per_hour": 500_000,
            "tokens_today": 0,
            "max_tokens_per_day": 2_000_000,
        }


@router.get("/chat/sessions", response_model=List[SessionOut])
def list_sessions(db: DB, user: CurrentUser, project_id: Optional[str] = None):
    stmt = select(AiChatSession).where(AiChatSession.user_id == user.id)
    if project_id:
        stmt = stmt.where(AiChatSession.project_id == project_id)
    stmt = stmt.order_by(AiChatSession.updated_at.desc())
    sessions = list(db.scalars(stmt))
    return [
        SessionOut(
            id=s.id, project_id=s.project_id, title=s.title,
            created_at=str(s.created_at), updated_at=str(s.updated_at),
        )
        for s in sessions
    ]


@router.delete("/chat/sessions/{session_id}", status_code=204)
def delete_session(session_id: str, db: DB, user: CurrentUser):
    session = db.get(AiChatSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Oturum bulunamadı")
    db.delete(session)
    db.commit()


@router.get("/chat/sessions/{session_id}/messages", response_model=List[MessageOut])
def list_messages(session_id: str, db: DB, user: CurrentUser):
    session = db.get(AiChatSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Oturum bulunamadı")
    msgs = list(db.scalars(
        select(AiChatMessage)
        .where(AiChatMessage.session_id == session_id)
        .order_by(AiChatMessage.created_at)
    ))
    return [
        MessageOut(id=m.id, role=m.role, content=m.content, created_at=str(m.created_at))
        for m in msgs
    ]


@router.post(
    "/chat/sessions/{session_id}/messages",
    response_model=ChatResponse,
    responses={
        200: {
            "description": "AI mesaji basariyla uretildi",
            "content": {
                "application/json": {
                    "example": {
                        "user_message": {
                            "id": "msg-user-1",
                            "role": "user",
                            "content": "Odeme akisi icin hangi senaryolari eklemeliyim?",
                            "created_at": "2026-04-16T10:00:00Z",
                        },
                        "assistant_message": {
                            "id": "msg-assistant-1",
                            "role": "assistant",
                            "content": "Boundary ve negatif odeme senaryolarini da eklemenizi oneririm.",
                            "created_at": "2026-04-16T10:00:01Z",
                        },
                    }
                }
            },
        },
        404: {"description": "Sohbet oturumu bulunamadi"},
        429: {"description": "AI oran siniri asildi"},
    },
)
async def send_message(session_id: str, body: MessageCreate, db: DB, user: CurrentUser):
    # ── Per-user LLM rate limit ──
    _check_llm_access(str(user.id))

    session = db.get(AiChatSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Oturum bulunamadı")

    user_msg = AiChatMessage(session_id=session_id, role="user", content=body.content)
    db.add(user_msg)
    db.flush()

    prev_msgs = list(db.scalars(
        select(AiChatMessage)
        .where(AiChatMessage.session_id == session_id)
        .order_by(AiChatMessage.created_at)
    ))
    history = [{"role": m.role, "content": m.content} for m in prev_msgs[-settings.ai_max_context_messages:]]

    try:
        ai_response = await async_chat_completion(
            body.content,
            history=history,
            project_id=session.project_id,
            user_id=str(user.id),
        )
    except Exception as e:
        _logger.exception("Async chat completion failed for session %s", session_id)
        ai_response = f"AI yanıt üretemedi: {str(e)}"

    # Record usage (fire-and-forget)
    _record_llm_usage_safe(str(user.id), body.content, ai_response)

    assistant_msg = AiChatMessage(session_id=session_id, role="assistant", content=ai_response)
    db.add(assistant_msg)
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    # Background: learn from this conversation (non-blocking)
    import asyncio
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, _learn_from_chat, body.content, ai_response, session_id, session.project_id)

    return ChatResponse(
        user_message=MessageOut(id=user_msg.id, role=user_msg.role, content=user_msg.content, created_at=str(user_msg.created_at)),
        assistant_message=MessageOut(id=assistant_msg.id, role=assistant_msg.role, content=assistant_msg.content, created_at=str(assistant_msg.created_at)),
    )


# ── SSE Streaming Chat ──────────────────────────────────────────────


@router.post("/chat/sessions/{session_id}/messages/stream")
async def stream_message(session_id: str, body: MessageCreate, db: DB, user: CurrentUser):
    """
    Streaming chat endpoint — Server-Sent Events (SSE) ile token token yanıt gonderir.

    SSE event formati:
      data: {"token": "merhaba"}          — her token chunk'i
      data: {"done": true, "message_id": "...", "user_message_id": "..."}  — tamamlandi
      data: {"error": "..."}              — hata durumunda
    """
    # ── Per-user LLM rate limit ──
    _check_llm_access(str(user.id))

    # ── Session dogrulama ────────────────────────────────────────────
    session = db.get(AiChatSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Oturum bulunamadi")

    # ── Kullanıcı mesajini kaydet ────────────────────────────────────
    user_msg = AiChatMessage(session_id=session_id, role="user", content=body.content)
    db.add(user_msg)
    db.flush()
    user_msg_id = user_msg.id

    # ── Geçmiş mesajlari al ──────────────────────────────────────────
    prev_msgs = list(db.scalars(
        select(AiChatMessage)
        .where(AiChatMessage.session_id == session_id)
        .order_by(AiChatMessage.created_at)
    ))
    history = [{"role": m.role, "content": m.content} for m in prev_msgs[-settings.ai_max_context_messages:]]

    # Commit user message so it persists regardless of streaming outcome
    db.commit()

    # ── SSE async generator ──────────────────────────────────────────
    async def _sse_generator():
        collected_tokens: list[str] = []
        assistant_msg_id = str(uuid.uuid4())
        try:
            async for token in async_chat_completion_stream(
                body.content,
                history=history,
                project_id=session.project_id,
                user_id=str(user.id),
            ):
                collected_tokens.append(token)
                event_data = _json.dumps({"token": token}, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

            # ── Tamamlanan yanitı DB'ye kaydet ──────────────────────
            full_response = "".join(collected_tokens)
            _record_llm_usage_safe(str(user.id), body.content, full_response)
            _save_assistant_message(
                session_id=session_id,
                message_id=assistant_msg_id,
                content=full_response,
                user_content=body.content,
                project_id=session.project_id,
            )

            done_data = _json.dumps({
                "done": True,
                "message_id": assistant_msg_id,
                "user_message_id": user_msg_id,
            }, ensure_ascii=False)
            yield f"data: {done_data}\n\n"

        except Exception as e:
            _logger.error("SSE streaming hatasi: %s", e)
            # If we collected some tokens, still try to save
            if collected_tokens:
                partial = "".join(collected_tokens)
                _record_llm_usage_safe(str(user.id), body.content, partial)
                _save_assistant_message(
                    session_id=session_id,
                    message_id=assistant_msg_id,
                    content=partial + f"\n\n[Streaming kesildi: {str(e)[:100]}]",
                    user_content=body.content,
                    project_id=session.project_id,
                )
            error_data = _json.dumps({"error": str(e)[:200]}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _save_assistant_message(
    session_id: str,
    message_id: str,
    content: str,
    user_content: str,
    project_id: str,
) -> None:
    """
    Streaming tamamlandiktan sonra assistant mesajini DB'ye kaydet.
    Ayri bir DB session kullanir cunku streaming generator
    orijinal request session'i kapanmis olabilir.
    """
    try:
        from app.infra.database import SessionLocal
        with SessionLocal() as db:
            msg = AiChatMessage(
                session_id=session_id,
                role="assistant",
                content=content,
            )
            # Override the auto-generated id with our pre-determined one
            msg.id = message_id
            db.add(msg)
            db.commit()

        # Background: learn from this conversation (fire-and-forget)
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, _learn_from_chat, user_content, content, session_id, project_id)
        except RuntimeError:
            # No running event loop (called from sync context) — fallback to thread
            threading.Thread(
                target=_learn_from_chat,
                args=(user_content, content, session_id, project_id),
                daemon=True,
            ).start()
    except Exception as e:
        _logger.error("Assistant mesajı kaydedilemedi: %s", e)


# ═══ Extended Streaming Request Models ══════════════════════════════════


class ScenarioStreamRequest(BaseModel):
    description: str
    context: str = ""
    count: int = Field(default=5, ge=1, le=20)
    project_id: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=32768)


class AnalysisStreamRequest(BaseModel):
    execution_data: str
    question: str = ""
    project_id: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=32768)


class TestDataStreamRequest(BaseModel):
    description: str
    columns: Optional[List[dict]] = None
    row_count: int = Field(default=10, ge=1, le=100)
    project_id: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=32768)


class GeneralStreamRequest(BaseModel):
    system_prompt: str
    user_message: str
    parse_json: bool = False
    project_id: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=32768)


# ═══ Extended Streaming Endpoints ═══════════════════════════════════════


@router.post("/stream/scenarios")
async def stream_scenario_generation(body: ScenarioStreamRequest, user: CurrentUser):
    """Senaryo uretimini streaming olarak yapar."""
    from app.domains.ai.streaming_service import get_streaming_service
    svc = get_streaming_service()
    _check_llm_access(str(user.id))

    async def event_generator():
        collected = ""
        async for chunk in svc.stream_scenario_generation(
            description=body.description,
            context=body.context,
            count=body.count,
            project_id=body.project_id,
            user_id=str(user.id),
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        ):
            if chunk.get("type") == "token":
                collected += str(chunk.get("content", ""))
            elif chunk.get("type") == "complete":
                _record_llm_usage_safe(str(user.id), body.description, body.context, collected)
            elif chunk.get("type") == "error" and collected:
                _record_llm_usage_safe(str(user.id), body.description, body.context, collected)
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/stream/analysis")
async def stream_test_analysis(body: AnalysisStreamRequest, user: CurrentUser):
    """Test analizi streaming."""
    from app.domains.ai.streaming_service import get_streaming_service
    svc = get_streaming_service()
    _check_llm_access(str(user.id))

    async def event_generator():
        collected = ""
        async for chunk in svc.stream_test_analysis(
            execution_data=body.execution_data,
            question=body.question,
            project_id=body.project_id,
            user_id=str(user.id),
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        ):
            if chunk.get("type") == "token":
                collected += str(chunk.get("content", ""))
            elif chunk.get("type") == "complete":
                _record_llm_usage_safe(str(user.id), body.execution_data, body.question, collected)
            elif chunk.get("type") == "error" and collected:
                _record_llm_usage_safe(str(user.id), body.execution_data, body.question, collected)
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/stream/test-data")
async def stream_test_data(body: TestDataStreamRequest, user: CurrentUser):
    """Test verisi uretimi streaming."""
    from app.domains.ai.streaming_service import get_streaming_service
    svc = get_streaming_service()
    _check_llm_access(str(user.id))

    async def event_generator():
        collected = ""
        async for chunk in svc.stream_test_data_generation(
            description=body.description,
            columns=body.columns,
            row_count=body.row_count,
            project_id=body.project_id,
            user_id=str(user.id),
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        ):
            if chunk.get("type") == "token":
                collected += str(chunk.get("content", ""))
            elif chunk.get("type") == "complete":
                _record_llm_usage_safe(str(user.id), body.description, body.columns, collected)
            elif chunk.get("type") == "error" and collected:
                _record_llm_usage_safe(str(user.id), body.description, body.columns, collected)
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/stream/general")
async def stream_general_llm(body: GeneralStreamRequest, user: CurrentUser):
    """Genel amacli LLM streaming."""
    from app.domains.ai.streaming_service import get_streaming_service
    svc = get_streaming_service()
    _check_llm_access(str(user.id))

    async def event_generator():
        collected = ""
        async for chunk in svc.stream_general(
            system=body.system_prompt,
            user_content=body.user_message,
            parse_json=body.parse_json,
            project_id=body.project_id,
            user_id=str(user.id),
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        ):
            if chunk.get("type") == "token":
                collected += str(chunk.get("content", ""))
            elif chunk.get("type") == "complete":
                _record_llm_usage_safe(str(user.id), body.system_prompt, body.user_message, collected)
            elif chunk.get("type") == "error" and collected:
                _record_llm_usage_safe(str(user.id), body.system_prompt, body.user_message, collected)
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── AI Suggest Scenarios ─────────────────────────────────────────────

class SuggestScenariosRequest(BaseModel):
    description: str = ""
    count: int = 5

class AnalyzeExecutionRequest(BaseModel):
    question: str = ""

@router.post("/projects/{project_id}/suggest-scenarios")
async def suggest_scenarios(project_id: str, body: SuggestScenariosRequest, db: DB, user: CurrentUser):
    from app.domains.tspm.models import TspmScenario, TspmProject
    _check_llm_access(str(user.id))
    p = db.get(TspmProject, project_id)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proje bulunamadı")
    existing = list(db.scalars(
        select(TspmScenario).where(TspmScenario.project_id == project_id).limit(50)
    ))
    context = "\n".join([f"- {s.title}" for s in existing])
    desc = body.description or f"Proje: {p.name}. Mevcut senaryolar:\n{context}\n\nEksik test senaryolarını öner."
    try:
        scenarios = await async_generate_scenarios(
            desc,
            context=context,
            count=body.count,
            project_id=project_id,
            user_id=str(user.id),
        )
        _record_llm_usage_safe(str(user.id), desc, context, scenarios)
        return {"scenarios": scenarios}
    except Exception as e:
        _raise_structured_internal_error("ai_scenario_suggestion_failed", "AI hatası", e)


@router.post("/projects/{project_id}/executions/{run_id}/analyze")
async def analyze_execution(project_id: str, run_id: str, body: AnalyzeExecutionRequest, db: DB, user: CurrentUser):
    from app.domains.tspm.models import TspmExecution, TspmExecutionResult, TspmScenario
    _check_llm_access(str(user.id))
    ex = db.get(TspmExecution, run_id)
    if ex is None or ex.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koşu bulunamadı")
    results = list(db.scalars(
        select(TspmExecutionResult).where(TspmExecutionResult.execution_id == run_id)
    ))
    data_lines = []
    for r in results:
        sc = db.get(TspmScenario, r.scenario_id)
        data_lines.append(f"Senaryo: {sc.title if sc else r.scenario_id} | Durum: {r.status} | Not: {r.note or '-'}")
    execution_data = f"Koşu: {ex.name}\nTarih: {ex.created_at}\nDurum: {ex.status}\n\nSonuçlar:\n" + "\n".join(data_lines)
    try:
        analysis = await async_analyze_test_results(
            execution_data,
            body.question,
            project_id=project_id,
            user_id=str(user.id),
        )
        _record_llm_usage_safe(str(user.id), execution_data, body.question, analysis)
        return analysis
    except Exception as e:
        _raise_structured_internal_error("ai_execution_analysis_failed", "AI analiz hatası", e)


# ═══════════════════════════════════════════════════════════════════════
# AI Intelligence: Test Önceliklendirme, Anomali Tespiti, Assertion Advisor
# ═══════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/prioritize-tests")
def prioritize_tests(project_id: str, body: dict, db: DB, user: CurrentUser):
    """
    Değişen dosyalara ve geçmiş başarısızlık oranlarına göre testleri önceliklendirir.
    body: { changed_files: list[str], history: dict[str, {fail_rate: float, avg_duration: float}] }
    """
    from app.domains.tspm.models import TspmScenario, TspmExecutionResult, TspmExecution
    changed_files = body.get("changed_files", [])
    history = body.get("history", {})

    # Projenin tüm senaryolarını al
    scenarios = list(db.scalars(
        select(TspmScenario).where(TspmScenario.project_id == project_id)
    ))

    prioritized = []
    for sc in scenarios:
        score = 0.0
        h = history.get(sc.id, {})
        fail_rate = float(h.get("fail_rate", 0))
        avg_duration = float(h.get("avg_duration", 0))

        # Başarısızlık oranı ağırlığı: %40
        score += fail_rate * 0.4
        # Yavaş testler daha önce çalışsın: %20
        score += min(avg_duration / 60.0, 1.0) * 0.2
        # Değişen dosya etiket eşleşmesi: %40
        tags = sc.tags or []
        if any(cf.lower() in " ".join(tags).lower() for cf in changed_files):
            score += 0.4

        prioritized.append({
            "id": sc.id,
            "title": sc.title,
            "score": round(score, 3),
            "tags": tags,
            "fail_rate": fail_rate,
            "avg_duration": avg_duration,
        })

    prioritized.sort(key=lambda x: x["score"], reverse=True)
    return {"scenarios": prioritized, "total": len(prioritized)}


@router.post("/projects/{project_id}/anomaly-detect")
def anomaly_detect(project_id: str, body: dict, db: DB, user: CurrentUser):
    """
    Test sonuçlarında anomali (flaky, yavaşlama, regresyon) tespit eder.
    body: { test_results: list[{testId, status, duration, retryCount}] }
    """
    import statistics
    results = body.get("test_results", [])
    if not results:
        # Projedeki son koşu sonuçlarını kullan
        from app.domains.tspm.models import TspmExecutionResult, TspmExecution
        last_exec = db.scalars(
            select(TspmExecution).where(TspmExecution.project_id == project_id)
            .order_by(TspmExecution.created_at.desc()).limit(1)
        ).first()
        if last_exec:
            rows = list(db.scalars(
                select(TspmExecutionResult).where(TspmExecutionResult.execution_id == last_exec.id)
            ))
            results = [{"testId": r.scenario_id, "status": r.status, "duration": r.duration_ms or 0, "retryCount": 0} for r in rows]

    anomalies = []
    durations = [r.get("duration", 0) for r in results if r.get("duration", 0) > 0]
    if len(durations) > 2:
        mean_dur = statistics.mean(durations)
        stdev_dur = statistics.stdev(durations) if len(durations) > 1 else 0
        threshold = mean_dur + 2 * stdev_dur

        for r in results:
            issues = []
            if r.get("retryCount", 0) > 1:
                issues.append("flaky")
            if r.get("duration", 0) > threshold and threshold > 0:
                issues.append("yavaş")
            if r.get("status") == "failed":
                issues.append("başarısız")
            if issues:
                anomalies.append({"testId": r["testId"], "issues": issues, "duration": r.get("duration", 0)})

    return {
        "anomalies": anomalies,
        "total_tested": len(results),
        "anomaly_count": len(anomalies),
        "avg_duration_ms": round(statistics.mean(durations), 2) if durations else 0,
    }


@router.post("/assert-advisor")
async def assert_advisor(body: dict, user: CurrentUser):
    """
    Verilen test kodunu analiz ederek assertion önerileri üretir (LLM destekli).
    body: { source_code: str, file_path: str }
    """
    source = body.get("source_code", "")
    file_path = body.get("file_path", "")
    if not source.strip():
        raise HTTPException(400, "source_code gerekli")
    _check_llm_access(str(user.id))

    try:
        suggestions = await async_call_llm(
            "Sen kıdemli bir QA mühendisisin. Test kodunu analiz ederek eksik assertion'ları tespit et.",
            f"Dosya: {file_path}\n\nKod:\n```\n{source[:3000]}\n```\n\nJSON formatında dön: "
            '[{"line": int, "current": "...", "suggested": "...", "reason": "..."}]',
            json_mode=True,
            _trace_user_id=str(user.id),
        )
        _record_llm_usage_safe(str(user.id), file_path, source, suggestions)
        parsed = json.loads(suggestions)
        return {"suggestions": parsed if isinstance(parsed, list) else parsed.get("suggestions", [])}
    except Exception as e:
        _raise_structured_internal_error("ai_assert_advisor_failed", "AI assertion analizi hatası", e)


class KnowledgeIngestRequest(BaseModel):
    text: str = Field(min_length=5)
    source: str = Field(default="code_change")
    metadata: dict = Field(default_factory=dict)


@router.post("/knowledge/ingest")
def knowledge_ingest(body: KnowledgeIngestRequest, user: CurrentUser, project_id: str = ""):
    """Dışarıdan bilgi ekle — git hook, CI/CD, veya diğer araçlar için."""
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    allowed_sources = {"code_change", "execution", "error_pattern", "insight", "feature_file", "docs", "chat_history"}
    if body.source not in allowed_sources:
        raise HTTPException(400, f"Geçersiz source. İzin verilen: {allowed_sources}")
    from app.domains.ai.knowledge_store import KnowledgeStore
    store = KnowledgeStore(project_id=project_id)
    try:
        ok = store.ingest(text=body.text, source=body.source, metadata=body.metadata, project_id=project_id)
    finally:
        store.close()
    return {"ingested": True, "embedded": ok}


@router.get("/knowledge/stats")
def knowledge_stats(user: CurrentUser, project_id: str = ""):
    """KnowledgeStore istatistiklerini döndürür — UI hafıza göstergesi için."""
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    from app.domains.ai.knowledge_store import KnowledgeStore
    store = KnowledgeStore(project_id=project_id)
    try:
        return store.stats(project_id=project_id)
    finally:
        store.close()


@router.get("/providers")
def get_providers(user: CurrentUser):
    """Yapılandırılmış AI provider'ları döndürür (API anahtarları gizlenir)."""
    from app.config import get_settings
    s = get_settings()
    return {
        "active": s.ai_provider,
        "runtime_switch_supported": False,
        "note": "Saglayici secimi deployment konfigurasyonudur. AI_PROVIDER ortam degiskenini guncelleyip servisi yeniden baslatin.",
        "providers": [
            {"id": "openai", "name": "OpenAI", "configured": bool(s.openai_api_key)},
            {"id": "anthropic", "name": "Anthropic (Claude)", "configured": bool(s.anthropic_api_key)},
            {"id": "ollama", "name": "Ollama", "configured": bool(s.ollama_base_url)},
        ],
    }


_SUPPORTED_PROVIDERS = ("openai", "anthropic")


@router.put("/providers/active")
def set_active_provider(body: dict, user: CurrentUser):
    """Runtime provider degisikligi desteklenmez; yalnizca admin'e deterministic yanit doner."""
    from app.deps import _user_permissions
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(403, "Admin yetkisi gerekli")
    from app.config import get_settings
    s = get_settings()
    provider = body.get("provider", "")
    if provider and provider not in _SUPPORTED_PROVIDERS:
        raise HTTPException(409, f"'{provider}' provider runtime degisikligi desteklenmiyor.")
    if not provider:
        raise HTTPException(400, "Geçersiz provider. 'openai' veya 'anthropic' olmali.")
    return {
        "active": s.ai_provider,
        "runtime_switch_supported": False,
        "note": "Runtime provider degisikligi desteklenmiyor. AI_PROVIDER env ile yapilandirin.",
    }


# ── Batch Embedding API ──────────────────────────────────────────────────────


class BatchEmbedRequest(BaseModel):
    items: List[dict] = Field(..., description="[{text, source, metadata}] listesi")


class BatchEmbedResponse(BaseModel):
    ingested: int
    total: int


@router.post("/knowledge/batch-ingest", response_model=BatchEmbedResponse)
def batch_ingest(body: BatchEmbedRequest, user: CurrentUser, project_id: str = ""):
    """Toplu bilgi ingestion — embedding + KnowledgeStore kayit."""
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    try:
        from app.domains.ai.knowledge_store import KnowledgeStore
        store = KnowledgeStore(project_id=project_id)
        try:
            count = store.ingest_batch(body.items, project_id=project_id)
        finally:
            store.close()
        return BatchEmbedResponse(ingested=count, total=len(body.items))
    except Exception as e:
        _raise_structured_internal_error("ai_batch_ingest_failed", "Batch ingest hatasi", e)


@router.post("/knowledge/search")
def knowledge_search(body: dict, user: CurrentUser, project_id: str = ""):
    """KnowledgeStore'da semantik arama."""
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    query = body.get("query", "")
    if not query:
        raise HTTPException(400, "query alani gerekli")
    top_k = body.get("top_k", 5)
    sources = body.get("sources")
    min_similarity = body.get("min_similarity", 0.30)

    try:
        from app.domains.ai.knowledge_store import KnowledgeStore
        store = KnowledgeStore(project_id=project_id)
        try:
            chunks = store.retrieve(
                query,
                top_k=top_k,
                sources=sources,
                min_similarity=min_similarity,
                project_id=project_id,
            )
        finally:
            store.close()
        return {
            "results": [
                {
                    "content": c.content[:500],
                    "source": c.source,
                    "similarity": round(c.similarity, 3),
                    "metadata": c.metadata,
                }
                for c in chunks
            ],
            "total": len(chunks),
        }
    except Exception as e:
        _raise_structured_internal_error("ai_knowledge_search_failed", "Arama hatasi", e)


@router.delete("/knowledge/clear")
def knowledge_clear(user: CurrentUser, project_id: str = ""):
    """KnowledgeStore temizle (admin only)."""
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    from app.deps import _user_permissions
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(403, "Admin yetkisi gerekli")
    try:
        from app.domains.ai.knowledge_store import KnowledgeStore
        store = KnowledgeStore(project_id=project_id)
        try:
            conn = store._get_conn()
            with conn.cursor() as cur:
                if store._supports_project_scope(cur):
                    cur.execute("DELETE FROM project_knowledge WHERE project_id = %s", (project_id,))
                else:
                    cur.execute("DELETE FROM project_knowledge")
        finally:
            store.close()
        return {"cleared": True}
    except Exception as e:
        _raise_structured_internal_error("ai_knowledge_clear_failed", "Temizleme hatasi", e)


# ═══════════════════════════════════════════════════════════════════════
# LLM Quality Metrics & Smart Router Endpoints
# ═══════════════════════════════════════════════════════════════════════


@router.get("/quality-metrics")
def get_quality_metrics(
    user: CurrentUser,
    days: int = 30,
    agent_name: Optional[str] = None,
    model: Optional[str] = None,
    project_id: str = "",
    task_type: Optional[str] = None,
    phase: Optional[str] = None,
):
    """
    LLM kalite metriklerini getir — başarı orani, latency, hata dagilimi, trend.

    Query params:
      days       — kac gunluk veri (default 30)
      agent_name — belirli agent'a filtrele (opsiyonel)
      model      — belirli modele filtrele (opsiyonel)
    """
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    from app.deps import _user_permissions
    from app.domains.ai.quality_metrics import get_llm_quality_metrics
    perms = _user_permissions(user)
    scoped_user_id = None if "admin.*" in perms else str(user.id)
    return get_llm_quality_metrics(
        days=days,
        agent_name=agent_name,
        model=model,
        project_id=project_id,
        user_id=scoped_user_id,
        task_type=task_type,
        phase=phase,
    )


# ── Faz 4: Unified Quality Dashboard ────────────────────────────────────


@router.get("/quality/dashboard")
def quality_dashboard(user: CurrentUser, days: int = 7):
    """
    Unified AI quality dashboard — tek cagri ile tüm metrikler.

    Icerdigi bloklar:
      - overview (maliyet dahil)
      - by_agent / by_model
      - daily_trend / error_distribution
      - regression_alerts
      - judge (LLM-as-Judge ozetleri)
      - routing (Smart Model Router config + circuit state)
      - ingestion (RAG KnowledgeStore source istatistikleri)
      - eval_latest (son eval run)
    """
    from app.domains.ai.quality_metrics import get_llm_quality_metrics
    from app.domains.ai.quality_judge import get_judge_stats
    from app.domains.ai.smart_model_router import get_routing_stats
    from app.domains.ai.rag_ingestion import get_ingestion_stats
    from app.domains.ai.eval_suite import get_latest_eval_report
    from app.domains.evals.reporting import history_report, history_summary, latest_report

    metrics = get_llm_quality_metrics(days=days)
    eval_harness_history = history_report(limit=30)
    eval_harness_latest = latest_report()
    eval_harness_summary = history_summary(limit=30)
    workflow_signoff_latest = _build_workflow_signoff_summary()
    return {
        "period_days": days,
        "overview": metrics.get("overview", {}),
        "by_agent": metrics.get("by_agent", []),
        "by_model": metrics.get("by_model", []),
        "daily_trend": metrics.get("daily_trend", []),
        "error_distribution": metrics.get("error_distribution", {}),
        "regression_alerts": metrics.get("regression_alerts", []),
        "recommendations": metrics.get("recommendations", []),
        "judge": get_judge_stats(days=days),
        "routing": get_routing_stats(),
        "ingestion": get_ingestion_stats(),
        "eval_latest": get_latest_eval_report(),
        "eval_harness_latest": eval_harness_latest,
        "eval_harness_history": eval_harness_history,
        "eval_harness_summary": eval_harness_summary,
        "workflow_signoff_latest": workflow_signoff_latest,
    }


# ── Faz 5: Eval + Few-Shot Admin + RAG Maintenance ──────────────────────


@router.post("/eval/run")
def eval_run(
    user: CurrentUser,
    task_type: Optional[str] = None,
    include_judge: bool = True,
):
    """Golden eval suite'i manuel tetikle. Yalnizca admin."""
    from app.deps import _user_permissions
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(403, "Admin yetkisi gerekli")

    from app.domains.ai.eval_suite import run_eval_suite
    report = run_eval_suite(task_type=task_type, include_judge=include_judge)
    return {
        "suite": report.suite_name,
        "total": report.total_prompts,
        "pass_count": report.pass_count,
        "fail_count": report.fail_count,
        "pass_rate": report.pass_rate,
        "results": [
            {
                "prompt_id": r.prompt_id,
                "task_type": r.task_type,
                "model": r.model,
                "tier": r.tier,
                "pass_all": r.pass_all,
                "judge_overall": r.judge_overall,
                "latency_ms": r.latency_ms,
                "cost_usd": r.cost_usd,
            }
            for r in report.results
        ],
    }


@router.get("/eval/latest")
def eval_latest(user: CurrentUser, suite: str = "banking_test_gen_v1", limit: int = 50):
    """Son eval run sonuclarini getir."""
    from app.domains.ai.eval_suite import get_latest_eval_report
    return get_latest_eval_report(suite_name=suite, limit=limit)


@router.get("/few-shot/candidates")
def few_shot_candidates(user: CurrentUser, limit: int = 20):
    """Onay bekleyen few-shot aday ornekleri."""
    from app.domains.ai.few_shot_bank import list_candidates
    return {"candidates": list_candidates(limit=limit)}


@router.post("/few-shot/candidates/{example_id}/approve")
def few_shot_approve(example_id: int, user: CurrentUser):
    """Aday ornegi onayla. Yalnizca admin."""
    from app.deps import _user_permissions
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(403, "Admin yetkisi gerekli")
    from app.domains.ai.few_shot_bank import approve_candidate
    ok = approve_candidate(example_id, reviewer=str(user.id))
    if not ok:
        raise HTTPException(404, "Ornek bulunamadi")
    return {"approved": True, "id": example_id}


@router.post("/few-shot/seed")
def few_shot_seed(user: CurrentUser, force: bool = False):
    """Statik FEW_SHOT_EXAMPLES'i DB'ye yaz. Yalnizca admin."""
    from app.deps import _user_permissions
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(403, "Admin yetkisi gerekli")
    from app.domains.ai.few_shot_bank import seed_few_shot_examples_from_static
    return seed_few_shot_examples_from_static(force=force)


@router.post("/knowledge/ingest/bdd")
def knowledge_ingest_bdd(
    user: CurrentUser,
    base_path: str = "/Users/yasin_bulgan/Desktop/BGTS_Test_Donusum",
    limit: int = 0,
):
    """Manuel BDD .feature ingest. Yalnizca admin."""
    from app.deps import _user_permissions
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(403, "Admin yetkisi gerekli")
    from app.domains.ai.rag_ingestion import ingest_bdd_features
    chunks = ingest_bdd_features(base_path, limit=limit or None)
    return {"chunks_ingested": chunks}


@router.post("/knowledge/ingest/traces")
def knowledge_ingest_traces(
    user: CurrentUser,
    days: int = 1,
    max_records: int = 200,
):
    """Son N gunluk trace'lerden RAG'a beslenme. Yalnizca admin."""
    from app.deps import _user_permissions
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(403, "Admin yetkisi gerekli")
    from app.domains.ai.rag_ingestion import ingest_trace_insights
    return ingest_trace_insights(days=days, max_records=max_records)


# ── Semantic Cache yonetimi ─────────────────────────────────────────────


@router.get("/cache/stats")
def cache_stats(user: CurrentUser):
    """Semantic cache istatistikleri."""
    from app.domains.ai.semantic_cache import cache_stats
    return cache_stats()


@router.delete("/cache")
def cache_clear_endpoint(
    user: CurrentUser,
    task_type: Optional[str] = None,
):
    """Semantic cache temizle (admin). task_type verilirse sadece o bucket."""
    from app.deps import _user_permissions
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(403, "Admin yetkisi gerekli")
    from app.domains.ai.semantic_cache import cache_clear
    deleted = cache_clear(task_type=task_type)
    return {"deleted": deleted, "task_type": task_type}


# ── Fine-Tune Export ────────────────────────────────────────────────────


@router.get("/finetune/readiness")
def finetune_readiness(user: CurrentUser):
    """Fine-tuning için yeterli veri var mi?"""
    from app.domains.ai.finetune_export import get_export_readiness
    return get_export_readiness()


# ── Correlation ID Trace Chain ──────────────────────────────────────────


@router.get("/trace/chain/{correlation_id}")
def trace_chain(correlation_id: str, user: CurrentUser):
    """Bir correlation_id'ye ait tüm LLM cagri zincirini getir.

    Debug araci: kullanıcı tek bir ID ile baslangic istekten son LLM cagrisina
    kadar tüm adimlari gorur (trace'ler + judge skorlari + cross-agent events).
    """
    from app.domains.ai.llm_trace import _get_conn

    result: dict = {
        "correlation_id": correlation_id,
        "traces": [],
        "judge_runs": [],
        "cross_agent_events": [],
    }

    try:
        conn = _get_conn()
    except Exception as exc:
        raise HTTPException(503, f"DB bağlantı hatasi: {exc}")

    try:
        with conn.cursor() as cur:
            # 1) Traces
            cur.execute(
                """
                SELECT id, agent_name, model, phase, task_type,
                       latency_ms, success, json_parse_ok, cost_usd,
                       user_prompt_preview, response_preview, created_at
                FROM llm_traces
                WHERE correlation_id = %s
                ORDER BY created_at ASC
                LIMIT 200
                """,
                (correlation_id,),
            )
            for r in cur.fetchall() or []:
                result["traces"].append({
                    "id": r[0],
                    "agent_name": r[1],
                    "model": r[2],
                    "phase": r[3],
                    "task_type": r[4],
                    "latency_ms": r[5],
                    "success": r[6],
                    "json_parse_ok": r[7],
                    "cost_usd": float(r[8]) if r[8] else 0.0,
                    "user_prompt": (r[9] or "")[:400],
                    "response": (r[10] or "")[:600],
                    "created_at": r[11].isoformat() if r[11] else None,
                })

            # 2) Judge runs (tablo varsa)
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'llm_judge_runs')"
            )
            if cur.fetchone()[0]:
                cur.execute(
                    """
                    SELECT task_type, judged_model, overall,
                           correctness, completeness, domain_fit, format_validity,
                           rationale, created_at
                    FROM llm_judge_runs
                    WHERE correlation_id = %s
                    ORDER BY created_at ASC
                    """,
                    (correlation_id,),
                )
                for r in cur.fetchall() or []:
                    result["judge_runs"].append({
                        "task_type": r[0],
                        "judged_model": r[1],
                        "overall": float(r[2]) if r[2] is not None else None,
                        "correctness": float(r[3]) if r[3] is not None else None,
                        "completeness": float(r[4]) if r[4] is not None else None,
                        "domain_fit": float(r[5]) if r[5] is not None else None,
                        "format_validity": float(r[6]) if r[6] is not None else None,
                        "rationale": r[7],
                        "created_at": r[8].isoformat() if r[8] else None,
                    })
    except Exception as exc:
        _logger.debug("trace_chain hatasi: %s", exc)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    # Aggregate stats
    result["summary"] = {
        "total_traces": len(result["traces"]),
        "total_judge_runs": len(result["judge_runs"]),
        "total_cost_usd": round(sum(t.get("cost_usd", 0) for t in result["traces"]), 6),
        "total_latency_ms": sum(t.get("latency_ms", 0) for t in result["traces"]),
        "success_count": sum(1 for t in result["traces"] if t.get("success")),
        "avg_judge_overall": (
            round(
                sum(j["overall"] for j in result["judge_runs"] if j["overall"]) /
                max(1, len(result["judge_runs"])),
                2,
            ) if result["judge_runs"] else None
        ),
    }
    return result


# ── Rate-limit state endpoint ──────────────────────────────────────────


@router.get("/rate-limits")
def rate_limits_state(user: CurrentUser):
    """Tüm modellerin provider rate-limit state'i."""
    from app.domains.ai.rate_limit_monitor import get_all_rate_limits
    return {"models": get_all_rate_limits()}


# ── Pre-flight token planning ──────────────────────────────────────────


class TokenPlanRequest(BaseModel):
    model: str
    system_prompt: Optional[str] = None
    user_message: str
    requested_max_output: int = Field(default=4096, ge=1, le=64000)


@router.post("/token-plan")
def token_plan_endpoint(body: TokenPlanRequest, user: CurrentUser):
    """Prompt'un modele sigip sigmadigini on-kontrol et."""
    from app.domains.ai.token_counter import plan_tokens

    messages = []
    if body.system_prompt:
        messages.append({"role": "system", "content": body.system_prompt})
    messages.append({"role": "user", "content": body.user_message})

    plan = plan_tokens(
        model=body.model,
        messages=messages,
        requested_max_output=body.requested_max_output,
    )
    return plan.to_dict()


# ── Derin geliştirme turu: yeni endpoint'ler ──────────────────────────


@router.get("/shield/output-violations")
def shield_output_violations(user: CurrentUser, days: int = 7):
    """output_shield ihlal istatistikleri."""
    from app.domains.ai.output_shield import get_violation_stats
    return get_violation_stats(days=days)


@router.get("/routing/learned")
def routing_learned(user: CurrentUser, days: int = 14):
    """router_learning — son N gunluk veri uzerinden preference analizi."""
    from app.domains.ai.router_learning import compute_preferences
    return {"preferences": compute_preferences(days=days)}


@router.post("/routing/learn")
def routing_run_learning(user: CurrentUser, days: int = 14, persist: bool = True):
    """Router learning cycle'i manuel calistir (admin)."""
    from app.deps import _user_permissions
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(403, "Admin yetkisi gerekli")
    from app.domains.ai.router_learning import run_learning_cycle
    return run_learning_cycle(days=days, persist=persist)


@router.get("/review-queue")
def review_queue_pending(user: CurrentUser, limit: int = 50):
    """Bekleyen human-review kararlari."""
    from app.domains.ai.review_queue import list_pending
    return {"pending": list_pending(limit=limit)}


@router.get("/review-queue/stats")
def review_queue_stats(user: CurrentUser, days: int = 7):
    """Review kuyruk istatistikleri."""
    from app.domains.ai.review_queue import queue_stats
    return queue_stats(days=days)


class ReviewDecisionRequest(BaseModel):
    decision: str = Field(..., pattern=r"^(approved|rejected|edited)$")
    comment: Optional[str] = None
    edited_response: Optional[str] = None


@router.post("/review-queue/{review_id}/resolve")
def review_resolve(review_id: str, body: ReviewDecisionRequest, user: CurrentUser):
    """Review kararini uygula (admin)."""
    from app.deps import _user_permissions
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(403, "Admin yetkisi gerekli")
    from app.domains.ai.review_queue import resolve
    ok = resolve(
        review_id=review_id,
        decision=body.decision,
        reviewer=str(user.id),
        comment=body.comment,
        edited_response=body.edited_response,
    )
    if not ok:
        raise HTTPException(404, "Review kaydi bulunamadi veya zaten sonuclanmis")
    return {"resolved": True, "id": review_id, "decision": body.decision}


@router.get("/tools/list")
def tools_list(user: CurrentUser):
    """Kullanilabilir LLM tool'lari."""
    from app.domains.ai.tools import list_tools, tools_enabled
    return {
        "enabled": tools_enabled(),
        "tools": [
            {"name": t.name, "description": t.description}
            for t in list_tools()
        ],
    }


@router.post("/cache/embeddings/clear")
def cache_embeddings_clear(user: CurrentUser):
    """Embedding cache temizle (admin)."""
    from app.deps import _user_permissions
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(403, "Admin yetkisi gerekli")
    from app.domains.ai.embedding_cache import clear_embedding_cache
    deleted = clear_embedding_cache()
    return {"deleted": deleted}


@router.get("/cache/embeddings/stats")
def cache_embeddings_stats(user: CurrentUser):
    """Embedding cache istatistikleri."""
    from app.domains.ai.embedding_cache import cache_stats
    return cache_stats()


@router.post("/finetune/export")
def finetune_export(
    user: CurrentUser,
    min_judge_score: float = 9.0,
    task_type: Optional[str] = None,
    include_few_shot: bool = True,
    days: int = 90,
):
    """Fine-tune JSONL'i üret (admin). Cikti dosyasi yolu doner."""
    from app.deps import _user_permissions
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(403, "Admin yetkisi gerekli")
    from app.domains.ai.finetune_export import export_finetune_jsonl
    task_types = [task_type] if task_type else None
    result = export_finetune_jsonl(
        min_judge_score=min_judge_score,
        task_types=task_types,
        include_few_shot=include_few_shot,
        days=days,
    )
    return {
        "path": result.path,
        "total_pairs": result.total_pairs,
        "from_judge": result.from_judge,
        "from_few_shot": result.from_few_shot,
        "task_types": result.task_types,
    }


@router.get("/llm-traces")
def list_llm_traces(
    user: CurrentUser,
    run_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    limit: int = 50,
    project_id: str = "",
    task_type: Optional[str] = None,
    phase: Optional[str] = None,
):
    """Son LLM trace kayitlarini getir."""
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    from app.deps import _user_permissions
    from app.domains.ai.llm_trace import get_recent_traces
    perms = _user_permissions(user)
    scoped_user_id = None if "admin.*" in perms else str(user.id)
    return {
        "traces": get_recent_traces(
            project_id=project_id,
            user_id=scoped_user_id,
            run_id=run_id,
            agent_name=agent_name,
            task_type=task_type,
            phase=phase,
            limit=limit,
        )
    }


@router.get("/llm-traces/stats")
def llm_trace_stats(user: CurrentUser):
    """LLM trace özet istatistikleri."""
    from app.domains.ai.llm_trace import get_trace_stats
    return get_trace_stats()


@router.get("/model-router/stats")
def model_router_stats(user: CurrentUser):
    """Smart Model Router konfigurasyonu ve istatistikleri."""
    try:
        from app.domains.ai.smart_model_router import get_routing_stats
        return get_routing_stats()
    except ImportError:
        return {"error": "Smart Model Router modulu bulunamadi"}
    except Exception as e:
        _logger.exception("Model router stats lookup failed")
        _raise_structured_internal_error("ai_model_router_stats_failed", "Router stats hatasi", e)


@router.get("/cross-agent-memory/stats")
def cross_agent_memory_stats(user: CurrentUser, db: DB, project_id: str = ""):
    """CrossAgentMemory istatistikleri — agent'lar arasi bilgi paylasim durumu."""
    _require_project_access(db, user, project_id)
    from app.domains.ai.cross_agent_memory import CrossAgentMemory
    return CrossAgentMemory.stats(project_id=project_id)


@router.get("/cross-agent-memory/entries")
def cross_agent_memory_entries(
    user: CurrentUser,
    db: DB,
    event_type: Optional[str] = None,
    agent_name: Optional[str] = None,
    limit: int = 20,
    project_id: str = "",
):
    """CrossAgentMemory'deki entry'leri listele."""
    _require_project_access(db, user, project_id)
    from app.domains.ai.cross_agent_memory import CrossAgentMemory
    event_types = [event_type] if event_type else None
    entries = CrossAgentMemory.query(
        project_id=project_id,
        event_types=event_types,
        limit=min(limit, 100),
    )
    # agent_name filtresi
    if agent_name:
        entries = [e for e in entries if e.get("agent_name") == agent_name]
    return {"entries": entries, "total": len(entries)}


@router.get("/few-shot-bank/stats")
def few_shot_bank_stats(user: CurrentUser):
    """Few-shot ornek bankasi istatistikleri."""
    try:
        from app.domains.ai.few_shot_bank import list_available_examples, get_example_count
        return {
            "categories": list_available_examples(),
            "counts": get_example_count(),
        }
    except ImportError:
        return {"error": "Few-shot bank modulu bulunamadi"}
    except Exception as e:
        _raise_structured_internal_error("ai_few_shot_stats_failed", "Few-shot stats hatasi", e)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# NEXUS AI AUTOPILOT — Zero-touch QA operating loop
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class AutopilotRunRequest(BaseModel):
    project_id: str = Field(..., min_length=1)
    mode: str = Field(default="autonomous", pattern=r"^(observe|assist|autonomous)$")
    apply_safe_actions: bool = True
    trigger: str = Field(default="manual", max_length=64)


@router.get("/autopilot/status")
def autopilot_status(
    db: DB,
    user: CurrentUser,
    project_id: str = "",
):
    """Nexus AI Autopilot son durumu ve gerekirse canlı snapshot."""
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    from app.domains.ai.autopilot import latest_autopilot_status

    return latest_autopilot_status(db, project_id)


@router.get("/autopilot/runs")
def autopilot_runs(
    db: DB,
    user: CurrentUser,
    project_id: str = "",
    limit: int = 20,
):
    """Nexus AI Autopilot çalışma geçmişi."""
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    from app.domains.ai.autopilot import list_autopilot_runs

    return {"runs": list_autopilot_runs(db, project_id=project_id, limit=limit)}


@router.post("/autopilot/run")
def autopilot_run(
    body: AutopilotRunRequest,
    db: DB,
    user: CurrentUser,
):
    """
    Autopilot'u tek proje için manuel tetikle.

    mode:
      - observe: sadece sinyal + öneri
      - assist: öneri + güvenli plan
      - autonomous: öneri + güvenli aksiyon uygulama
    """
    from app.domains.ai.autopilot import NexusAutopilot

    try:
        autopilot = NexusAutopilot(db=db, project_id=body.project_id)
        return autopilot.run(
            mode=body.mode,  # type: ignore[arg-type]
            apply_safe_actions=body.apply_safe_actions,
            trigger=body.trigger,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        _logger.exception("Autopilot run hatasi")
        raise HTTPException(500, f"Autopilot hatasi: {str(exc)[:300]}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# QA ORCHESTRATION — Plan-Act-Verify Autonomous Testing Cycle
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class QAPlanRequest(BaseModel):
    goal: str = Field(..., min_length=3, description="QA hedefi — ornegin 'Transfer endpoint kapsamini artir'")
    context: Optional[Dict] = Field(default=None, description="Ek baglam bilgisi")


class QAPlanStep(BaseModel):
    step_id: int
    action: str
    description: str
    target: Optional[str] = None
    params: Dict = Field(default_factory=dict)
    depends_on: List[int] = Field(default_factory=list)
    estimated_duration_ms: int = 5000


class QAPlanResponse(BaseModel):
    plan_id: str
    goal: str
    steps: List[Dict]
    estimated_total_duration_ms: int
    coverage_before: float = 0.0
    expected_coverage_after: float = 0.0


class QACycleResponse(BaseModel):
    plan_id: str
    goal_achieved: bool = False
    coverage_before: float = 0.0
    coverage_after: float = 0.0
    coverage_delta: float = 0.0
    tests_generated: int = 0
    tests_executed: int = 0
    tests_passed: int = 0
    failures_healed: int = 0
    flaky_detected: int = 0
    assertions_added: int = 0
    quality_score: float = 0.0
    next_recommendations: List[str] = Field(default_factory=list)


class QAExploreRequest(BaseModel):
    spec_id: Optional[str] = Field(default=None, description="Belirli bir spec ile sinirla")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# NL TEST GENERATION — Pydantic Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class NLTestRequest(BaseModel):
    text: str = Field(..., min_length=3, description="Dogal dil test aciklamasi")
    output_format: str = Field(
        default="api_test",
        description="Cikti formati: api_test, bdd, pytest, playwright",
    )
    context: Optional[Dict] = Field(default=None, description="Ek baglam bilgisi")


class ParsedIntent(BaseModel):
    test_type: str = "positive"
    method: Optional[str] = None
    path_hint: Optional[str] = None
    expected_status: Optional[int] = None
    conditions: List[str] = Field(default_factory=list)
    entities: Dict[str, str] = Field(default_factory=dict)


class MatchedEndpoint(BaseModel):
    endpoint_id: str
    method: str
    path: str
    confidence: float


class GeneratedOutput(BaseModel):
    test_cases: List[Dict] = Field(default_factory=list)
    code: Optional[str] = None
    gherkin: Optional[str] = None


class ValidationResult(BaseModel):
    syntax_valid: bool = True
    warnings: List[str] = Field(default_factory=list)


class NLTestResponse(BaseModel):
    input_text: str
    parsed_intent: Dict
    matched_endpoints: List[Dict]
    output_format: str
    generated: Dict
    validation: Dict
    model_used: str
    duration_ms: float


class BatchNLRequest(BaseModel):
    texts: List[str] = Field(..., min_items=1, description="Dogal dil test aciklamalari listesi")
    output_format: str = Field(default="api_test")


class BatchNLResponse(BaseModel):
    results: List[Dict]
    summary: Dict


class EndpointSuggestion(BaseModel):
    text: str
    test_type: str
    priority: str


class SuggestFromEndpointResponse(BaseModel):
    endpoint_id: str
    endpoint: str
    suggestions: List[Dict]


class ValidateCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Dogrulanacak kod")
    language: str = Field(..., description="python veya typescript")


@router.post("/qa/plan")
def qa_create_plan(
    body: QAPlanRequest,
    db: DB,
    user: CurrentUser,
    project_id: str = "",
):
    """
    QA hedefi için bir test plani oluştur.

    Plan, LLM destekli olarak mevcut kapsam bosluklarini analiz eder
    ve adım adım bir test stratejisi uretir.
    """
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")

    try:
        from app.domains.ai.qa_orchestrator import QAOrchestrator
        orchestrator = QAOrchestrator(db=db, project_id=project_id)
        plan = orchestrator.plan(goal=body.goal, context=body.context)
        return plan
    except Exception as e:
        _logger.exception("QA plan olusturma hatasi")
        raise HTTPException(500, f"QA plan hatasi: {str(e)[:300]}")


@router.post("/qa/execute/{plan_id}")
def qa_execute_plan(
    plan_id: str,
    db: DB,
    user: CurrentUser,
    project_id: str = "",
):
    """
    Olusturulan bir QA planini çalıştır.

    Her adım sirasiyla yürütülür; bagimliliklari karsilanmayan
    adimlar atlanir.
    """
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")

    try:
        from app.domains.ai.qa_orchestrator import QAOrchestrator
        orchestrator = QAOrchestrator(db=db, project_id=project_id)
        result = orchestrator.act(plan_id=plan_id)
        if "error" in result:
            raise HTTPException(404, result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        _logger.exception("QA plan yurutme hatasi")
        raise HTTPException(500, f"QA execute hatasi: {str(e)[:300]}")


@router.post("/qa/verify/{plan_id}")
def qa_verify_plan(
    plan_id: str,
    db: DB,
    user: CurrentUser,
    project_id: str = "",
):
    """
    Plan sonuclarini dogrula — onceki/sonraki karsilastirma,
    kalite puani ve sonraki adım onerileri.
    """
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")

    try:
        from app.domains.ai.qa_orchestrator import QAOrchestrator
        orchestrator = QAOrchestrator(db=db, project_id=project_id)
        result = orchestrator.verify(plan_id=plan_id)
        if "error" in result:
            raise HTTPException(404, result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        _logger.exception("QA dogrulama hatasi")
        raise HTTPException(500, f"QA verify hatasi: {str(e)[:300]}")


@router.post("/qa/full-cycle")
def qa_full_cycle(
    body: QAPlanRequest,
    db: DB,
    user: CurrentUser,
    project_id: str = "",
):
    """
    Tam Plan -> Act -> Verify dongusu çalıştır.

    Tek bir istekle otonom QA dongusu baslatir ve tamamlar.
    """
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")

    try:
        from app.domains.ai.qa_orchestrator import QAOrchestrator
        orchestrator = QAOrchestrator(db=db, project_id=project_id)
        result = orchestrator.run_full_cycle(goal=body.goal, context=body.context)
        return result
    except Exception as e:
        _logger.exception("QA full-cycle hatasi")
        raise HTTPException(500, f"QA full-cycle hatasi: {str(e)[:300]}")


@router.post("/qa/explore")
def qa_explore(
    body: QAExploreRequest,
    db: DB,
    user: CurrentUser,
    project_id: str = "",
):
    """
    Otonom keşif modu — tüm endpoint'leri analiz eder,
    test edilmemis/yetersiz test edilmis olanlari bulur,
    test planlari uretir, calistirir ve dogrular.
    """
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")

    try:
        from app.domains.ai.qa_orchestrator import QAOrchestrator
        orchestrator = QAOrchestrator(db=db, project_id=project_id)
        result = orchestrator.explore(spec_id=body.spec_id)
        return result
    except Exception as e:
        _logger.exception("QA explore hatasi")
        raise HTTPException(500, f"QA explore hatasi: {str(e)[:300]}")


@router.get("/qa/status/{plan_id}")
def qa_plan_status(
    plan_id: str,
    user: CurrentUser,
):
    """
    QA planinin mevcut durumunu getir — adım ilerlemesi,
    kapsam bilgisi ve dogrulama sonuclari.
    """
    try:
        from app.domains.ai.qa_orchestrator import get_plan_status
        result = get_plan_status(plan_id)
        if "error" in result:
            raise HTTPException(404, result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"QA status hatasi: {str(e)[:300]}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# NL TEST GENERATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.post("/nl-test/generate", response_model=NLTestResponse)
def nl_test_generate(
    body: NLTestRequest,
    db: DB,
    user: CurrentUser,
    project_id: str = "",
):
    """
    Dogal dil aciklamasindan test uretir.

    Turkce veya Ingilizce metin girdisi alip istenen formatta
    (api_test, bdd, pytest, playwright) test ciktisi uretir.
    """
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")

    valid_formats = ("api_test", "bdd", "pytest", "playwright")
    if body.output_format not in valid_formats:
        raise HTTPException(400, "Geçersiz output_format. Izin verilen: %s" % ", ".join(valid_formats))

    try:
        from app.domains.ai.nl_test_generator import NLTestGenerator
        generator = NLTestGenerator(db=db, project_id=project_id)
        result = generator.generate_from_text(
            text=body.text,
            output_format=body.output_format,
            context=body.context,
        )
        return result
    except Exception as e:
        _logger.exception("NL test generation hatasi")
        raise HTTPException(500, f"NL test üretim hatasi: {str(e)[:300]}")


@router.post("/nl-test/batch", response_model=BatchNLResponse)
def nl_test_batch(
    body: BatchNLRequest,
    db: DB,
    user: CurrentUser,
    project_id: str = "",
):
    """
    Birden fazla dogal dil aciklamasindan toplu test uretimi.

    Her metin için ayri sonuç dondurur + toplam özet istatistikleri.
    """
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")

    if len(body.texts) > 50:
        raise HTTPException(400, "Tek seferde en fazla 50 metin gonderilebilir")

    try:
        from app.domains.ai.nl_test_generator import NLTestGenerator
        generator = NLTestGenerator(db=db, project_id=project_id)
        result = generator.batch_generate(
            texts=body.texts,
            output_format=body.output_format,
        )
        return result
    except Exception as e:
        _logger.exception("NL batch generation hatasi")
        raise HTTPException(500, f"NL batch üretim hatasi: {str(e)[:300]}")


@router.post("/nl-test/suggest/{endpoint_id}", response_model=SuggestFromEndpointResponse)
def nl_test_suggest(
    endpoint_id: str,
    db: DB,
    user: CurrentUser,
    project_id: str = "",
    count: int = 5,
):
    """
    Verilen endpoint için dogal dil test aciklamalari öner.

    QA muhendisine \"bu endpoint için su testleri yazabilirsin\" onerileri sunar.
    """
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")

    count = min(max(count, 1), 20)

    try:
        from app.domains.ai.nl_test_generator import NLTestGenerator
        generator = NLTestGenerator(db=db, project_id=project_id)
        result = generator.suggest_from_endpoint(
            endpoint_id=endpoint_id,
            count=count,
        )
        return result
    except Exception as e:
        _logger.exception("NL test suggest hatasi")
        raise HTTPException(500, f"NL suggest hatasi: {str(e)[:300]}")


@router.post("/nl-test/validate")
def nl_test_validate(
    body: ValidateCodeRequest,
    user: CurrentUser,
):
    """
    Uretilen test kodunun syntax dogrulamasini yapar.

    Python için ast.parse(), TypeScript için temel yapisal kontroller.
    """
    valid_languages = ("python", "typescript")
    if body.language not in valid_languages:
        raise HTTPException(400, "Geçersiz language. Izin verilen: %s" % ", ".join(valid_languages))

    try:
        from app.domains.ai.nl_test_generator import NLTestGenerator
        # validate_code is stateless, so we can use a lightweight instance
        from app.infra.database import SessionLocal
        with SessionLocal() as db:
            generator = NLTestGenerator(db=db, project_id="")
            result = generator.validate_code(body.code, body.language)
        return result
    except Exception as e:
        _logger.exception("NL test validate hatasi")
        raise HTTPException(500, f"Kod dogrulama hatasi: {str(e)[:300]}")


# ─────────────────────────────────────────────────────────────────────────────
# B4 — AI Quality Dashboard  GET /api/v1/ai/quality/dashboard
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/quality/dashboard",
    summary="AI Quality dashboard — unified metrics, judge scores, routing & ingestion stats",
    tags=["ai-quality"],
)
def ai_quality_dashboard(
    days: int = 30,
    user: CurrentUser = None,
) -> Dict[str, Any]:
    """Unified dashboard payload consumed by ``apps/web/.../ai-quality/page.tsx``.

    Aggregates:
    * LLM call metrics (overview, by_model, regression alerts, recommendations)
    * Quality-judge scores (correctness, completeness, domain_fit, format)
    * Smart model router state (routing mode, tiers, circuit breakers)
    * RAG ingestion statistics (sources, total docs)
    * Latest eval-suite run

    All sub-calls are defensive — a failing sub-module returns empty data rather
    than a 500, so the dashboard degrades gracefully while the rest still renders.
    """
    days = max(1, min(days, 365))

    # 1. LLM quality metrics (overview, by_model, regressions, recommendations)
    try:
        from app.domains.ai.quality_metrics import get_llm_quality_metrics
        raw = get_llm_quality_metrics(days=days)
    except Exception as exc:
        _logger.warning("quality_metrics unavailable: %s", exc)
        raw = {}

    overview_raw = raw.get("overview", {})
    # Map internal field names → frontend contract
    overview: Dict[str, Any] = {
        "total_calls":          overview_raw.get("total_calls"),
        "success_rate":         overview_raw.get("success_rate"),
        "json_parse_rate":      overview_raw.get("json_parse_rate"),
        "avg_latency_ms":       overview_raw.get("avg_latency_ms"),
        "total_cost_usd":       overview_raw.get("total_cost_usd"),
        "avg_cost_usd":         overview_raw.get("avg_cost_usd"),
        "cost_per_1k_calls_usd": overview_raw.get("cost_per_1k_calls_usd"),
    }

    # by_model: ensure frontend-expected keys exist
    by_model_raw: list = raw.get("by_model", [])
    by_model = [
        {
            "model":           m.get("model", "unknown"),
            "calls":           m.get("calls", 0),
            "success_rate":    m.get("success_rate", 0.0),
            "json_parse_rate": m.get("json_parse_rate", 0.0),
            "avg_latency_ms":  m.get("avg_latency_ms", 0),
            "p95_latency_ms":  m.get("p95_latency_ms", 0),
            "total_cost_usd":  m.get("total_cost_usd"),
            "avg_cost_usd":    m.get("avg_cost_usd"),
        }
        for m in by_model_raw
    ]

    regression_alerts: list = raw.get("regression_alerts", [])
    recommendations: list   = raw.get("recommendations", [])

    # 2. Quality-judge scores
    try:
        from app.domains.ai.quality_judge import get_judge_stats
        judge_raw = get_judge_stats(days=days)
    except Exception as exc:
        _logger.warning("quality_judge unavailable: %s", exc)
        judge_raw = {}

    judge: Dict[str, Any] = {
        "total":              judge_raw.get("total"),
        "avg_overall":        judge_raw.get("avg_overall"),
        "avg_correctness":    judge_raw.get("avg_correctness"),
        "avg_completeness":   judge_raw.get("avg_completeness"),
        "avg_domain_fit":     judge_raw.get("avg_domain_fit"),
        "avg_format_validity": judge_raw.get("avg_format_validity"),
        "by_task":            judge_raw.get("by_task", []),
    }

    # 3. Smart model router state
    try:
        from app.domains.ai.smart_model_router import get_routing_stats, _circuit_state
        routing_raw = get_routing_stats()
        circuit_snapshot = {
            model: {"failures": state[0], "last_failure_ts": int(state[1])}
            for model, state in _circuit_state.items()
        }
    except Exception as exc:
        _logger.warning("smart_model_router unavailable: %s", exc)
        routing_raw = {}
        circuit_snapshot = {}

    routing: Dict[str, Any] = {
        "routing_mode":         routing_raw.get("routing_mode"),
        "tiers":                routing_raw.get("tiers"),
        "provider_availability": routing_raw.get("provider_availability"),
        "fallback_chain":       routing_raw.get("fallback_chain"),
        "circuit_state":        circuit_snapshot,
    }

    # 4. RAG ingestion statistics
    try:
        from app.domains.ai.rag_ingestion import get_ingestion_stats
        ingestion_raw = get_ingestion_stats()
    except Exception as exc:
        _logger.warning("rag_ingestion unavailable: %s", exc)
        ingestion_raw = {}

    ingestion: Dict[str, Any] = {
        "total":   ingestion_raw.get("total"),
        "sources": ingestion_raw.get("sources", []),
    }

    # 5. Latest eval-suite run
    try:
        from app.domains.ai.eval_suite import get_latest_eval_report
        eval_raw = get_latest_eval_report()
    except Exception as exc:
        _logger.warning("eval_suite unavailable: %s", exc)
        eval_raw = {}

    eval_latest: Dict[str, Any] = {
        "suite":      eval_raw.get("suite"),
        "total":      eval_raw.get("total"),
        "pass_count": eval_raw.get("pass_count"),
        "pass_rate":  eval_raw.get("pass_rate"),
        "results":    eval_raw.get("results", []),
    }

    return {
        "period_days":       days,
        "overview":          overview,
        "by_model":          by_model,
        "regression_alerts": regression_alerts,
        "recommendations":   recommendations,
        "judge":             judge,
        "routing":           routing,
        "ingestion":         ingestion,
        "eval_latest":       eval_latest,
    }
