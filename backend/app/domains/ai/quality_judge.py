"""
LLM-as-Judge — LLM ciktilari için 4 boyutlu skorlama.

Skorlar (0-10): correctness, completeness, domain_fit, format_validity.
Judge modeli: route_model("quality_judge") -> PREMIUM (claude-sonnet-4).

Feature flag: ``ai.judge.enabled`` (default False). Acilirsa sampling'e gore
otomatik skorlar DB'ye yazilir (llm_judge_runs).
"""

from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import dataclass
from typing import Any, Optional

from app.domains.ai.gateway_client import gateway_complete
from app.domains.ai.smart_model_router import route_model

logger = logging.getLogger(__name__)


_SAMPLING_RATES: dict[str, float] = {
    "security_audit": 1.00,
    "quality_judge": 0.00,
    "test_generation": 0.05,
    "chain_builder": 0.10,
    "code_generation": 0.05,
    "spec_analysis": 0.05,
    "chat": 0.02,
    "default": 0.05,
}


@dataclass
class JudgeResult:
    correctness: float
    completeness: float
    domain_fit: float
    format_validity: float
    overall: float
    rationale: str
    judge_model: str
    sampled: bool = True


_JUDGE_SYSTEM_PROMPT = """Sen bir Turkce konusan kidemli QA denetcisisin.
Gorevin bir LLM ciktisini 4 boyutta (0-10) skorlamak.

Boyutlar:
1. correctness     — Cevap dogru mu? (0: yanlis, 10: mukemmel)
2. completeness    — Sorunun tüm parcalari ele alindi mi?
3. domain_fit      — Bankacilik/test otomasyon domaine uygun mu? (Turkce terimler, BDDK/KVKK/MASAK/PCI-DSS)
4. format_validity — Beklenen format (JSON, gherkin, markdown) gecerli mi?

Ciktiyi SADECE asagidaki JSON formatinda ver:
{
  "correctness": <0-10>,
  "completeness": <0-10>,
  "domain_fit": <0-10>,
  "format_validity": <0-10>,
  "rationale": "<tek cumle>"
}

ASLA baska metin, markdown baslik, veya yorum ekleme."""


def _judge_enabled(tenant_id: Optional[str] = None) -> bool:
    """Feature flag: ai.judge.enabled — default False."""
    try:
        from app.domains.feature_flags.service import feature_flags
        return feature_flags.is_enabled("ai.judge.enabled", tenant_id=tenant_id, default=False)
    except Exception:
        return False


def _should_sample(task_type: str, force: bool = False, tenant_id: Optional[str] = None) -> bool:
    if force:
        return True
    if not _judge_enabled(tenant_id):
        return False
    rate = _SAMPLING_RATES.get(task_type, _SAMPLING_RATES["default"])
    return random.random() < rate


def judge_output(
    task_type: str,
    user_prompt: str,
    response: str,
    *,
    reference: Optional[str] = None,
    trace_id: Optional[int] = None,
    judged_model: Optional[str] = None,
    force: bool = False,
) -> Optional[JudgeResult]:
    """LLM ciktisini skorla. Sampling/flag'e takilirsa None doner."""
    if not _should_sample(task_type, force=force):
        return None

    if not response or len(response.strip()) < 20:
        return None

    try:
        rec = route_model("quality_judge")
        judge_model = rec.model
    except Exception as exc:
        logger.debug("judge_output router hatasi: %s", exc)
        return None

    user_content = (
        f"Task tipi: {task_type}\n\n"
        f"Kullanıcı Istegi:\n{user_prompt[:2000]}\n\n"
        f"Degerlendirilecek Cevap:\n{response[:3000]}"
    )
    if reference:
        user_content += f"\n\nAltin Referans Cevap:\n{reference[:2000]}"

    try:
        raw = gateway_complete(
            task_type="quality_judge",
            user_message=user_content,
            system_message=_JUDGE_SYSTEM_PROMPT,
            temperature=rec.temperature,
            max_tokens=min(rec.max_tokens, 1024),
            json_mode=True,
            model_override=judge_model,
        )
    except Exception as exc:
        logger.debug("judge_output gateway hatasi: %s", exc)
        return None

    parsed = _parse_judge_json(raw)
    if not parsed:
        return None

    correctness = _clip(parsed.get("correctness", 0))
    completeness = _clip(parsed.get("completeness", 0))
    domain_fit = _clip(parsed.get("domain_fit", 0))
    format_validity = _clip(parsed.get("format_validity", 0))
    rationale = str(parsed.get("rationale", ""))[:500]

    overall = round(
        correctness * 0.35 + completeness * 0.25 + domain_fit * 0.25 + format_validity * 0.15,
        2,
    )

    result = JudgeResult(
        correctness=correctness,
        completeness=completeness,
        domain_fit=domain_fit,
        format_validity=format_validity,
        overall=overall,
        rationale=rationale,
        judge_model=judge_model,
        sampled=True,
    )

    _persist_judge_run(
        trace_id=trace_id,
        task_type=task_type,
        judged_model=judged_model or "unknown",
        judge_model=judge_model,
        result=result,
    )
    return result


