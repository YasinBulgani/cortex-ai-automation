"""Test Intelligence Engine — Neurex QA.

Her test koşusundan öğrenen, risk skorları üreten, ETA tahmin eden,
anomali tespit eden ve tester performansını profilleyen zeka katmanı.

Harici AI çağrısı yoktur; tüm algoritmalar deterministik istatistik tabanlıdır.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as _tz
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.test_management.models import (
    TestCase,
    TestCycle,
    TestManagementProject,
    TestPlan,
    TestRun,
    TestRunCase,
)

# ── Yardımcı ─────────────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(_tz.utc)


SEVERITY_WEIGHT = {"critical": 1.0, "major": 0.7, "minor": 0.4, "trivial": 0.1}
PRIORITY_WEIGHT = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.1}
STATUS_DONE = {"passed", "failed", "blocked", "skipped"}


# ── Veri sınıfları ────────────────────────────────────────────────────────────

@dataclass
class CaseRiskScore:
    case_id: str
    case_key: str
    title: str
    risk_score: float          # 0.0–1.0
    failure_rate: float
    severity_weight: float
    recency_factor: float
    priority_weight: float
    last_status: Optional[str]
    last_failed_at: Optional[datetime]
    recommendation: str        # "run_first" | "run_normal" | "deprioritize"


@dataclass
class TesterProfile:
    user_id: str
    assigned_count: int
    completed_count: int
    remaining_count: int
    avg_duration_seconds: float
    velocity_per_hour: float   # tamamlanan case / saat
    pass_rate: float
    blocked_rate: float
    is_bottleneck: bool
    last_activity_at: Optional[datetime]
    inactive_minutes: float


@dataclass
class ETAPrediction:
    run_id: str
    total_cases: int
    completed_cases: int
    remaining_cases: int
    elapsed_hours: float
    velocity_per_hour: float   # son 1 saatteki hız
    overall_velocity: float    # tüm koşum boyunca
    eta_hours: Optional[float]
    predicted_completion: Optional[datetime]
    confidence: float          # 0.0–1.0
    on_track: bool
    risk_level: str            # "low" | "medium" | "high" | "critical"
    message: str


@dataclass
class Anomaly:
    severity: str              # "warning" | "critical"
    type: str
    title: str
    detail: str
    run_case_id: Optional[str] = None
    user_id: Optional[str] = None
    suggested_action: str = ""


@dataclass
class RunIntelligenceReport:
    run_id: str
    run_name: str
    generated_at: datetime
    eta: ETAPrediction
    testers: list[TesterProfile]
    anomalies: list[Anomaly]
    risk_sorted_remaining: list[CaseRiskScore]
    summary_health: str        # "healthy" | "at_risk" | "critical"
    health_score: float        # 0–100


@dataclass
class ReleaseReadinessPrediction:
    project_id: str
    generated_at: datetime
    will_meet_gate: bool
    confidence: float
    days_to_completion: Optional[float]
    blocking_factors: list[str]
    execution_rate: float
    pass_rate: float
    open_defects: int
    recommendation: str


# ── Ana servis fonksiyonları ──────────────────────────────────────────────────

def compute_case_risk_score(case: TestCase, failure_history: dict[str, Any]) -> CaseRiskScore:
    """Bir test case'inin risk skorunu 0–1 arasında hesaplar.

    Risk = failure_rate×0.40 + severity×0.30 + recency×0.20 + priority×0.10
    """
    total_runs = failure_history.get("total_runs", 0)
    fail_count = failure_history.get("fail_count", 0)

    failure_rate = (fail_count / total_runs) if total_runs > 0 else 0.0

    sev = SEVERITY_WEIGHT.get(case.severity, 0.4)
    pri = PRIORITY_WEIGHT.get(case.priority, 0.4)

    # Son failure'dan bu yana geçen gün — yakın = daha riskli
    recency = 0.0
    if case.last_failed_at:
        days_ago = (_utcnow() - case.last_failed_at.replace(tzinfo=_tz.utc)).days
        recency = max(0.0, 1.0 - days_ago / 30.0)  # 30 günde sıfırlanır

    risk = failure_rate * 0.40 + sev * 0.30 + recency * 0.20 + pri * 0.10
    risk = min(1.0, risk)

    if risk >= 0.70:
        recommendation = "run_first"
    elif risk >= 0.35:
        recommendation = "run_normal"
    else:
        recommendation = "deprioritize"

    return CaseRiskScore(
        case_id=case.id,
        case_key=case.case_key,
        title=case.title,
        risk_score=round(risk, 3),
        failure_rate=round(failure_rate, 3),
        severity_weight=sev,
        recency_factor=round(recency, 3),
        priority_weight=pri,
        last_status=case.last_run_status,
        last_failed_at=case.last_failed_at,
        recommendation=recommendation,
    )


def get_run_intelligence(db: Session, project_id: str, run_id: str) -> RunIntelligenceReport:
    """Bir test koşumu için tam zeka raporu üretir."""

    run = db.execute(select(TestRun).where(TestRun.id == run_id)).scalar_one_or_none()
    if not run:
        raise ValueError(f"Run {run_id} bulunamadı")

    run_cases = db.execute(
        select(TestRunCase).where(TestRunCase.run_id == run_id)
    ).scalars().all()

    eta = _predict_eta(run, run_cases)
    testers = _build_tester_profiles(run_cases)
    anomalies = _detect_anomalies(run, run_cases, testers, eta)
    risk_sorted = _risk_sort_remaining(db, run_cases)

    # Genel sağlık skoru
    critical_anomalies = sum(1 for a in anomalies if a.severity == "critical")
    warning_anomalies = sum(1 for a in anomalies if a.severity == "warning")

    health_score = 100.0
    health_score -= critical_anomalies * 20
    health_score -= warning_anomalies * 8
    if not eta.on_track:
        health_score -= 15
    if eta.risk_level == "critical":
        health_score -= 20
    health_score = max(0.0, min(100.0, health_score))

    if health_score >= 75:
        summary_health = "healthy"
    elif health_score >= 45:
        summary_health = "at_risk"
    else:
        summary_health = "critical"

    return RunIntelligenceReport(
        run_id=run_id,
        run_name=run.name,
        generated_at=_utcnow(),
        eta=eta,
        testers=testers,
        anomalies=anomalies,
        risk_sorted_remaining=risk_sorted,
        summary_health=summary_health,
        health_score=round(health_score, 1),
    )


def _predict_eta(run: TestRun, run_cases: list[TestRunCase]) -> ETAPrediction:
    total = len(run_cases)
    completed = [rc for rc in run_cases if rc.status in STATUS_DONE]
    remaining = total - len(completed)

    # Koşum başlangıcından bu yana geçen süre
    started_at = run.started_at or _utcnow()
    elapsed_hours = max(0.001, (_utcnow() - started_at.replace(tzinfo=_tz.utc)).total_seconds() / 3600)

    overall_velocity = len(completed) / elapsed_hours

    # Son 1 saatteki hız (anlık)
    one_hour_ago = _utcnow() - timedelta(hours=1)
    recent_completed = [
        rc for rc in completed
        if rc.completed_at and rc.completed_at.replace(tzinfo=_tz.utc) >= one_hour_ago
    ]
    recent_velocity = len(recent_completed) / 1.0  # son 1 saat

    # Tahmin için hız: ağırlıklı ortalama (anlık ağırlık 0.6, genel 0.4)
    velocity = recent_velocity * 0.6 + overall_velocity * 0.4 if len(completed) > 0 else 0.0

    eta_hours = None
    predicted_completion = None
    confidence = 0.0

    if velocity > 0 and remaining > 0:
        eta_hours = remaining / velocity
        predicted_completion = _utcnow() + timedelta(hours=eta_hours)

        # Güven: hız varyasyonu küçükse yüksek güven
        durations = [
            rc.duration_seconds for rc in completed if rc.duration_seconds and rc.duration_seconds > 0
        ]
        if len(durations) >= 3:
            mean_d = sum(durations) / len(durations)
            variance = sum((d - mean_d) ** 2 for d in durations) / len(durations)
            cv = math.sqrt(variance) / mean_d if mean_d > 0 else 1.0
            confidence = max(0.1, min(0.95, 1.0 - cv))
        else:
            confidence = 0.4

    # Risk seviyesi
    if remaining == 0:
        risk_level = "low"
        on_track = True
        message = "Tüm case'ler tamamlandı."
    elif velocity == 0:
        risk_level = "critical"
        on_track = False
        message = f"{remaining} case bekliyor, aktif ilerleme yok."
    elif eta_hours and eta_hours <= 8:
        risk_level = "low"
        on_track = True
        message = f"~{eta_hours:.1f} saat içinde tamamlanması bekleniyor."
    elif eta_hours and eta_hours <= 24:
        risk_level = "medium"
        on_track = True
        message = f"~{eta_hours:.0f} saat kaldı — izlemede tutun."
    else:
        risk_level = "high"
        on_track = False
        message = f"Yüksek risk: ~{eta_hours:.0f} saat tahmin ediliyor."

    return ETAPrediction(
        run_id=run.id,
        total_cases=total,
        completed_cases=len(completed),
        remaining_cases=remaining,
        elapsed_hours=round(elapsed_hours, 2),
        velocity_per_hour=round(recent_velocity, 2),
        overall_velocity=round(overall_velocity, 2),
        eta_hours=round(eta_hours, 1) if eta_hours else None,
        predicted_completion=predicted_completion,
        confidence=round(confidence, 2),
        on_track=on_track,
        risk_level=risk_level,
        message=message,
    )


def _build_tester_profiles(run_cases: list[TestRunCase]) -> list[TesterProfile]:
    """Her atanmış tester için performans profili üretir."""
    by_tester: dict[str, list[TestRunCase]] = defaultdict(list)
    unassigned: list[TestRunCase] = []

    for rc in run_cases:
        if rc.assigned_to:
            by_tester[rc.assigned_to].append(rc)
        else:
            unassigned.append(rc)

    profiles: list[TesterProfile] = []
    all_velocities: list[float] = []

    for user_id, cases in by_tester.items():
        completed = [rc for rc in cases if rc.status in STATUS_DONE]
        remaining_count = len(cases) - len(completed)

        durations = [rc.duration_seconds for rc in completed if rc.duration_seconds and rc.duration_seconds > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        # Tester'ın çalışma penceresini bul
        started_times = [rc.started_at for rc in cases if rc.started_at]
        if started_times:
            first_start = min(started_times).replace(tzinfo=_tz.utc)
            elapsed = max(0.001, (_utcnow() - first_start).total_seconds() / 3600)
            velocity = len(completed) / elapsed
        else:
            velocity = 0.0

        all_velocities.append(velocity)

        pass_count = sum(1 for rc in completed if rc.status == "passed")
        blocked_count = sum(1 for rc in completed if rc.status == "blocked")
        pass_rate = pass_count / len(completed) if completed else 0.0
        blocked_rate = blocked_count / len(completed) if completed else 0.0

        # Son aktivite
        activity_times = [
            rc.completed_at for rc in completed if rc.completed_at
        ]
        last_activity = max(activity_times).replace(tzinfo=_tz.utc) if activity_times else None
        inactive_minutes = (
            (_utcnow() - last_activity).total_seconds() / 60
            if last_activity else 999.0
        )

        profiles.append(TesterProfile(
            user_id=user_id,
            assigned_count=len(cases),
            completed_count=len(completed),
            remaining_count=remaining_count,
            avg_duration_seconds=round(avg_duration, 1),
            velocity_per_hour=round(velocity, 2),
            pass_rate=round(pass_rate, 3),
            blocked_rate=round(blocked_rate, 3),
            is_bottleneck=False,  # sonraki adımda set edilir
            last_activity_at=last_activity,
            inactive_minutes=round(inactive_minutes, 1),
        ))

    # Darboğaz tespiti: ortalama hızın %40 altındaki tester
    if all_velocities:
        avg_velocity = sum(all_velocities) / len(all_velocities)
        for p in profiles:
            if avg_velocity > 0 and p.velocity_per_hour < avg_velocity * 0.4 and p.remaining_count > 0:
                p.is_bottleneck = True

    # Atanmamış case'ler için sahte profil
    if unassigned:
        profiles.append(TesterProfile(
            user_id="__unassigned__",
            assigned_count=len(unassigned),
            completed_count=0,
            remaining_count=len(unassigned),
            avg_duration_seconds=0.0,
            velocity_per_hour=0.0,
            pass_rate=0.0,
            blocked_rate=0.0,
            is_bottleneck=True,
            last_activity_at=None,
            inactive_minutes=999.0,
        ))

    return sorted(profiles, key=lambda p: p.remaining_count, reverse=True)


def _detect_anomalies(
    run: TestRun,
    run_cases: list[TestRunCase],
    testers: list[TesterProfile],
    eta: ETAPrediction,
) -> list[Anomaly]:
    """Koşumdaki anomalileri tespit eder."""
    anomalies: list[Anomaly] = []

    # Tamamlanan case'lerin ortalama süresi
    durations = [
        rc.duration_seconds for rc in run_cases
        if rc.status in STATUS_DONE and rc.duration_seconds and rc.duration_seconds > 0
    ]
    avg_duration = sum(durations) / len(durations) if durations else 0

    # 1. Takılı case'ler (başladı ama bitmedi, uzun süredir)
    for rc in run_cases:
        if rc.status == "not_run" and rc.started_at:
            elapsed_secs = (_utcnow() - rc.started_at.replace(tzinfo=_tz.utc)).total_seconds()
            threshold = max(1800, avg_duration * 2)  # en az 30 dk veya 2× ortalama
            if elapsed_secs > threshold:
                elapsed_min = int(elapsed_secs / 60)
                anomalies.append(Anomaly(
                    severity="critical",
                    type="stuck_case",
                    title="Takılı Case",
                    detail=f"Case başlatıldı ama {elapsed_min} dakikadır sonuç girilmedi.",
                    run_case_id=rc.id,
                    user_id=rc.assigned_to,
                    suggested_action="Tester ile iletişime geç veya case'i yeniden ata.",
                ))

    # 2. Tester inaktivitesi (30+ dakika)
    for tester in testers:
        if tester.user_id == "__unassigned__":
            continue
        if tester.remaining_count > 0 and tester.inactive_minutes > 30:
            anomalies.append(Anomaly(
                severity="warning",
                type="tester_inactive",
                title="Tester İnaktif",
                detail=f"{int(tester.inactive_minutes)} dakikadır aktivite yok, {tester.remaining_count} case bekliyor.",
                user_id=tester.user_id,
                suggested_action="Tester'a ping at veya case'leri yeniden dağıt.",
            ))

    # 3. Yüksek blocked oranı (>%25)
    total_done = sum(1 for rc in run_cases if rc.status in STATUS_DONE)
    blocked_count = sum(1 for rc in run_cases if rc.status == "blocked")
    if total_done > 0 and blocked_count / total_done > 0.25:
        anomalies.append(Anomaly(
            severity="critical",
            type="high_blocked_rate",
            title="Yüksek Blocked Oranı",
            detail=f"Tamamlanan case'lerin %{int(blocked_count/total_done*100)}'i blocked — ortam sorunu olabilir.",
            suggested_action="Test ortamını kontrol et, ortam defect'i aç.",
        ))

    # 4. Hız düşüşü (son saat genel ortalamanın %50 altında)
    if eta.overall_velocity > 0 and eta.velocity_per_hour < eta.overall_velocity * 0.5 and eta.remaining_cases > 5:
        anomalies.append(Anomaly(
            severity="warning",
            type="velocity_decline",
            title="Hız Düşüşü",
            detail=f"Anlık hız ({eta.velocity_per_hour:.1f}/saat) genel ortalamanın ({eta.overall_velocity:.1f}/saat) çok altında.",
            suggested_action="Darboğaz olan tester'ı tespit et, takılı case'leri kontrol et.",
        ))

    # 5. Atanmamış case'ler
    unassigned_count = sum(1 for rc in run_cases if rc.status == "not_run" and not rc.assigned_to)
    if unassigned_count > 0:
        anomalies.append(Anomaly(
            severity="warning",
            type="unassigned_cases",
            title="Atanmamış Case'ler",
            detail=f"{unassigned_count} case herhangi bir tester'a atanmadı.",
            suggested_action="Case'leri tester'lara ata.",
        ))

    # 6. ETA riski
    if not eta.on_track and eta.remaining_cases > 0:
        anomalies.append(Anomaly(
            severity="critical" if eta.risk_level == "critical" else "warning",
            type="eta_risk",
            title="Zamanlama Riski",
            detail=eta.message,
            suggested_action="Tester sayısını artır veya scope'u daralt.",
        ))

    return sorted(anomalies, key=lambda a: (0 if a.severity == "critical" else 1, a.type))


def _risk_sort_remaining(db: Session, run_cases: list[TestRunCase]) -> list[CaseRiskScore]:
    """Kalan case'leri risk skoruna göre sıralar."""
    remaining_ids = [rc.case_id for rc in run_cases if rc.status == "not_run"]
    if not remaining_ids:
        return []

    cases = db.execute(
        select(TestCase).where(TestCase.id.in_(remaining_ids))
    ).scalars().all()

    # Bu case'lerin geçmiş failure sayısı (bu run dışında)
    case_map = {c.id: c for c in cases}
    scores: list[CaseRiskScore] = []

    for case in cases:
        # Basit history: last_run_status ve last_failed_at'ten hesapla
        total_runs_est = 1 if case.last_run_status else 0
        fail_count_est = 1 if case.last_run_status in ("failed", "blocked") else 0

        history = {"total_runs": total_runs_est, "fail_count": fail_count_est}
        scores.append(compute_case_risk_score(case, history))

    return sorted(scores, key=lambda s: s.risk_score, reverse=True)[:50]  # top 50


