"""Eval runner — suite orkestratörü.

Akış:
    1. Suite'in adapter'ını registry'den al
    2. ``adapter.available()`` False → SuiteResult(passed=True, skipped note)
       (CI'ı kırmamak için; rapora açık yazılır)
    3. Her case için:
        a. ``adapter.run(inputs)`` → actual
        b. Her scorer: ``score(case, actual)`` → ScorerOutput
        c. CaseResult(passed = tüm scorer'lar passed)
    4. Aggregate:
        * scorer adı → ortalama value
        * case_pass_rate
    5. Threshold kontrolü → SuiteResult.passed

Tasarım notları:
    * Adapter çağrısı senkron ama case'ler için concurrent yürütme opsiyonel
      (ThreadPoolExecutor). DSL retrieval için CPU-bound matmul zaten GIL'de,
      embed çağrısı network-bound → paralelden kazanç var. Default:
      ``max_workers=4`` (ENV ile override).
    * Hata izolasyonu: bir case patlarsa sadece o case ``error`` alır;
      suite çalışmaya devam eder.
    * ``started_at/finished_at`` timezone-aware UTC.
"""
from __future__ import annotations

import concurrent.futures as _cf
import logging
import os
import time
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from app.infra.telemetry import set_span_attr, trace_span

from .adapters import get_adapter
from .schemas import (
    Adapter,
    CaseResult,
    EvalCase,
    ScorerOutput,
    Suite,
    SuiteResult,
)
from .scorers import get_scorer

logger = logging.getLogger(__name__)


def _default_max_workers() -> int:
    raw = os.environ.get("EVAL_MAX_WORKERS", "4")
    try:
        return max(1, min(32, int(raw)))
    except ValueError:
        return 4


def _run_case(adapter: Adapter, case: EvalCase, scorer_names: List[str]) -> CaseResult:
    t0 = time.monotonic()
    try:
        actual = adapter.run(dict(case.inputs))
    except Exception as exc:  # yakalanan: SUT'un kendi hatası
        latency_ms = int((time.monotonic() - t0) * 1000)
        logger.warning("Case %s adapter hata: %s", case.id, exc)
        return CaseResult(
            case_id=case.id,
            passed=False,
            latency_ms=latency_ms,
            error=f"{type(exc).__name__}: {exc}",
            actual={},
        )
    latency_ms = int((time.monotonic() - t0) * 1000)

    outputs: List[ScorerOutput] = []
    for sname in scorer_names:
        scorer = get_scorer(sname)
        try:
            out = scorer.score(case=case, actual=actual)
        except Exception as exc:
            logger.warning("Case %s scorer %s hata: %s", case.id, sname, exc)
            out = ScorerOutput(
                name=sname,
                value=0.0,
                passed=False,
                details={"error": f"{type(exc).__name__}: {exc}"},
            )
        outputs.append(out)

    passed = bool(outputs) and all(o.passed for o in outputs)
    return CaseResult(
        case_id=case.id,
        passed=passed,
        scores=outputs,
        latency_ms=latency_ms,
        actual=actual,
    )


def _aggregate(result: SuiteResult) -> None:
    """Scorer bazlı ortalama value'ları ve pass-rate hesapla."""
    if not result.cases:
        return

    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    for cr in result.cases:
        for s in cr.scores:
            sums[s.name] = sums.get(s.name, 0.0) + float(s.value)
            counts[s.name] = counts.get(s.name, 0) + 1

    aggregate = {}
    for name, total in sums.items():
        n = counts.get(name) or 1
        aggregate[f"mean_{name}"] = round(total / n, 6)

    aggregate["case_pass_rate"] = round(result.case_pass_rate(), 6)
    aggregate["cases_total"] = float(len(result.cases))
    aggregate["cases_passed"] = float(result.count_passed())
    result.aggregate = aggregate

    result.total_latency_ms = sum(c.latency_ms for c in result.cases)


def _check_thresholds(suite: Suite, result: SuiteResult) -> None:
    failures: List[str] = []
    for metric, threshold in suite.thresholds.mean_thresholds.items():
        key = f"mean_{metric}" if not metric.startswith("mean_") else metric
        actual = result.aggregate.get(key)
        if actual is None:
            failures.append(f"{key}: aggregate yok (scorer adı yanlış olabilir)")
            continue
        if actual < threshold:
            failures.append(
                f"{key}={actual:.4f} < threshold {threshold:.4f}"
            )

    pass_rate = result.aggregate.get("case_pass_rate", 0.0)
    if pass_rate < suite.thresholds.min_case_pass_rate:
        failures.append(
            f"case_pass_rate={pass_rate:.4f} < "
            f"{suite.thresholds.min_case_pass_rate:.4f}"
        )

    result.threshold_failures = failures
    result.passed = not failures


def run_suite(
    suite: Suite,
    *,
    max_workers: Optional[int] = None,
) -> SuiteResult:
    with trace_span(
        "evals.run_suite",
        attrs={
            "suite": suite.name,
            "adapter": suite.adapter_name,
            "case_count": len(suite.cases),
            "scorer_count": len(suite.scorers),
        },
    ):
        out = _run_suite_inner(suite, max_workers=max_workers)
        set_span_attr("passed", out.passed)
        set_span_attr("cases_passed", out.count_passed())
        set_span_attr("total_latency_ms", out.total_latency_ms)
        return out


def _run_suite_inner(
    suite: Suite, *, max_workers: Optional[int] = None
) -> SuiteResult:
    adapter = get_adapter(suite.adapter_name)
    result = SuiteResult(suite_name=suite.name, adapter_name=suite.adapter_name)

    if not adapter.available():
        logger.warning(
            "Suite '%s' skip: adapter '%s' available() False",
            suite.name,
            suite.adapter_name,
        )
        # Skip'i pass olarak işaretleyip aggregate'e not düş
        result.aggregate = {"skipped": 1.0}
        result.passed = True  # CI'ı kırmayız, ama rapora explicit yazarız
        result.threshold_failures = [
            f"SKIPPED: adapter '{suite.adapter_name}' available değil"
        ]
        result.finished_at = datetime.now(timezone.utc)
        return result

    workers = max_workers if max_workers is not None else _default_max_workers()
    workers = max(1, min(workers, len(suite.cases) or 1))

    scorer_names = list(suite.scorers)

    if workers <= 1 or len(suite.cases) <= 1:
        for case in suite.cases:
            result.cases.append(_run_case(adapter, case, scorer_names))
    else:
        with _cf.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_run_case, adapter, case, scorer_names): case
                for case in suite.cases
            }
            for future in _cf.as_completed(futures):
                result.cases.append(future.result())
        # Sıra korunsun (deterministik rapor)
        order = {c.id: i for i, c in enumerate(suite.cases)}
        result.cases.sort(key=lambda cr: order.get(cr.case_id, 1_000_000))

    result.finished_at = datetime.now(timezone.utc)
    _aggregate(result)
    _check_thresholds(suite, result)
    return result


def run_suites(suites: Iterable[Suite], *, max_workers: Optional[int] = None) -> List[SuiteResult]:
    return [run_suite(s, max_workers=max_workers) for s in suites]
