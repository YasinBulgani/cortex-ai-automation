"""A11y parse + score + aggregate testleri."""
from __future__ import annotations

import pytest

from app.domains.a11y.service import (
    aggregate_reports,
    compute_score,
    parse_axe_report,
)


# ── compute_score ───────────────────────────────────────────────────────


class TestScore:
    def test_perfect_100(self) -> None:
        assert compute_score({"critical": 0, "serious": 0, "moderate": 0, "minor": 0}) == 100

    def test_one_critical_drops_25(self) -> None:
        assert compute_score({"critical": 1, "serious": 0, "moderate": 0, "minor": 0}) == 75

    def test_all_serious(self) -> None:
        # 3 serious × 10 = 30 → 70
        assert compute_score({"critical": 0, "serious": 3, "moderate": 0, "minor": 0}) == 70

    def test_floors_at_zero(self) -> None:
        # 10 critical → 250 penalty → 100 - 250 < 0 → 0
        assert compute_score({"critical": 10}) == 0

    def test_unknown_severities_ignored(self) -> None:
        assert compute_score({"info": 5, "critical": 1}) == 75


# ── parse_axe_report ────────────────────────────────────────────────────


_SAMPLE = {
    "url": "https://example.com/login",
    "timestamp": "2026-04-19T10:00:00.000Z",
    "violations": [
        {
            "id": "color-contrast",
            "impact": "serious",
            "help": "Elements must have sufficient color contrast",
            "helpUrl": "https://dequeuniversity.com/rules/axe/4.9/color-contrast",
            "description": "Ensures the contrast between foreground and background colors meets WCAG 2 AA",
            "nodes": [
                {"target": [".login-btn"]},
                {"target": [".submit-btn"]},
            ],
        },
        {
            "id": "label",
            "impact": "critical",
            "help": "Form elements must have labels",
            "nodes": [
                {"target": ["input[name=email]"]},
            ],
        },
        {
            "id": "landmark-one-main",
            "impact": "moderate",
            "help": "Page should have one main landmark",
            "nodes": [],
        },
    ],
    "passes": [{"id": "aria-valid-attr"}, {"id": "region"}],
    "incomplete": [],
    "inapplicable": [{"id": "html-has-lang"}],
}


class TestParse:
    def test_basic_parse(self) -> None:
        r = parse_axe_report(_SAMPLE)
        assert r.url == "https://example.com/login"
        assert len(r.violations) == 3
        # 1 critical (25) + 1 serious (10) + 1 moderate (3) = 38 → 62
        assert r.score == 62

    def test_severity_counts(self) -> None:
        r = parse_axe_report(_SAMPLE)
        assert r.severity_counts["critical"] == 1
        assert r.severity_counts["serious"] == 1
        assert r.severity_counts["moderate"] == 1
        assert r.severity_counts["minor"] == 0

    def test_node_counts(self) -> None:
        r = parse_axe_report(_SAMPLE)
        # color-contrast 2 + label 1 + landmark-one-main 0 = 3
        assert r.total_nodes_with_violations == 3
        contrast = next(v for v in r.violations if v.id == "color-contrast")
        assert contrast.node_count == 2
        assert ".login-btn" in contrast.sample_targets[0]

    def test_supporting_counts(self) -> None:
        r = parse_axe_report(_SAMPLE)
        assert r.passes_count == 2
        assert r.incomplete_count == 0
        assert r.inapplicable_count == 1

    def test_unknown_impact_defaults_moderate(self) -> None:
        r = parse_axe_report(
            {
                "violations": [
                    {"id": "x", "impact": "extremely-bad", "nodes": []}
                ]
            }
        )
        assert r.violations[0].impact == "moderate"

    def test_empty_report(self) -> None:
        r = parse_axe_report({})
        assert r.score == 100
        assert r.violations == []
        assert all(c == 0 for c in r.severity_counts.values())

    def test_violations_not_list_tolerated(self) -> None:
        r = parse_axe_report({"violations": "not-a-list"})
        assert r.score == 100

    def test_rejects_non_dict(self) -> None:
        with pytest.raises(ValueError):
            parse_axe_report("not a dict")  # type: ignore[arg-type]


# ── aggregate_reports ───────────────────────────────────────────────────


class TestAggregate:
    def test_empty(self) -> None:
        agg = aggregate_reports([])
        assert agg.total_reports == 0
        assert agg.avg_score == 0.0

    def test_single_report(self) -> None:
        r = parse_axe_report(_SAMPLE)
        agg = aggregate_reports([r])
        assert agg.total_reports == 1
        assert agg.avg_score == 62.0
        assert agg.worst_score == 62

    def test_multiple_reports(self) -> None:
        r1 = parse_axe_report(_SAMPLE)  # 62
        r2 = parse_axe_report({"violations": []})  # 100
        r3 = parse_axe_report({
            "violations": [
                {"id": "foo", "impact": "critical", "nodes": [{"target": ["#a"]}]}
            ]
        })  # 75
        agg = aggregate_reports([r1, r2, r3])
        assert agg.total_reports == 3
        assert agg.avg_score == pytest.approx((62 + 100 + 75) / 3, abs=0.1)
        assert agg.worst_score == 62
        assert agg.severity_totals["critical"] == 2  # r1 + r3
        assert agg.severity_totals["serious"] == 1

    def test_top_rules_ranked_by_node_count(self) -> None:
        # color-contrast 2 node, label 1, foo 3
        r1 = parse_axe_report(_SAMPLE)
        r2 = parse_axe_report({
            "violations": [
                {"id": "foo", "impact": "minor", "nodes": [
                    {"target": ["a"]}, {"target": ["b"]}, {"target": ["c"]}
                ]}
            ]
        })
        agg = aggregate_reports([r1, r2])
        top_ids = [rule_id for rule_id, _ in agg.most_common_violations]
        # foo=3 en üstte, color-contrast=2, label=1
        assert top_ids[0] == "foo"
        assert top_ids[1] == "color-contrast"
