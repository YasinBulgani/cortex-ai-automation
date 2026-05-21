"""
Nexus QA — AI Pipeline Orkestratörü

Çok adımlı AI iş akışını yönetir:
  1. analyze_document  → Modül + risk analizi (JSON)
  2. generate_test_cases → Test case'leri üret (JSON)
  3. generate_gherkin   → Gherkin feature dosyası
  4. generate_playwright → Playwright TypeScript testi

Her adım önceki adımın çıktısını bağlam olarak kullanır.
SSE formatında adım adım progress eventi yield eder.

Kullanım (route'dan):
    async for event in run_pipeline(request, steps):
        yield f"data: {json.dumps(event)}\\n\\n"
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import AsyncGenerator

from app.core.json_repair import repair_json_safe
from app.core.models import AIRequest, Message, TaskType, ProviderName
from app.core.prompts import get_system_prompt
from app.core.router import ai_router

logger = logging.getLogger(__name__)

# Pipeline adım sırası — hepsi veya subset çalıştırılabilir
ALL_STEPS: list[str] = [
    "analyze_document",
    "generate_test_cases",
    "generate_gherkin",
    "generate_playwright",
]

# Adım → TaskType eşlemesi
_STEP_TO_TASK: dict[str, TaskType] = {
    "analyze_document":    TaskType.ANALYZE_DOCUMENT,
    "generate_test_cases": TaskType.GENERATE_TEST_CASES,
    "generate_gherkin":    TaskType.GENERATE_GHERKIN,
    "generate_playwright": TaskType.GENERATE_PLAYWRIGHT,
}


def _make_event(
    step: str,
    status: str,
    content: str = "",
    error: str = "",
    elapsed_ms: int = 0,
    pipeline_id: str = "",
) -> dict:
    return {
        "pipeline_id": pipeline_id,
        "step":        step,
        "status":      status,   # "started" | "completed" | "failed"
        "content":     content,
        "error":       error,
        "elapsed_ms":  elapsed_ms,
    }


async def _ai_call(task_type: TaskType, messages: list[Message]) -> str:
    """Gateway üzerinden tek AI çağrısı.

    temperature ve max_tokens None → model_post_init görev tipine göre atar.
    """
    request = AIRequest(
        task_type=task_type,
        messages=messages,
        provider=ProviderName.AUTO,
        # None: model_post_init her görev için doğru temperature/max_tokens'ı seçer
        temperature=None,
        max_tokens=None,
    )
    response = await ai_router.route(request)
    return response.content


def _build_messages_for_step(
    step: str,
    document: str,
    previous_outputs: dict[str, str],
) -> list[Message]:
    """
    Her adım için mesaj listesi oluştur.
    Önceki adımların çıktıları bağlam olarak eklenir.
    """
    task_type = _STEP_TO_TASK[step]
    system_content = get_system_prompt(task_type)

    # Önceki adımların çıktısını context'e ekle
    context_parts: list[str] = []
    if step == "analyze_document":
        context_parts.append(f"Doküman:\n{document}")
    elif step == "generate_test_cases":
        analysis = previous_outputs.get("analyze_document", "")
        context_parts.append(f"Doküman:\n{document}")
        if analysis:
            context_parts.append(f"Doküman Analizi:\n{analysis}")
        context_parts.append("Yukarıdaki analiz ve dokümanı kullanarak kapsamlı test case'ler üret.")
    elif step == "generate_gherkin":
        test_cases = previous_outputs.get("generate_test_cases", "")
        if test_cases:
            context_parts.append(f"Test Case'ler:\n{test_cases}")
        context_parts.append("Yukarıdaki test case'leri Gherkin BDD formatına çevir.")
    elif step == "generate_playwright":
        gherkin = previous_outputs.get("generate_gherkin", "")
        test_cases = previous_outputs.get("generate_test_cases", "")
        if gherkin:
            context_parts.append(f"Gherkin Senaryoları:\n{gherkin}")
        elif test_cases:
            context_parts.append(f"Test Case'ler:\n{test_cases}")
        context_parts.append("Yukarıdaki senaryolar için Playwright TypeScript testi üret.")

    user_content = "\n\n".join(context_parts)

    return [
        Message(role="system", content=system_content),
        Message(role="user", content=user_content),
    ]


async def run_pipeline(
    document: str,
    steps: list[str] | None = None,
    pipeline_id: str | None = None,
) -> AsyncGenerator[dict, None]:
    """
    Pipeline'ı çalıştır ve her adım için SSE event yield et.

    Args:
        document:    Analiz edilecek doküman metni.
        steps:       Çalıştırılacak adımlar (None → tümü).
        pipeline_id: Korelasyon ID (None → otomatik üretilir).

    Yields:
        dict — SSE event (json.dumps ile serialize edilecek).
    """
    if steps is None:
        steps = ALL_STEPS

    # Geçersiz adımları filtrele
    valid_steps = [s for s in steps if s in _STEP_TO_TASK]
    if not valid_steps:
        yield _make_event("pipeline", "failed", error="Geçerli adım bulunamadı")
        return

    pid = pipeline_id or str(uuid.uuid4())[:8]
    previous_outputs: dict[str, str] = {}

    logger.info("Pipeline başladı. id=%s adımlar=%s", pid, valid_steps)
    yield _make_event("pipeline", "started", pipeline_id=pid,
                      content=json.dumps({"steps": valid_steps}))

    pipeline_start = time.monotonic()

    for step in valid_steps:
        step_start = time.monotonic()
        yield _make_event(step, "started", pipeline_id=pid)
        logger.info("[%s] %s başladı", pid, step)

        try:
            messages = _build_messages_for_step(step, document, previous_outputs)
            task_type = _STEP_TO_TASK[step]
            content = await _ai_call(task_type, messages)

            elapsed = int((time.monotonic() - step_start) * 1000)
            previous_outputs[step] = content

            logger.info("[%s] %s tamamlandı (%dms, %d karakter)", pid, step, elapsed, len(content))
            yield _make_event(step, "completed", content=content,
                              elapsed_ms=elapsed, pipeline_id=pid)

        except Exception as exc:
            elapsed = int((time.monotonic() - step_start) * 1000)
            logger.error("[%s] %s başarısız: %s", pid, step, exc)
            yield _make_event(step, "failed", error=str(exc)[:300],
                              elapsed_ms=elapsed, pipeline_id=pid)
            # Pipeline devam eder — başarısız adım atlanır

    # Eval skoru — pipeline bitince kod/gherkin kalitesini ölç
    eval_results: dict = {}
    try:
        from pathlib import Path
        import sys
        _engine_root = Path(__file__).resolve().parent.parent.parent.parent / "engine"
        if str(_engine_root) not in sys.path:
            sys.path.insert(0, str(_engine_root))
        from evals.scorer import score_pipeline_output
        raw_scores = score_pipeline_output(previous_outputs)
        eval_results = {k: v.to_dict() for k, v in raw_scores.items()}
        logger.info("[%s] Eval skorları: %s", pid,
                    {k: v["score"] for k, v in eval_results.items()})
    except Exception as exc:
        logger.warning("[%s] Eval skoru hesaplanamadı: %s", pid, exc)

    total_ms = int((time.monotonic() - pipeline_start) * 1000)
    logger.info("Pipeline tamamlandı. id=%s toplam=%dms", pid, total_ms)
    yield _make_event(
        "pipeline", "completed",
        pipeline_id=pid,
        elapsed_ms=total_ms,
        content=json.dumps({
            "completed_steps": list(previous_outputs.keys()),
            "eval_scores": eval_results,
        }),
    )
