"""Flaky test karantinası — ingest + stabilite skoru + karantina kararı.

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §4 / E2.2.

Çekirdek kavramlar:
    * **pass_rate** = passed / (passed + failed). Skipped bu oran dışı.
    * **flip_count** = son N run'da ardışık status değişikliği. Monoton fail
      flaky DEĞİL, sürekli geçip düşen flaky'dir.
    * **flakiness_score** = f(pass_rate, flip_count) ∈ [0, 1].
      Formül: ``(1 - pass_rate) * 0.5 + (flip_rate) * 0.5``
      flip_rate = flip_count / (runs_count - 1) — ne kadar sık değişti.

Karantina eşikleri (ENV ile ayarlanabilir):
    * MIN_RUNS_FOR_DECISION = 5 — daha az run'da karar verme
    * FLAKINESS_QUARANTINE_THRESHOLD = 0.35
    * FLAKINESS_UNQUARANTINE_THRESHOLD = 0.15  # hysteresis

Hysteresis: karantinaya alırken 0.35+, çıkarırken 0.15- ister. Bu
sayede eşiğin hemen altında oynayan test gidip gelmez.

Karantina süresi:
    Default 5 gün. Dolduğunda test tekrar değerlendirilir; hâlâ flaky ise
    ticket referansı ile hard fail'e geçebilir (E4 sprint'inde).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, List, Literal, Optional, Sequence, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


RunStatus = Literal["passed", "failed", "skipped", "error", "flaky"]

# Hesaba dahil edilen statusler (skipped/error dışarıda)
_COUNTED = {"passed", "failed"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


# ── Pure hesaplama ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StabilityScore:
    runs_count: int
    passed_count: int
    failed_count: int
    flip_count: int
    pass_rate: float
    flakiness_score: float


def compute_stability(statuses: Sequence[str]) -> StabilityScore:
    """Kronolojik olarak eski → yeni sıralı status listesinden skor.

    ``statuses`` dışındaki değerler (skipped/error) yok sayılır ama
    ``runs_count`` **filtrelenmiş** sayıyı ifade eder — flakiness hesabı
    sadece pass/fail üstünden.
    """
    filtered = [s for s in statuses if s in _COUNTED]
    n = len(filtered)
    if n == 0:
        return StabilityScore(0, 0, 0, 0, 0.0, 0.0)

    passed = sum(1 for s in filtered if s == "passed")
    failed = n - passed

    flips = 0
    for i in range(1, n):
        if filtered[i] != filtered[i - 1]:
            flips += 1

    pass_rate = passed / n
    flip_rate = flips / (n - 1) if n > 1 else 0.0
    flakiness = round((1 - pass_rate) * 0.5 + flip_rate * 0.5, 6)

    return StabilityScore(
        runs_count=n,
        passed_count=passed,
        failed_count=failed,
        flip_count=flips,
        pass_rate=round(pass_rate, 6),
        flakiness_score=flakiness,
    )


@dataclass(frozen=True)
class QuarantineDecision:
    should_quarantine: bool
    reason: str
    quarantined_until: Optional[datetime]


def decide_quarantine(
    score: StabilityScore,
    *,
    currently_quarantined: bool,
    now: Optional[datetime] = None,
) -> QuarantineDecision:
    """Hysteresis-li karar.

    Args:
        score: compute_stability sonucu
        currently_quarantined: önceki state — hysteresis için
        now: zaman kaynağı (test için injectable)
    """
    now = now or datetime.now(timezone.utc)
    min_runs = _env_int("FLAKY_MIN_RUNS", 5)
    q_thr = _env_float("FLAKY_QUARANTINE_THRESHOLD", 0.35)
    unq_thr = _env_float("FLAKY_UNQUARANTINE_THRESHOLD", 0.15)
    q_days = _env_int("FLAKY_QUARANTINE_DAYS", 5)

    if score.runs_count < min_runs:
        return QuarantineDecision(
            should_quarantine=currently_quarantined,
            reason="insufficient_runs",
            quarantined_until=None,
        )

    if currently_quarantined:
        # Çıkma eşiği
        if score.flakiness_score <= unq_thr and score.pass_rate >= 0.90:
            return QuarantineDecision(
                should_quarantine=False,
                reason="recovered",
                quarantined_until=None,
            )
        return QuarantineDecision(
            should_quarantine=True,
            reason="still_flaky",
            quarantined_until=now + timedelta(days=q_days),
        )
    else:
        if score.flakiness_score >= q_thr:
            return QuarantineDecision(
                should_quarantine=True,
                reason="threshold_exceeded",
                quarantined_until=now + timedelta(days=q_days),
            )
        return QuarantineDecision(
            should_quarantine=False,
            reason="stable",
            quarantined_until=None,
        )


# ── Pydantic wire models ──────────────────────────────────────────────────


class IngestItem(BaseModel):
    project_id: Optional[str] = None
    test_key: str = Field(min_length=1, description="Dosya::test veya TR::senaryo")
    test_name: Optional[str] = None
    env: str = Field(default="ci", max_length=32)
    status: RunStatus
    duration_ms: Optional[int] = Field(default=None, ge=0)
    error_message: Optional[str] = None
    run_id: Optional[str] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    ts: Optional[datetime] = None


class IngestRequest(BaseModel):
    """Bir batch'te birden fazla test sonucu gönder (CI tarafı için pratik)."""

    events: List[IngestItem] = Field(min_length=1, max_length=500)


