"""
Extended Streaming Service — Chat disindaki LLM islemlerini de stream eder.

Desteklenen islemler:
  - Senaryo uretimi (stream + JSON parse sonunda)
  - Test sonucu analizi (stream)
  - Test verisi uretimi (stream)
  - CoverUp test uretimi (stream)
  - NL test uretimi (stream)
  - Genel amacli streaming

Her islem iki asamali:
  1. Token stream (UI'a aninda gosterilir)
  2. Toplanan tüm metin JSON olarak parse edilir (islem sonunda)
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncIterator

from app.config import settings

logger = logging.getLogger(__name__)


class StreamingLLMService:
    """Tüm LLM islemlerini streaming destekli yapar."""

    async def stream_scenario_generation(
        self,
        description: str,
        context: str = "",
        count: int = 5,
        project_id: str | None = None,
        user_id: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[dict]:
        """
        Senaryo uretimini stream et.

        Yields:
            {"type": "token", "content": "..."} — Her token chunk
            {"type": "complete", "scenarios": [...]} — Tamamlandiginda parse edilmis JSON
            {"type": "error", "message": "..."} — Hata durumunda
        """
        from app.domains.ai.service import (
            SYSTEM_PROMPT_SCENARIO_GEN, _get_rag_context_async, _parse_json_response,
            async_stream_llm,
        )

        rag = await _get_rag_context_async(
            description,
            sources=["feature_file", "docs"],
            top_k=3,
            project_id=project_id,
        )
        system = SYSTEM_PROMPT_SCENARIO_GEN
        if rag:
            system += f"\n\n## Projedeki Mevcut Senaryo Ornekleri\n{rag}"

        user_content = f"Aciklama: {description}\nIstenen senaryo sayisi: {count}"
        if context:
            user_content += f"\n\nEk Baglam:\n{context}"

        collected = ""
        try:
            async for token in async_stream_llm(
                system,
                user_content,
                temperature=temperature,
                max_tokens=max_tokens,
                _trace_agent="streaming_service",
                _trace_phase="stream_scenario_generation",
                _trace_project_id=project_id,
                _trace_user_id=user_id,
                _trace_task_type="scenario_generation",
            ):
                collected += token
                yield {"type": "token", "content": token}

            # Parse completed text
            try:
                parsed = _parse_json_response(collected)
                yield {"type": "complete", "scenarios": parsed.get("scenarios", [])}
            except Exception:
                yield {"type": "complete", "raw": collected}
        except Exception as exc:
            yield {"type": "error", "message": str(exc)[:500]}

    async def stream_test_analysis(
        self,
        execution_data: str,
        question: str = "",
        project_id: str | None = None,
        user_id: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[dict]:
        """Test sonucu analizini stream et."""
        from app.domains.ai.service import (
            SYSTEM_PROMPT_ANALYSIS, _get_rag_context_async, _parse_json_response,
            async_stream_llm,
        )

        query = question or execution_data[:300]
        rag = await _get_rag_context_async(
            query,
            sources=["insight", "error_pattern"],
            top_k=3,
            project_id=project_id,
        )
        system = SYSTEM_PROMPT_ANALYSIS
        if rag:
            system += f"\n\n## Geçmiş Benzer Durumlar\n{rag}"

        user_content = f"Test Koşu Verileri:\n{execution_data}"
        if question:
            user_content += f"\n\nKullanici Sorusu: {question}"

        collected = ""
        try:
            async for token in async_stream_llm(
                system,
                user_content,
                temperature=temperature,
                max_tokens=max_tokens,
                _trace_agent="streaming_service",
                _trace_phase="stream_test_analysis",
                _trace_project_id=project_id,
                _trace_user_id=user_id,
                _trace_task_type="test_analysis",
            ):
                collected += token
                yield {"type": "token", "content": token}

            try:
                parsed = _parse_json_response(collected)
                yield {"type": "complete", "analysis": parsed}
            except Exception:
                yield {"type": "complete", "raw": collected}
        except Exception as exc:
            yield {"type": "error", "message": str(exc)[:500]}

    async def stream_test_data_generation(
        self,
        description: str,
        columns: list[dict] | None = None,
        row_count: int = 10,
        project_id: str | None = None,
        user_id: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[dict]:
        """Test verisi uretimini stream et."""
        from app.domains.ai.service import (
            SYSTEM_PROMPT_TESTDATA, _parse_json_response, async_stream_llm,
        )

        user_content = f"Aciklama: {description}\nIstenen satir sayisi: {row_count}"
        if columns:
            user_content += f"\n\nMevcut kolon tanimlari:\n{json.dumps(columns, ensure_ascii=False)}"

        collected = ""
        try:
            async for token in async_stream_llm(
                SYSTEM_PROMPT_TESTDATA,
                user_content,
                temperature=temperature,
                max_tokens=max_tokens,
                _trace_agent="streaming_service",
                _trace_phase="stream_test_data_generation",
                _trace_project_id=project_id,
                _trace_user_id=user_id,
                _trace_task_type="test_data_generation",
            ):
                collected += token
                yield {"type": "token", "content": token}

            try:
                parsed = _parse_json_response(collected)
                yield {"type": "complete", "data": parsed}
            except Exception:
                yield {"type": "complete", "raw": collected}
        except Exception as exc:
            yield {"type": "error", "message": str(exc)[:500]}

    async def stream_general(
        self,
        system: str,
        user_content: str,
        *,
        parse_json: bool = False,
        project_id: str | None = None,
        user_id: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[dict]:
        """Genel amacli streaming — herhangi bir LLM islemini stream et."""
        from app.domains.ai.service import _parse_json_response, async_stream_llm

        collected = ""
        try:
            async for token in async_stream_llm(
                system,
                user_content,
                temperature=temperature,
                max_tokens=max_tokens,
                _trace_agent="streaming_service",
                _trace_phase="stream_general",
                _trace_project_id=project_id,
                _trace_user_id=user_id,
                _trace_task_type="general_stream",
            ):
                collected += token
                yield {"type": "token", "content": token}

            if parse_json:
                try:
                    parsed = _parse_json_response(collected)
                    yield {"type": "complete", "data": parsed}
                except Exception:
                    yield {"type": "complete", "raw": collected}
            else:
                yield {"type": "complete", "text": collected}
        except Exception as exc:
            yield {"type": "error", "message": str(exc)[:500]}


# Singleton
_streaming_service = None


def get_streaming_service() -> StreamingLLMService:
    global _streaming_service
    if _streaming_service is None:
        _streaming_service = StreamingLLMService()
    return _streaming_service
