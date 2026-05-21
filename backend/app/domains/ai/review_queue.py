"""
Human-in-the-Loop Review Queue — dusuk confidence LLM kararlarini insan onayina yolla.

Ihtiyac (banking governance):
    - LLM bir test case urettiginde "%40 eminim bu dogru" diyorsa otomatik
      approve etmek riskli.
    - Kritik task'lerde (security_audit, compliance) her karar + insan gozu lazim.
    - KVKK/BDDK denetimleri icin "kim onayladi, ne zaman" audit trail.

Yapi:
    1. LLM cevabindan confidence skor cikart (varsa <confidence>0.XX</confidence>)
    2. Confidence < esik OR task_type her zaman review gerektiriyor -> review_queue'ya at
    3. UI: admin paneli bekleyen kararlari listeler, approve/reject/edit
    4. Approve -> caller'a sonuc gider. Reject -> audit log, caller exception alir.

Tablo: llm_review_queue (migration 0007)
Flag: ai.review.queue — default False (staging'de test sonrasi ac)
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Task-bazli esikler ──────────────────────────────────────────────────


# Her task_type icin:
#   always_review: True -> tum cagrilar review'a gider (compliance)
#   confidence_threshold: float -> confidence bu deger altinda ise review
_TASK_CONFIG: dict[str, dict[str, Any]] = {
    "security_audit": {"always_review": True, "confidence_threshold": 1.0},
    "test_generation": {"always_review": False, "confidence_threshold": 0.6},
    "chain_builder": {"always_review": False, "confidence_threshold": 0.7},
    "spec_analysis": {"always_review": False, "confidence_threshold": 0.5},
    "code_generation": {"always_review": False, "confidence_threshold": 0.5},
    "default": {"always_review": False, "confidence_threshold": 0.4},
}


# ── Confidence extraction ───────────────────────────────────────────────


_CONF_PATTERNS = [
    re.compile(r"<confidence>\s*([01]?\.\d+|[01])\s*</confidence>", re.I),
    re.compile(r'"confidence"\s*:\s*([01]?\.\d+|[01])'),
    re.compile(r"(?:confidence|guven)[:=\s]+([01]?\.\d+|[01])", re.I),
]


def extract_confidence(response: str) -> Optional[float]:
    """LLM cevabindan confidence skor cikart (0.0-1.0). Yoksa None.

    Destekler:
      - <confidence>0.8</confidence>
      - {"confidence": 0.8, ...}
      - "confidence: 0.8"
    """
    if not response:
        return None
    for pat in _CONF_PATTERNS:
        m = pat.search(response)
        if m:
            try:
                val = float(m.group(1))
                return max(0.0, min(1.0, val))
            except (ValueError, TypeError):
                continue
    return None


# ── Karar fonksiyonu ─────────────────────────────────────────────────────


def should_queue_for_review(
    task_type: str,
    response: str,
    *,
    judge_overall: Optional[float] = None,
    tenant_id: Optional[str] = None,
) -> tuple[bool, str, Optional[float]]:
    """
    Bu cevabi review_queue'ya atmaliyiz mi?

    Returns:
        (queue, reason, extracted_confidence)
    """
    if not _queue_enabled(tenant_id):
        return False, "flag_disabled", None

    config = _TASK_CONFIG.get(task_type, _TASK_CONFIG["default"])

    # 1) Her zaman review
    if config.get("always_review"):
        return True, f"task_{task_type}_always_review", None

    # 2) Confidence dusuk
    conf = extract_confidence(response)
    if conf is not None and conf < config["confidence_threshold"]:
        return True, f"low_confidence_{conf:.2f}", conf

    # 3) Judge skoru dusuk (varsa)
    if judge_overall is not None and judge_overall < 6.0:
        return True, f"low_judge_score_{judge_overall:.1f}", conf

    return False, "passed", conf


def _queue_enabled(tenant_id: Optional[str] = None) -> bool:
    """Feature flag: ai.review.queue — default False."""
    try:
        from app.domains.feature_flags.service import feature_flags
        return feature_flags.is_enabled("ai.review.queue", tenant_id=tenant_id, default=False)
    except Exception:
        return False


# ── DB operations ────────────────────────────────────────────────────────


def enqueue(
    task_type: str,
    user_prompt: str,
    response: str,
    *,
    reason: str,
    confidence: Optional[float] = None,
    judge_overall: Optional[float] = None,
    project_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Optional[str]:
    """Review kuyruga ekle. ID doner, hata olursa None."""
    try:
        from app.domains.ai.llm_trace import _get_conn
        from app.domains.ai.correlation import get_correlation_id
        conn = _get_conn()
    except Exception:
        return None

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'llm_review_queue')"
            )
            if not cur.fetchone()[0]:
                logger.debug("llm_review_queue tablosu yok — migration gerek")
                return None

            review_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO llm_review_queue
                    (id, task_type, user_prompt, response, reason,
                     confidence, judge_overall, status, project_id,
                     correlation_id, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s)
                """,
                (
                    review_id,
                    task_type,
                    user_prompt[:5000],
                    response[:10000],
                    reason,
                    confidence,
                    judge_overall,
                    project_id,
                    get_correlation_id(),
                    tenant_id,
                ),
            )
            return review_id
    except Exception as exc:
        logger.debug("review_queue enqueue hatasi: %s", exc)
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def list_pending(limit: int = 50) -> list[dict[str, Any]]:
    """Bekleyen review kayitlarini listele (admin UI icin)."""
    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
    except Exception:
        return []

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'llm_review_queue')"
            )
            if not cur.fetchone()[0]:
                return []
            cur.execute(
                """
                SELECT id, task_type, user_prompt, response, reason,
                       confidence, judge_overall, project_id, created_at
                FROM llm_review_queue
                WHERE status = 'pending'
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall() or []
            return [
                {
                    "id": r[0],
                    "task_type": r[1],
                    "user_prompt": (r[2] or "")[:500],
                    "response": (r[3] or "")[:1000],
                    "reason": r[4],
                    "confidence": float(r[5]) if r[5] is not None else None,
                    "judge_overall": float(r[6]) if r[6] is not None else None,
                    "project_id": r[7],
                    "created_at": r[8].isoformat() if r[8] else None,
                }
                for r in rows
            ]
    except Exception as exc:
        logger.debug("list_pending hatasi: %s", exc)
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def resolve(
    review_id: str,
    decision: str,
    *,
    reviewer: str,
    edited_response: Optional[str] = None,
    comment: Optional[str] = None,
) -> bool:
    """
    Review kararini uygula.

    Args:
        review_id:        UUID
        decision:         "approved" | "rejected" | "edited"
        reviewer:         Kim onayladi (user id/email)
        edited_response:  decision='edited' ise yeni cevap
        comment:          Aciklama

    Returns: True basarili
    """
    if decision not in ("approved", "rejected", "edited"):
        return False

    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
    except Exception:
        return False

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE llm_review_queue
                SET status = %s,
                    reviewer = %s,
                    reviewed_at = now(),
                    review_comment = %s,
                    edited_response = %s
                WHERE id = %s AND status = 'pending'
                RETURNING id
                """,
                (decision, reviewer, comment, edited_response, review_id),
            )
            return cur.fetchone() is not None
    except Exception as exc:
        logger.debug("review resolve hatasi: %s", exc)
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def queue_stats(days: int = 7) -> dict[str, Any]:
    """Dashboard: pending/approved/rejected sayilari + avg bekleme."""
    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
    except Exception:
        return {"enabled": False}

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'llm_review_queue')"
            )
            if not cur.fetchone()[0]:
                return {"enabled": False}
            cur.execute(
                """
                SELECT status, COUNT(*) as cnt
                FROM llm_review_queue
                WHERE created_at > NOW() - INTERVAL %s
                GROUP BY status
                """,
                (f"{int(days)} days",),
            )
            by_status = {r[0]: r[1] for r in cur.fetchall() or []}

            cur.execute(
                """
                SELECT AVG(EXTRACT(EPOCH FROM (reviewed_at - created_at)))
                FROM llm_review_queue
                WHERE reviewed_at IS NOT NULL
                  AND created_at > NOW() - INTERVAL %s
                """,
                (f"{int(days)} days",),
            )
            avg_wait = cur.fetchone()[0]

            return {
                "enabled": True,
                "by_status": by_status,
                "avg_wait_secs": float(avg_wait) if avg_wait else None,
                "period_days": days,
            }
    except Exception as exc:
        return {"enabled": False, "error": str(exc)}
    finally:
        try:
            conn.close()
        except Exception:
            pass
