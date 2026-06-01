"""Unit tests for app.domains.knowledge_base.service (in-memory store)."""
from __future__ import annotations

import pytest

try:
    import app.domains.knowledge_base.service as svc
except ImportError as _e:  # pragma: no cover
    svc = None  # type: ignore

pytestmark = pytest.mark.skipif(svc is None, reason=f"knowledge_base service unavailable: {svc}")


@pytest.fixture(autouse=True)
def _clear_store():
    """Ensure a clean in-memory store for every test."""
    if svc is not None:
        svc.clear()
    yield
    if svc is not None:
        svc.clear()


# ── create_article ────────────────────────────────────────────────────────


def test_create_article_missing_title_raises_value_error():
    with pytest.raises(ValueError, match="title ve body zorunlu"):
        svc.create_article(title="   ", body="Some body content.", author_id="user-1")


def test_create_article_missing_body_raises_value_error():
    with pytest.raises(ValueError, match="title ve body zorunlu"):
        svc.create_article(title="Valid Title", body="  ", author_id="user-1")


def test_create_article_success():
    article = svc.create_article(
        title="Getting Started",
        body="Welcome to the knowledge base.",
        author_id="user-42",
        author_name="Alice",
        tags=["intro", "basics"],
        category="getting-started",
    )
    assert article.id.startswith("a-")
    assert article.title == "Getting Started"
    assert article.category == "getting-started"
    assert "intro" in article.tags
    assert article.author_id == "user-42"
    assert article.view_count == 0


# ── get_article ───────────────────────────────────────────────────────────


def test_get_article_returns_none_when_not_found():
    """get_article returns None for unknown IDs (no KeyError)."""
    result = svc.get_article("a-nonexistent")
    assert result is None


def test_get_article_increments_view_count():
    article = svc.create_article(
        title="Popular Article",
        body="Content here.",
        author_id="user-1",
    )
    assert article.view_count == 0
    fetched = svc.get_article(article.id)
    assert fetched is not None
    assert fetched.view_count == 1


def test_get_article_no_increment_when_flag_false():
    article = svc.create_article(
        title="Silent Read",
        body="No increment please.",
        author_id="user-1",
    )
    svc.get_article(article.id, increment_views=False)
    assert article.view_count == 0


# ── list_articles (filter by category/tag) ───────────────────────────────


def test_list_articles_filter_by_category():
    svc.create_article(title="Cat A", body="Body A.", author_id="u", category="cat-a")
    svc.create_article(title="Cat B", body="Body B.", author_id="u", category="cat-b")
    results = svc.list_articles(category="cat-a")
    assert len(results) == 1
    assert results[0].title == "Cat A"


def test_list_articles_filter_by_tag():
    svc.create_article(title="Tagged", body="Body.", author_id="u", tags=["python", "testing"])
    svc.create_article(title="Untagged", body="Body.", author_id="u", tags=["java"])
    results = svc.list_articles(tag="python")
    assert len(results) == 1
    assert results[0].title == "Tagged"


def test_list_articles_no_filter_returns_all():
    svc.create_article(title="A1", body="Body.", author_id="u")
    svc.create_article(title="A2", body="Body.", author_id="u")
    svc.create_article(title="A3", body="Body.", author_id="u")
    assert len(svc.list_articles()) == 3


# ── search_articles ───────────────────────────────────────────────────────


def test_search_returns_matching_articles():
    svc.create_article(title="Python Testing Guide", body="pytest is great.", author_id="u")
    svc.create_article(title="Java Guide", body="JUnit tests.", author_id="u")
    results = svc.search("python")
    assert len(results) == 1
    assert results[0].title == "Python Testing Guide"


def test_search_empty_query_returns_empty_list():
    svc.create_article(title="Some Article", body="Content.", author_id="u")
    results = svc.search("   ")
    assert results == []


def test_search_matches_body_content():
    svc.create_article(
        title="Unremarkable Title",
        body="This article discusses selenium locator strategies.",
        author_id="u",
    )
    results = svc.search("selenium")
    assert len(results) == 1


def test_search_tag_match():
    svc.create_article(
        title="Some Article",
        body="Content without keyword.",
        author_id="u",
        tags=["automation", "playwright"],
    )
    results = svc.search("playwright")
    assert len(results) >= 1
    assert any(a.title == "Some Article" for a in results)


# ── update_article ────────────────────────────────────────────────────────


def test_update_article_by_author():
    article = svc.create_article(
        title="Original Title", body="Original body.", author_id="author-1"
    )
    updated = svc.update_article(
        article.id, "author-1", title="Updated Title", body="New body."
    )
    assert updated is not None
    assert updated.title == "Updated Title"
    assert updated.body == "New body."


def test_update_article_by_admin():
    article = svc.create_article(
        title="Protected", body="Admin only update.", author_id="author-1"
    )
    updated = svc.update_article(
        article.id, "admin-99", title="Admin Edit", is_admin=True
    )
    assert updated is not None
    assert updated.title == "Admin Edit"


def test_update_article_permission_error_for_non_author():
    article = svc.create_article(
        title="Mine", body="Don't touch.", author_id="author-1"
    )
    with pytest.raises(PermissionError, match="Sadece yazar veya admin"):
        svc.update_article(article.id, "stranger-99", title="Hacked")


def test_update_article_returns_none_for_unknown_id():
    result = svc.update_article("a-ghost", "user-1", title="X")
    assert result is None


# ── delete_article ────────────────────────────────────────────────────────


def test_delete_article_by_author():
    article = svc.create_article(
        title="To Delete", body="Temporary.", author_id="author-1"
    )
    result = svc.delete_article(article.id, "author-1")
    assert result is True
    assert svc.get_article(article.id, increment_views=False) is None


def test_delete_article_returns_false_for_unknown_id():
    result = svc.delete_article("a-missing", "user-1")
    assert result is False


def test_delete_article_permission_error_for_non_author():
    article = svc.create_article(
        title="Protected", body="Content.", author_id="author-1"
    )
    with pytest.raises(PermissionError, match="Sadece yazar veya admin"):
        svc.delete_article(article.id, "intruder-99")