class StabilityRow(BaseModel):
    project_id: Optional[str] = None
    test_key: str
    env: str
    runs_count: int
    passed_count: int
    failed_count: int
    flip_count: int
    pass_rate: float
    flakiness_score: float
    is_quarantined: bool
    quarantined_at: Optional[datetime] = None
    quarantined_until: Optional[datetime] = None
    last_ticket_key: Optional[str] = None
    last_run_ts: Optional[datetime] = None
    updated_at: datetime


# ── DB katmanı ─────────────────────────────────────────────────────────────


def _get_conn():
    from app.domains.ai.llm_trace import _get_conn as _base  # type: ignore
    return _base()


def ingest_events(events: Sequence[IngestItem]) -> int:
    """Batch insert — etkilenen test key'leri dönebiliriz ama şimdilik count.

    Her insert sonrası kendi test_key'inin stabilite skoru tetiklenir.
    """
    if not events:
        return 0

    conn = _get_conn()
    touched: set[tuple] = set()
    try:
        with conn.cursor() as cur:
            for ev in events:
                cur.execute(
                    """
                    INSERT INTO test_run_events
                        (project_id, test_key, test_name, env, status,
                         duration_ms, error_message, run_id, branch, commit_sha, ts)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, now()))
                    """,
                    (
                        ev.project_id,
                        ev.test_key,
                        ev.test_name,
                        ev.env,
                        ev.status,
                        ev.duration_ms,
                        (ev.error_message or "")[:4000] or None,
                        ev.run_id,
                        ev.branch,
                        ev.commit_sha,
                        ev.ts,
                    ),
                )
                touched.add((ev.project_id, ev.test_key, ev.env))
    finally:
        conn.close()

    # Her touched için stabilite skorunu güncelle
    for project_id, test_key, env in touched:
        try:
            refresh_stability(project_id, test_key, env)
        except Exception as exc:  # pragma: no cover - DB hata izolasyonu
            logger.warning(
                "flaky: refresh_stability başarısız (%s/%s/%s): %s",
                project_id, test_key, env, exc,
            )

    return len(events)