def _clip(value: Any) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(10.0, round(v, 2)))


def _parse_judge_json(raw: str) -> Optional[dict]:
    text = (raw or "").strip()
    fence = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            pass
    return None


def _persist_judge_run(
    trace_id: Optional[int],
    task_type: str,
    judged_model: str,
    judge_model: str,
    result: JudgeResult,
) -> None:
    """llm_judge_runs tablosuna kaydet. Sessiz."""
    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'llm_judge_runs')"
                )
                row = cur.fetchone()
                if not row or not row[0]:
                    return
                cur.execute(
                    """
                    INSERT INTO llm_judge_runs
                        (trace_id, task_type, judged_model, judge_model,
                         correctness, completeness, domain_fit, format_validity,
                         overall, rationale, sampled)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        trace_id, task_type, judged_model, judge_model,
                        result.correctness, result.completeness,
                        result.domain_fit, result.format_validity,
                        result.overall, result.rationale, result.sampled,
                    ),
                )
        finally:
            conn.close()
    except Exception as exc:
        logger.debug("llm_judge_runs kayit hatasi: %s", exc)


def get_judge_stats(days: int = 7) -> dict[str, Any]:
    """Son N gun judge özet — /ai/quality/dashboard için."""
    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
    except Exception:
        return {"total": 0, "by_task": [], "by_model": []}

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'llm_judge_runs')"
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return {"total": 0, "by_task": [], "by_model": []}

            cur.execute(
                """
                SELECT COUNT(*), AVG(overall), AVG(correctness),
                       AVG(completeness), AVG(domain_fit), AVG(format_validity)
                FROM llm_judge_runs
                WHERE created_at > NOW() - INTERVAL %s
                """,
                (f"{int(days)} days",),
            )
            r = cur.fetchone()
            total = r[0] or 0

            cur.execute(
                """
                SELECT task_type, COUNT(*) AS n, AVG(overall)
                FROM llm_judge_runs
                WHERE created_at > NOW() - INTERVAL %s
                GROUP BY task_type
                ORDER BY n DESC
                """,
                (f"{int(days)} days",),
            )
            by_task = [
                {"task_type": r2[0], "count": r2[1], "avg_overall": round(float(r2[2] or 0), 2)}
                for r2 in cur.fetchall()
            ]

            cur.execute(
                """
                SELECT judged_model, COUNT(*) AS n, AVG(overall)
                FROM llm_judge_runs
                WHERE created_at > NOW() - INTERVAL %s
                GROUP BY judged_model
                ORDER BY n DESC
                LIMIT 10
                """,
                (f"{int(days)} days",),
            )
            by_model = [
                {"model": r2[0], "count": r2[1], "avg_overall": round(float(r2[2] or 0), 2)}
                for r2 in cur.fetchall()
            ]

            return {
                "total": total,
                "avg_overall": round(float(r[1] or 0), 2),
                "avg_correctness": round(float(r[2] or 0), 2),
                "avg_completeness": round(float(r[3] or 0), 2),
                "avg_domain_fit": round(float(r[4] or 0), 2),
                "avg_format_validity": round(float(r[5] or 0), 2),
                "by_task": by_task,
                "by_model": by_model,
                "period_days": days,
            }
    except Exception as exc:
        logger.debug("get_judge_stats hatasi: %s", exc)
        return {"total": 0, "by_task": [], "by_model": [], "error": str(exc)}
    finally:
        try:
            conn.close()
        except Exception:
            pass