def get_tester_performance(db: Session, project_id: str, user_id: str) -> dict[str, Any]:
    """Bir tester'ın bu proje genelindeki performans özetini üretir."""

    # Tüm run case'leri bu tester için
    run_cases = db.execute(
        select(TestRunCase)
        .join(TestRun, TestRunCase.run_id == TestRun.id)
        .join(
            TestManagementProject.__table__,
            TestManagementProject.id == project_id,
        )
        .where(TestRunCase.assigned_to == user_id)
        .where(TestRunCase.status.in_(STATUS_DONE))
    ).scalars().all()

    if not run_cases:
        return {
            "user_id": user_id,
            "total_executed": 0,
            "pass_rate": 0.0,
            "avg_duration_seconds": 0.0,
            "defect_detection_rate": 0.0,
            "message": "Bu proje için yeterli veri yok.",
        }

    total = len(run_cases)
    passed = sum(1 for rc in run_cases if rc.status == "passed")
    failed = sum(1 for rc in run_cases if rc.status == "failed")
    blocked = sum(1 for rc in run_cases if rc.status == "blocked")

    durations = [rc.duration_seconds for rc in run_cases if rc.duration_seconds and rc.duration_seconds > 0]
    avg_duration = sum(durations) / len(durations) if durations else 0.0

    return {
        "user_id": user_id,
        "total_executed": total,
        "pass_rate": round(passed / total, 3),
        "fail_rate": round(failed / total, 3),
        "blocked_rate": round(blocked / total, 3),
        "avg_duration_seconds": round(avg_duration, 1),
        "defect_detection_rate": round(failed / total, 3),  # fail = defect bulma
    }


