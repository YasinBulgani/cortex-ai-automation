"""AI Chat endpoints — sessions and messages."""

from __future__ import annotations

from typing import List, Optional

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
    """Kullanicinin guncel LLM kullanim durumunu dondurur (rate limit bilgisi)."""
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
    Streaming chat endpoint — Server-Sent Events (SSE) ile token token yanit gonderir.

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

    # ── Kullanici mesajini kaydet ────────────────────────────────────
    user_msg = AiChatMessage(session_id=session_id, role="user", content=body.content)
    db.add(user_msg)
    db.flush()
    user_msg_id = user_msg.id

    # ── Gecmis mesajlari al ──────────────────────────────────────────
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
        _logger.error("Assistant mesaji kaydedilemedi: %s", e)


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
    if provider not in ("openai", "anthropic", "ollama"):
        raise HTTPException(400, "Gecersiz provider. 'openai', 'anthropic' veya 'ollama' olmali.")
    configured = {
        "openai": bool(s.openai_api_key),
        "anthropic": bool(s.anthropic_api_key),
        "ollama": bool(s.ollama_base_url),
    }
    if not configured.get(provider):
        raise HTTPException(400, f"{provider} provider'i yapilandirilmamis.")
    if provider != s.ai_provider:
        raise HTTPException(
            409,
            "Runtime provider switching devre disi. AI_PROVIDER ortam degiskenini guncelleyip backend servisini yeniden baslatin.",
        )
    return {
        "active": s.ai_provider,
        "changed": False,
        "runtime_switch_supported": False,
        "note": "Aktif provider deployment konfigurasyonundan okunuyor.",
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
    LLM kalite metriklerini getir — basari orani, latency, hata dagilimi, trend.

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
def llm_trace_stats(user: CurrentUser, project_id: str = ""):
    """LLM trace ozet istatistikleri."""
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    from app.deps import _user_permissions
    from app.domains.ai.llm_trace import get_trace_stats_scoped

    perms = _user_permissions(user)
    scoped_user_id = None if "admin.*" in perms else str(user.id)
    return get_trace_stats_scoped(project_id=project_id, user_id=scoped_user_id)


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


# QA orchestration + natural-language test generation endpoints are split out.
router.include_router(qa_nl_router)
