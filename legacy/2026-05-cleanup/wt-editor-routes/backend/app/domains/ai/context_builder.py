"""Query-aware project context builder for grounded AI chat responses."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domains.tspm.models import (
    TspmExecution,
    TspmExecutionMetrics,
    TspmExecutionResult,
    TspmProject,
    TspmRequirement,
    TspmScenario,
    TspmScenarioRequirement,
    TspmTestCase,
    TspmTestDataSet,
)

_STOP_WORDS = {
    "acaba",
    "ama",
    "ancak",
    "as",
    "bir",
    "bu",
    "can",
    "da",
    "de",
    "daha",
    "değil",
    "diye",
    "en",
    "for",
    "gibi",
    "hangi",
    "how",
    "için",
    "ile",
    "ilgili",
    "in",
    "is",
    "it",
    "mi",
    "mı",
    "mu",
    "mü",
    "nasıl",
    "ne",
    "neden",
    "olan",
    "olarak",
    "olanı",
    "or",
    "the",
    "ve",
    "veya",
    "what",
    "why",
    "ya",
}

_INTENT_KEYWORDS: dict[str, set[str]] = {
    "failure": {"bug", "debug", "error", "fail", "failure", "flaky", "hata", "neden", "root", "sorun"},
    "coverage": {"coverage", "eksik", "gap", "kapsam", "oran", "requirement"},
    "automation": {"automation", "bdd", "cucumber", "gherkin", "java", "locator", "nexusqa", "playwright", "selector"},
    "data": {"csv", "data", "dataset", "schema", "sql", "test data", "veri"},
    "scenario": {"senaryo", "scenario", "test case", "testcase", "test"},
}


@dataclass
class ContextSnippet:
    source_type: str
    title: str
    body: str
    score: float


def build_project_ai_context(
    db: Session,
    project_id: str,
    user_query: str,
    *,
    max_chars: int = 6000,
) -> str:
    """Build a compact, query-aware project context for AI chat prompts."""
    project = db.get(TspmProject, project_id)
    if project is None:
        return ""

    query = (user_query or "").strip()
    keywords = _extract_keywords(query)
    intent = _detect_intent(query, keywords)

    sections: list[str] = []
    summary = _build_project_summary(db, project, intent)
    if summary:
        sections.append(summary)

    snippets = _collect_relevant_snippets(db, project_id, query, keywords, intent)
    if snippets:
        snippet_lines = ["Soru ile en ilgili proje kayıtları:"]
        current_len = sum(len(s) for s in sections) + len("\n\n".join(snippet_lines))
        for snippet in snippets:
            block = f"[{snippet.source_type}] {snippet.title}\n{snippet.body}"
            projected_len = current_len + len(block) + 2
            if projected_len > max_chars and len(snippet_lines) > 1:
                break
            snippet_lines.append(block)
            current_len = projected_len
        sections.append("\n\n".join(snippet_lines))

    return "\n\n".join(section for section in sections if section).strip()


def _build_project_summary(db: Session, project: TspmProject, intent: str) -> str:
    scenario_count = db.scalar(
        select(func.count(TspmScenario.id)).where(TspmScenario.project_id == project.id)
    ) or 0
    requirement_count = db.scalar(
        select(func.count(TspmRequirement.id)).where(TspmRequirement.project_id == project.id)
    ) or 0
    pending_test_cases = db.scalar(
        select(func.count(TspmTestCase.id)).where(
            TspmTestCase.project_id == project.id,
            TspmTestCase.review_status == "pending",
        )
    ) or 0
    latest_metrics = db.scalar(
        select(TspmExecutionMetrics)
        .where(TspmExecutionMetrics.project_id == project.id)
        .order_by(TspmExecutionMetrics.executed_at.desc())
    )
    recent_exec_count = db.scalar(
        select(func.count(TspmExecution.id)).where(TspmExecution.project_id == project.id)
    ) or 0

    lines = [
        "Proje özeti:",
        f"- Proje: {project.name}",
        f"- Senaryo sayısı: {scenario_count}",
        f"- Gereksinim sayısı: {requirement_count}",
        f"- Bekleyen AI test case sayısı: {pending_test_cases}",
        f"- Koşu sayısı: {recent_exec_count}",
    ]

    if latest_metrics:
        lines.append(
            "- Son koşu başarı oranı: "
            f"%{latest_metrics.pass_rate:.1f} "
            f"({latest_metrics.passed} geçti / {latest_metrics.failed} başarısız)"
        )

    if intent == "coverage":
        gap_count = _count_requirement_gaps(db, project.id)
        lines.append(f"- Kapsam boşluğu olan gereksinim sayısı: {gap_count}")

    return "\n".join(lines)


def _collect_relevant_snippets(
    db: Session,
    project_id: str,
    query: str,
    keywords: list[str],
    intent: str,
) -> list[ContextSnippet]:
    snippets: list[ContextSnippet] = []
    snippets.extend(_scenario_snippets(db, project_id, query, keywords, intent))
    snippets.extend(_requirement_snippets(db, project_id, query, keywords, intent))
    snippets.extend(_failed_execution_snippets(db, project_id, query, keywords, intent))
    snippets.extend(_test_case_snippets(db, project_id, query, keywords, intent))

    if intent == "data":
        snippets.extend(_dataset_snippets(db, project_id, query, keywords))

    deduped: dict[tuple[str, str], ContextSnippet] = {}
    for snippet in snippets:
        key = (snippet.source_type, snippet.title)
        if key not in deduped or deduped[key].score < snippet.score:
            deduped[key] = snippet

    ordered = sorted(
        deduped.values(),
        key=lambda item: (-item.score, item.source_type, item.title),
    )
    return ordered[:8]


def _scenario_snippets(
    db: Session,
    project_id: str,
    query: str,
    keywords: list[str],
    intent: str,
) -> list[ContextSnippet]:
    scenarios = list(
        db.scalars(
            select(TspmScenario)
            .where(TspmScenario.project_id == project_id)
            .order_by(TspmScenario.updated_at.desc())
            .limit(120)
        )
    )

    snippets: list[ContextSnippet] = []
    for scenario in scenarios:
        step_summary = _summarize_steps(scenario.steps)
        text = " ".join(
            filter(
                None,
                [
                    scenario.title,
                    scenario.description or "",
                    " ".join(scenario.tags or []),
                    step_summary,
                ],
            )
        )
        score = _score_text(text, keywords)
        if intent in {"scenario", "automation"}:
            score += 1.5
        if scenario.status == "approved":
            score += 0.5
        if not keywords:
            score += 0.2
        if score <= 0:
            continue

        details = [
            f"Durum: {scenario.status}",
        ]
        if scenario.tags:
            details.append(f"Etiketler: {', '.join(scenario.tags[:6])}")
        if scenario.description:
            details.append(f"Açıklama: {_truncate(scenario.description, 220)}")
        if step_summary:
            details.append(f"Adımlar: {_truncate(step_summary, 220)}")

        snippets.append(
            ContextSnippet(
                source_type="Senaryo",
                title=scenario.title,
                body="\n".join(details),
                score=score,
            )
        )
    return snippets


def _requirement_snippets(
    db: Session,
    project_id: str,
    query: str,
    keywords: list[str],
    intent: str,
) -> list[ContextSnippet]:
    requirements = list(
        db.scalars(
            select(TspmRequirement)
            .where(TspmRequirement.project_id == project_id)
            .order_by(TspmRequirement.created_at.desc())
            .limit(100)
        )
    )
    linked_counts = dict(
        db.execute(
            select(
                TspmScenarioRequirement.requirement_id,
                func.count(TspmScenarioRequirement.scenario_id),
            )
            .join(TspmRequirement, TspmRequirement.id == TspmScenarioRequirement.requirement_id)
            .where(TspmRequirement.project_id == project_id)
            .group_by(TspmScenarioRequirement.requirement_id)
        ).all()
    )

    snippets: list[ContextSnippet] = []
    for requirement in requirements:
        linked = linked_counts.get(requirement.id, 0)
        text = " ".join(
            filter(
                None,
                [
                    requirement.external_id,
                    requirement.title,
                    requirement.description or "",
                    requirement.priority,
                    requirement.source or "",
                ],
            )
        )
        score = _score_text(text, keywords)
        if intent == "coverage":
            score += 2
        if linked == 0:
            score += 2.5 if intent == "coverage" else 0.8
        if not keywords and linked == 0:
            score += 0.3
        if score <= 0:
            continue

        details = [
            f"ID: {requirement.external_id} | Öncelik: {requirement.priority} | Bağlı senaryo: {linked}",
        ]
        if requirement.source:
            details.append(f"Kaynak: {requirement.source}")
        if requirement.description:
            details.append(f"Açıklama: {_truncate(requirement.description, 220)}")
        if linked == 0:
            details.append("Not: Bu gereksinim için bağlı senaryo görünmüyor.")

        snippets.append(
            ContextSnippet(
                source_type="Gereksinim",
                title=requirement.title,
                body="\n".join(details),
                score=score,
            )
        )
    return snippets


def _failed_execution_snippets(
    db: Session,
    project_id: str,
    query: str,
    keywords: list[str],
    intent: str,
) -> list[ContextSnippet]:
    executions = list(
        db.scalars(
            select(TspmExecution)
            .where(TspmExecution.project_id == project_id)
            .order_by(TspmExecution.created_at.desc())
            .limit(8)
        )
    )
    if not executions:
        return []

    snippets: list[ContextSnippet] = []
    for execution in executions:
        results = list(
            db.scalars(
                select(TspmExecutionResult)
                .where(
                    TspmExecutionResult.execution_id == execution.id,
                    TspmExecutionResult.status == "failed",
                )
                .limit(10)
            )
        )
        for result in results:
            scenario = db.get(TspmScenario, result.scenario_id)
            text = " ".join(
                filter(
                    None,
                    [
                        execution.name,
                        execution.status,
                        result.note or "",
                        scenario.title if scenario else "",
                        scenario.description if scenario else "",
                    ],
                )
            )
            score = _score_text(text, keywords)
            if intent == "failure":
                score += 4
            elif not keywords:
                score += 0.6
            if score <= 0:
                continue

            title = scenario.title if scenario else f"Scenario {result.scenario_id}"
            date_str = execution.created_at.strftime("%d.%m.%Y") if execution.created_at else "?"
            details = [
                f"Koşu: {execution.name} | Tarih: {date_str} | Durum: {execution.status}",
            ]
            if result.note:
                details.append(f"Hata notu: {_truncate(result.note, 240)}")
            if scenario and scenario.tags:
                details.append(f"Etiketler: {', '.join(scenario.tags[:5])}")

            snippets.append(
                ContextSnippet(
                    source_type="Başarısız Koşu",
                    title=title,
                    body="\n".join(details),
                    score=score,
                )
            )
    return snippets


def _test_case_snippets(
    db: Session,
    project_id: str,
    query: str,
    keywords: list[str],
    intent: str,
) -> list[ContextSnippet]:
    test_cases = list(
        db.scalars(
            select(TspmTestCase)
            .where(TspmTestCase.project_id == project_id)
            .order_by(TspmTestCase.updated_at.desc())
            .limit(80)
        )
    )
    snippets: list[ContextSnippet] = []
    for test_case in test_cases:
        text = " ".join(
            filter(
                None,
                [
                    test_case.title,
                    test_case.description or "",
                    test_case.module_name or "",
                    test_case.feature_area or "",
                    test_case.expected_result or "",
                    " ".join(test_case.tags or []),
                ],
            )
        )
        score = _score_text(text, keywords)
        if intent in {"scenario", "automation"}:
            score += 1
        if test_case.review_status == "pending":
            score += 0.6
        if score <= 0:
            continue

        details = [
            (
                f"Review: {test_case.review_status} | "
                f"Tip: {test_case.test_type} | "
                f"Öncelik: {test_case.priority} | "
                f"Risk: {test_case.risk_level}"
            ),
        ]
        if test_case.module_name or test_case.feature_area:
            details.append(
                "Alan: "
                + " / ".join(
                    part for part in [test_case.module_name, test_case.feature_area] if part
                )
            )
        if test_case.description:
            details.append(f"Açıklama: {_truncate(test_case.description, 200)}")

        snippets.append(
            ContextSnippet(
                source_type="AI Test Case",
                title=test_case.title,
                body="\n".join(details),
                score=score,
            )
        )
    return snippets


def _dataset_snippets(
    db: Session,
    project_id: str,
    query: str,
    keywords: list[str],
) -> list[ContextSnippet]:
    datasets = list(
        db.scalars(
            select(TspmTestDataSet)
            .where(TspmTestDataSet.project_id == project_id)
            .order_by(TspmTestDataSet.created_at.desc())
            .limit(30)
        )
    )
    snippets: list[ContextSnippet] = []
    for dataset in datasets:
        row_count = len(dataset.rows or [])
        column_names = [c.get("name", "") for c in (dataset.columns or [])[:8] if isinstance(c, dict)]
        text = " ".join(
            filter(
                None,
                [dataset.name, dataset.description or "", " ".join(column_names)],
            )
        )
        score = _score_text(text, keywords) + 1.5
        if score <= 0:
            continue
        body_lines = [
            f"Kolonlar: {', '.join(column_names) if column_names else 'tanımsız'}",
            f"Satır sayısı: {row_count}",
        ]
        if dataset.description:
            body_lines.append(f"Açıklama: {_truncate(dataset.description, 180)}")
        snippets.append(
            ContextSnippet(
                source_type="Test Verisi",
                title=dataset.name,
                body="\n".join(body_lines),
                score=score,
            )
        )
    return snippets


def _count_requirement_gaps(db: Session, project_id: str) -> int:
    linked_requirement_ids = set(
        db.scalars(
            select(TspmScenarioRequirement.requirement_id)
            .join(TspmRequirement, TspmRequirement.id == TspmScenarioRequirement.requirement_id)
            .where(TspmRequirement.project_id == project_id)
        )
    )
    requirement_ids = set(
        db.scalars(
            select(TspmRequirement.id).where(TspmRequirement.project_id == project_id)
        )
    )
    return len(requirement_ids - linked_requirement_ids)


def _extract_keywords(query: str) -> list[str]:
    tokens = [
        token
        for token in re.findall(r"[\w-]+", _normalize(query), flags=re.UNICODE)
        if len(token) > 1 and token not in _STOP_WORDS
    ]
    counts = Counter(tokens)
    return [token for token, _ in counts.most_common(8)]


def _detect_intent(query: str, keywords: list[str]) -> str:
    text = _normalize(query)
    scores: Counter[str] = Counter()
    for intent, intent_keywords in _INTENT_KEYWORDS.items():
        for keyword in intent_keywords:
            if keyword in text:
                scores[intent] += 2
        for keyword in keywords:
            if keyword in intent_keywords:
                scores[intent] += 1
    if not scores:
        return "general"
    return scores.most_common(1)[0][0]


def _score_text(text: str, keywords: list[str]) -> float:
    normalized = _normalize(text)
    if not normalized:
        return 0.0
    if not keywords:
        return 0.4

    score = 0.0
    for keyword in keywords:
        if keyword in normalized:
            occurrences = normalized.count(keyword)
            score += 2.5 + min(occurrences, 3) * 0.7

    if len(keywords) >= 2:
        phrase = " ".join(keywords[:2])
        if phrase and phrase in normalized:
            score += 1.5

    return score


def _summarize_steps(steps: Any) -> str:
    if not isinstance(steps, list):
        return ""

    parts: list[str] = []
    for step in steps[:4]:
        if isinstance(step, dict):
            piece = " ".join(
                filter(
                    None,
                    [
                        str(step.get("keyword", "")).strip(),
                        str(step.get("text", step.get("action", ""))).strip(),
                        str(step.get("expected", "")).strip(),
                    ],
                )
            ).strip()
            if piece:
                parts.append(piece)
        elif isinstance(step, str) and step.strip():
            parts.append(step.strip())
    return " | ".join(parts)


def _normalize(text: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", " ", (text or "").lower(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", cleaned).strip()


def _truncate(text: str, max_len: int) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 3].rstrip() + "..."
