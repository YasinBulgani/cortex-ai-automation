from __future__ import annotations

from app.domains.ai.knowledge_store import KnowledgeStore
from app.domains.ai import service as ai_service


class _FakeCursor:
    def __init__(self) -> None:
        self.last_sql = ""

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, sql: str, params=None) -> None:
        self.last_sql = sql

    def fetchone(self):
        if "information_schema.columns" in self.last_sql:
            return (1,)
        return (1,)

    def fetchall(self):
        return []

    def close(self) -> None:
        return None


class _FakeConn:
    def cursor(self) -> _FakeCursor:
        return _FakeCursor()


def test_retrieve_requires_project_id(monkeypatch) -> None:
    store = KnowledgeStore()

    monkeypatch.setattr(
        "app.domains.ai.knowledge_store._embed",
        lambda text: [0.1, 0.2],
    )

    def _unexpected_conn():
        raise AssertionError("DB access should not happen without project scope")

    monkeypatch.setattr(store, "_get_conn", _unexpected_conn)

    assert store.retrieve("login timeout") == []


def test_retrieve_passes_scoped_project_id(monkeypatch) -> None:
    store = KnowledgeStore(project_id="proj-123")
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        "app.domains.ai.knowledge_store._embed",
        lambda text: [0.1, 0.2],
    )
    monkeypatch.setattr(store, "_get_conn", lambda: _FakeConn())
    monkeypatch.setattr(store, "_has_pgvector", lambda cur: True)

    def _fake_vector_search(cur, query_vec, top_k, sources, min_sim, project_id):
        captured["project_id"] = project_id
        return []

    monkeypatch.setattr(store, "_vector_search", _fake_vector_search)

    assert store.retrieve("login timeout") == []
    assert captured["project_id"] == "proj-123"


def test_get_rag_context_returns_empty_without_project_id(monkeypatch) -> None:
    def _unexpected_store(*args, **kwargs):
        raise AssertionError("KnowledgeStore should not be constructed without project_id")

    monkeypatch.setattr(
        ai_service,
        "_get_rag_context",
        ai_service._get_rag_context,
    )
    monkeypatch.setattr(
        "app.domains.ai.knowledge_store.KnowledgeStore",
        _unexpected_store,
    )

    assert ai_service._get_rag_context("login timeout") == ""


def test_get_rag_context_constructs_scoped_store(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class _ScopedStore:
        def __init__(self, project_id=None, **kwargs) -> None:
            captured["project_id"] = project_id

        def retrieve(self, query, top_k=5, sources=None):
            return []

    monkeypatch.setattr(
        "app.domains.ai.knowledge_store.KnowledgeStore",
        _ScopedStore,
    )

    assert ai_service._get_rag_context("login timeout", project_id="proj-123") == ""
    assert captured["project_id"] == "proj-123"