def refresh_stability(
    project_id: Optional[str], test_key: str, env: str = "ci"
) -> StabilityRow:
    """Son N koşumu oku, skoru hesapla, DB'de upsert."""
    window = _env_int("FLAKY_WINDOW", 20)

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status, ts FROM test_run_events
                WHERE (%s::VARCHAR IS NULL AND project_id IS NULL OR project_id = %s)
                  AND test_key = %s AND env = %s
                ORDER BY ts DESC
                LIMIT %s
                """,
                (project_id, project_id, test_key, env, window),
            )
            rows = cur.fetchall()

        # ORDER BY DESC ile geldi → kronolojik için ters çevir
        statuses = [r[0] for r in reversed(rows)]
        last_ts = rows[0][1] if rows else None
        score = compute_stability(statuses)

        # Mevcut row'u oku (quarantine state için)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT is_quarantined FROM test_stability_scores
                WHERE (%s::VARCHAR IS NULL AND project_id IS NULL OR project_id = %s)
                  AND test_key = %s AND env = %s
                """,
                (project_id, project_id, test_key, env),
            )
            existing = cur.fetchone()
        currently_q = bool(existing[0]) if existing else False

        decision = decide_quarantine(score, currently_quarantined=currently_q)

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO test_stability_scores
                    (project_id, test_key, env, window_size,
                     runs_count, passed_count, failed_count, flip_count,
                     pass_rate, flakiness_score,
                     is_quarantined, quarantined_at, quarantined_until,
                     last_run_ts, updated_at)
                VALUES (%s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s,
                        %s,
                        CASE WHEN %s THEN now() ELSE NULL END,
                        %s,
                        %s, now())
                ON CONFLICT (project_id, test_key, env) DO UPDATE SET
                    window_size        = EXCLUDED.window_size,
                    runs_count         = EXCLUDED.runs_count,
                    passed_count       = EXCLUDED.passed_count,
                    failed_count       = EXCLUDED.failed_count,
                    flip_count         = EXCLUDED.flip_count,
                    pass_rate          = EXCLUDED.pass_rate,
                    flakiness_score    = EXCLUDED.flakiness_score,
                    is_quarantined     = EXCLUDED.is_quarantined,
                    quarantined_at     = CASE
                        WHEN EXCLUDED.is_quarantined AND NOT test_stability_scores.is_quarantined
                            THEN now()
                        WHEN NOT EXCLUDED.is_quarantined
                            THEN NULL
                        ELSE test_stability_scores.quarantined_at
                    END,
                    quarantined_until  = EXCLUDED.quarantined_until,
                    last_run_ts        = COALESCE(EXCLUDED.last_run_ts, test_stability_scores.last_run_ts),
                    updated_at         = now()
                RETURNING project_id, test_key, env, runs_count, passed_count,
                          failed_count, flip_count, pass_rate, flakiness_score,
                          is_quarantined, quarantined_at, quarantined_until,
                          last_ticket_key, last_run_ts, updated_at
                """,
                (
                    project_id, test_key, env, window,
                    score.runs_count, score.passed_count, score.failed_count, score.flip_count,
                    score.pass_rate, score.flakiness_score,
                    decision.should_quarantine,
                    decision.should_quarantine,
                    decision.quarantined_until,
                    last_ts,
                ),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    return _row_to_stability(row)


def list_top_flaky(
    *, limit: int = 10, only_quarantined: bool = False
) -> List[StabilityRow]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            q = """
                SELECT project_id, test_key, env, runs_count, passed_count,
                       failed_count, flip_count, pass_rate, flakiness_score,
                       is_quarantined, quarantined_at, quarantined_until,
                       last_ticket_key, last_run_ts, updated_at
                FROM test_stability_scores
                WHERE runs_count >= 5
            """
            if only_quarantined:
                q += " AND is_quarantined = TRUE"
            q += " ORDER BY flakiness_score DESC LIMIT %s"
            cur.execute(q, (limit,))
            rows = cur.fetchall()
    finally:
        conn.close()
    return [_row_to_stability(r) for r in rows]


def get_stability(
    project_id: Optional[str], test_key: str, env: str = "ci"
) -> Optional[StabilityRow]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT project_id, test_key, env, runs_count, passed_count,
                       failed_count, flip_count, pass_rate, flakiness_score,
                       is_quarantined, quarantined_at, quarantined_until,
                       last_ticket_key, last_run_ts, updated_at
                FROM test_stability_scores
                WHERE (%s::VARCHAR IS NULL AND project_id IS NULL OR project_id = %s)
                  AND test_key = %s AND env = %s
                """,
                (project_id, project_id, test_key, env),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    return _row_to_stability(row) if row else None


def is_quarantined(
    project_id: Optional[str], test_key: str, env: str = "ci"
) -> bool:
    """Runner'ın hızlı kullanacağı tek-bool sorgu."""
    row = get_stability(project_id, test_key, env)
    if not row:
        return False
    if not row.is_quarantined:
        return False
    # Süresi dolduysa de-quarantine; DB update bir sonraki refresh'te olur
    if row.quarantined_until and row.quarantined_until < datetime.now(timezone.utc):
        return False
    return True


def _row_to_stability(row: Any) -> StabilityRow:
    return StabilityRow(
        project_id=row[0],
        test_key=row[1],
        env=row[2],
        runs_count=int(row[3] or 0),
        passed_count=int(row[4] or 0),
        failed_count=int(row[5] or 0),
        flip_count=int(row[6] or 0),
        pass_rate=float(row[7] or 0),
        flakiness_score=float(row[8] or 0),
        is_quarantined=bool(row[9]),
        quarantined_at=row[10],
        quarantined_until=row[11],
        last_ticket_key=row[12],
        last_run_ts=row[13],
        updated_at=row[14],
    )
