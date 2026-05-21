"""Flaky karantina — pure hesaplama + karar matrisi testleri."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.domains.tspm.flaky_service import (
    IngestItem,
    IngestRequest,
    compute_stability,
    decide_quarantine,
)


# ── compute_stability ────────────────────────────────────────────────────


def test_all_pass() -> None:
    s = compute_stability(["passed"] * 10)
    assert s.runs_count == 10
    assert s.passed_count == 10
    assert s.failed_count == 0
    assert s.flip_count == 0
    assert s.pass_rate == 1.0
    assert s.flakiness_score == 0.0


def test_all_fail() -> None:
    s = compute_stability(["failed"] * 10)
    assert s.pass_rate == 0.0
    # Monoton fail → flakiness sadece (1-pass_rate)*0.5 = 0.5, flip=0
    assert s.flakiness_score == 0.5
    assert s.flip_count == 0


def test_classic_flaky_alternating() -> None:
    # passed, failed, passed, failed, passed, failed → 3/6 pass, 5 flip
    statuses = ["passed", "failed"] * 3
    s = compute_stability(statuses)
    assert s.runs_count == 6
    assert s.pass_rate == 0.5
    assert s.flip_count == 5
    # flip_rate = 5/5 = 1.0; flakiness = 0.5*0.5 + 1.0*0.5 = 0.75
    assert s.flakiness_score == 0.75


def test_skipped_error_ignored() -> None:
    # Skipped/error filtrelenir, sadece pass/fail sayılır
    s = compute_stability(
        ["passed", "skipped", "error", "passed", "failed", "skipped"]
    )
    assert s.runs_count == 3
    assert s.passed_count == 2
    assert s.failed_count == 1


def test_empty_statuses() -> None:
    s = compute_stability([])
    assert s.runs_count == 0
    assert s.flakiness_score == 0.0


def test_single_run_no_flips() -> None:
    s = compute_stability(["failed"])
    assert s.runs_count == 1
    assert s.flip_count == 0
    assert s.pass_rate == 0.0


def test_one_outlier_in_stable_run() -> None:
    # 18 passed, 2 failed, alternating'iz değil
    statuses = ["passed"] * 18 + ["failed", "passed"]
    s = compute_stability(statuses)
    assert s.pass_rate == pytest.approx(19 / 20)
    # İki flip: pass→fail, fail→pass
    assert s.flip_count == 2
    # flip_rate = 2/19 ≈ 0.105; flakiness ≈ 0.05*0.5 + 0.105*0.5 ≈ 0.078
    assert 0.06 < s.flakiness_score < 0.10


# ── decide_quarantine ────────────────────────────────────────────────────


def _score(
    flakiness: float = 0.0,
    pass_rate: float = 1.0,
    runs: int = 10,
):
    from app.domains.tspm.flaky_service import StabilityScore

    return StabilityScore(
        runs_count=runs,
        passed_count=int(runs * pass_rate),
        failed_count=runs - int(runs * pass_rate),
        flip_count=0,
        pass_rate=pass_rate,
        flakiness_score=flakiness,
    )


def test_insufficient_runs_keeps_current_state() -> None:
    dec = decide_quarantine(
        _score(flakiness=0.9, runs=3),  # < 5 min
        currently_quarantined=False,
    )
    assert dec.should_quarantine is False
    assert dec.reason == "insufficient_runs"

    dec2 = decide_quarantine(
        _score(flakiness=0.0, runs=3),
        currently_quarantined=True,
    )
    assert dec2.should_quarantine is True  # state korunur
    assert dec2.reason == "insufficient_runs"


def test_enters_quarantine_at_threshold() -> None:
    dec = decide_quarantine(
        _score(flakiness=0.40, pass_rate=0.6, runs=10),
        currently_quarantined=False,
    )
    assert dec.should_quarantine is True
    assert dec.reason == "threshold_exceeded"
    assert dec.quarantined_until is not None


def test_stays_stable_below_threshold() -> None:
    dec = decide_quarantine(
        _score(flakiness=0.10, pass_rate=0.95, runs=20),
        currently_quarantined=False,
    )
    assert dec.should_quarantine is False
    assert dec.reason == "stable"


def test_hysteresis_no_flip_at_mid_range() -> None:
    # flakiness 0.25 — enter threshold (0.35) altında ama exit (0.15) üstünde
    # → giriyorsa çıkmaz, girmiyorsa girmez
    not_in = decide_quarantine(
        _score(flakiness=0.25, pass_rate=0.75, runs=20),
        currently_quarantined=False,
    )
    assert not_in.should_quarantine is False

    in_q = decide_quarantine(
        _score(flakiness=0.25, pass_rate=0.75, runs=20),
        currently_quarantined=True,
    )
    assert in_q.should_quarantine is True
    assert in_q.reason == "still_flaky"


def test_exits_quarantine_when_recovered() -> None:
    dec = decide_quarantine(
        _score(flakiness=0.10, pass_rate=0.95, runs=20),
        currently_quarantined=True,
    )
    assert dec.should_quarantine is False
    assert dec.reason == "recovered"


def test_exits_requires_both_conditions() -> None:
    # flakiness düşük ama pass_rate 0.89 (< 0.90) → yine quarantine
    dec = decide_quarantine(
        _score(flakiness=0.10, pass_rate=0.89, runs=20),
        currently_quarantined=True,
    )
    assert dec.should_quarantine is True
    assert dec.reason == "still_flaky"


def test_env_override_changes_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLAKY_QUARANTINE_THRESHOLD", "0.10")
    dec = decide_quarantine(
        _score(flakiness=0.12, pass_rate=0.80, runs=10),
        currently_quarantined=False,
    )
    assert dec.should_quarantine is True


def test_quarantined_until_has_correct_offset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLAKY_QUARANTINE_DAYS", "7")
    now = datetime(2026, 4, 19, 10, 0, tzinfo=timezone.utc)
    dec = decide_quarantine(
        _score(flakiness=0.9, pass_rate=0.3, runs=10),
        currently_quarantined=False,
        now=now,
    )
    assert dec.quarantined_until == now + timedelta(days=7)


# ── IngestRequest validation ─────────────────────────────────────────────


def test_ingest_request_rejects_empty_list() -> None:
    with pytest.raises(ValueError):
        IngestRequest(events=[])


def test_ingest_item_status_validated() -> None:
    with pytest.raises(ValueError):
        IngestItem(test_key="t", status="invalid")  # type: ignore[arg-type]


def test_ingest_item_defaults() -> None:
    item = IngestItem(test_key="tests/a.spec.ts::login", status="passed")
    assert item.env == "ci"
    assert item.project_id is None
    assert item.duration_ms is None