def predict_release_readiness(db: Session, project_id: str) -> ReleaseReadinessPrediction:
    """Release gate kriterlerine göre teslim edilebilirlik tahmini üretir."""
    from app.domains.test_management.service import resolve_project_id  # noqa: PLC0415

    now = _utcnow()
    real_pid = resolve_project_id(db, project_id)

    # En son aktif koşumu bul — YALNIZCA bu projeye ait (cross-project sızıntı önleme)
    runs = db.execute(
        select(TestRun)
        .join(TestCycle, TestRun.cycle_id == TestCycle.id)
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .where(TestPlan.project_id == real_pid)
        .where(TestRun.status.in_(["in_progress", "not_started"]))
        .order_by(TestRun.created_at.desc())
    ).scalars().all()

    if not runs:
        return ReleaseReadinessPrediction(
            project_id=project_id,
            generated_at=now,
            will_meet_gate=False,
            confidence=0.0,
            days_to_completion=None,
            blocking_factors=["Aktif test koşumu bulunamadı."],
            execution_rate=0.0,
            pass_rate=0.0,
            open_defects=0,
            recommendation="Önce bir test koşumu başlatın.",
        )

    latest_run = runs[0]
    run_cases = db.execute(
        select(TestRunCase).where(TestRunCase.run_id == latest_run.id)
    ).scalars().all()

    total = len(run_cases)
    done = [rc for rc in run_cases if rc.status in STATUS_DONE]
    passed = [rc for rc in done if rc.status == "passed"]

    execution_rate = len(done) / total if total > 0 else 0.0
    pass_rate = len(passed) / len(done) if done else 0.0

    blocking_factors: list[str] = []

    if execution_rate < 0.95:
        blocking_factors.append(
            f"Execution tamamlanmadı: %{int(execution_rate*100)} (hedef: %95)"
        )
    if pass_rate < 0.90 and done:
        blocking_factors.append(
            f"Pass rate düşük: %{int(pass_rate*100)} (hedef: %90)"
        )

    open_blocked = sum(1 for rc in run_cases if rc.status == "blocked")
    if open_blocked > 0:
        blocking_factors.append(f"{open_blocked} blocked case var (hedef: 0)")

    # ETA hesabı
    eta = _predict_eta(latest_run, run_cases)
    days_to_completion = eta.eta_hours / 24 if eta.eta_hours else None

    will_meet_gate = len(blocking_factors) == 0
    confidence = 0.85 if will_meet_gate else max(0.1, 0.5 - len(blocking_factors) * 0.15)

    if will_meet_gate:
        recommendation = "Release gate kriterlerini karşılıyor. GO imzalanabilir."
    elif len(blocking_factors) == 1:
        recommendation = f"1 engel var: {blocking_factors[0]}"
    else:
        recommendation = f"{len(blocking_factors)} engel giderilmeden release yapılamaz."

    return ReleaseReadinessPrediction(
        project_id=project_id,
        generated_at=now,
        will_meet_gate=will_meet_gate,
        confidence=round(confidence, 2),
        days_to_completion=round(days_to_completion, 1) if days_to_completion else None,
        blocking_factors=blocking_factors,
        execution_rate=round(execution_rate, 3),
        pass_rate=round(pass_rate, 3),
        open_defects=open_blocked,
        recommendation=recommendation,
    )
