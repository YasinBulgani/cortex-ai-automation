"""Unit tests for test_management.semantic_search.

All tests mock the AI Gateway so no network calls are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_case(case_id: str, title: str, case_key: str = "TC-001",
               objective: str | None = None, tags: list | None = None,
               archived: bool = False) -> MagicMock:
    case = MagicMock()
    case.id = case_id
    case.case_key = case_key
    case.title = title
    case.objective = objective
    case.preconditions = None
    case.tags = tags or []
    case.project_id = "proj-1"
    case.last_run_status = None
    case.archived = archived
    return case


# ── _case_text ────────────────────────────────────────────────────────────────


class TestCaseText:
    def test_basic_title(self) -> None:
        from app.domains.test_management.semantic_search import _case_text

        case = _make_case("c1", "User login flow", case_key="AUTH-001")
        text = _case_text(case)
        assert "AUTH-001" in text
        assert "User login flow" in text

    def test_includes_objective(self) -> None:
        from app.domains.test_management.semantic_search import _case_text

        case = _make_case("c1", "Checkout", objective="Verify payment succeeds")
        text = _case_text(case)
        assert "Verify payment succeeds" in text

    def test_includes_tags(self) -> None:
        from app.domains.test_management.semantic_search import _case_text

        case = _make_case("c1", "Reset password", tags=["auth", "email"])
        text = _case_text(case)
        assert "auth" in text
        assert "email" in text

    def test_no_tags(self) -> None:
        from app.domains.test_management.semantic_search import _case_text

        case = _make_case("c1", "Empty tags")
        text = _case_text(case)
        assert "Tags" not in text


# ── _cosine_similarity ────────────────────────────────────────────────────────


class TestCosineSimilarity:
    def test_identical_vectors_score_one(self) -> None:
        from app.domains.test_management.semantic_search import _cosine_similarity

        v = [1.0, 0.0, 0.0]
        scores = _cosine_similarity(v, [v])
        assert len(scores) == 1
        assert abs(scores[0] - 1.0) < 1e-5

    def test_orthogonal_vectors_score_zero(self) -> None:
        from app.domains.test_management.semantic_search import _cosine_similarity

        q = [1.0, 0.0, 0.0]
        c = [0.0, 1.0, 0.0]
        scores = _cosine_similarity(q, [c])
        assert abs(scores[0]) < 1e-5

    def test_multiple_corpus_vectors(self) -> None:
        from app.domains.test_management.semantic_search import _cosine_similarity

        q = [1.0, 1.0, 0.0]
        c1 = [1.0, 0.0, 0.0]   # partial match
        c2 = [0.0, 0.0, 1.0]   # no match
        scores = _cosine_similarity(q, [c1, c2])
        assert len(scores) == 2
        assert scores[0] > scores[1]

    def test_empty_corpus(self) -> None:
        from app.domains.test_management.semantic_search import _cosine_similarity

        scores = _cosine_similarity([1.0, 0.0], [])
        assert scores == []


# ── find_similar_cases ────────────────────────────────────────────────────────


class TestFindSimilarCases:
    @pytest.fixture
    def mock_db(self) -> MagicMock:
        db = MagicMock()
        cases = [
            _make_case("c1", "Login with valid credentials", "AUTH-001"),
            _make_case("c2", "Login with invalid password", "AUTH-002"),
            _make_case("c3", "Checkout with credit card", "PAY-001"),
        ]
        db.query.return_value.filter.return_value.all.return_value = cases
        return db

    def test_returns_results_sorted_by_score(self, mock_db: MagicMock) -> None:
        from app.domains.test_management.semantic_search import find_similar_cases

        # Mock embedding: query matches c1 and c2 more than c3
        mock_vectors = [
            [1.0, 1.0, 0.0],   # query
            [1.0, 0.9, 0.0],   # c1 — very similar
            [0.9, 1.0, 0.0],   # c2 — similar
            [0.0, 0.0, 1.0],   # c3 — not similar
        ]

        with patch(
            "app.domains.test_management.semantic_search._embed",
            return_value=mock_vectors,
        ):
            results = find_similar_cases(mock_db, "proj-1", "login test", k=3, min_score=0.0)

        assert len(results) == 3
        # Results should be sorted by score descending
        assert results[0].score >= results[1].score >= results[2].score

    def test_filters_by_min_score(self, mock_db: MagicMock) -> None:
        from app.domains.test_management.semantic_search import find_similar_cases

        mock_vectors = [
            [1.0, 0.0, 0.0],   # query
            [1.0, 0.0, 0.0],   # c1 — score 1.0
            [0.0, 1.0, 0.0],   # c2 — score 0.0
            [0.0, 0.0, 1.0],   # c3 — score 0.0
        ]

        with patch(
            "app.domains.test_management.semantic_search._embed",
            return_value=mock_vectors,
        ):
            results = find_similar_cases(mock_db, "proj-1", "login", min_score=0.5)

        assert all(r.score >= 0.5 for r in results)
        assert len(results) == 1

    def test_returns_empty_when_gateway_unavailable(self, mock_db: MagicMock) -> None:
        from app.domains.test_management.semantic_search import find_similar_cases

        with patch(
            "app.domains.test_management.semantic_search._embed",
            return_value=None,
        ):
            results = find_similar_cases(mock_db, "proj-1", "any query")

        assert results == []

    def test_returns_empty_when_no_cases(self) -> None:
        from app.domains.test_management.semantic_search import find_similar_cases

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        results = find_similar_cases(db, "proj-1", "any query")
        assert results == []

    def test_exclude_case_id_omits_case(self, mock_db: MagicMock) -> None:
        from app.domains.test_management.semantic_search import find_similar_cases

        mock_vectors = [
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],   # c2 (after c1 excluded)
            [0.5, 0.5, 0.0],   # c3
        ]

        with patch(
            "app.domains.test_management.semantic_search._embed",
            return_value=mock_vectors,
        ):
            results = find_similar_cases(
                mock_db, "proj-1", "login", exclude_case_id="c1"
            )

        # c1 should not appear in results
        case_ids = [r.case_id for r in results]
        assert "c1" not in case_ids

    def test_respects_k_limit(self, mock_db: MagicMock) -> None:
        from app.domains.test_management.semantic_search import find_similar_cases

        mock_vectors = [
            [1.0, 0.0, 0.0],   # query
            [1.0, 0.0, 0.0],   # c1
            [0.9, 0.0, 0.0],   # c2
            [0.8, 0.0, 0.0],   # c3
        ]

        with patch(
            "app.domains.test_management.semantic_search._embed",
            return_value=mock_vectors,
        ):
            results = find_similar_cases(mock_db, "proj-1", "login", k=1, min_score=0.0)

        assert len(results) <= 1
