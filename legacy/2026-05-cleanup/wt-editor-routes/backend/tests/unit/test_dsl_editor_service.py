"""DSL editör servisi için unit testleri (git=disabled, DB mock).

Bu modül YALNIZCA servis fonksiyonlarını test eder; HTTP yok, DB için
gerçek SQLAlchemy session kullanıyoruz.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Her test kendi temiz katalog ve git-disabled ortamında çalışsın."""
    from app.domains.dsl import yaml_writer
    from app.domains.dsl import loader

    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(yaml_writer, "CATALOG_DIR", catalog_dir)
    # Loader da geçici dizini kullansın — singleton cache
    monkeypatch.setattr(loader, "_CATALOG_DIR", catalog_dir)
    loader.catalog_cache._catalog_dir = catalog_dir  # type: ignore[attr-defined]
    loader.catalog_cache._actions = []  # type: ignore[attr-defined]
    loader.catalog_cache._by_id = {}  # type: ignore[attr-defined]
    loader.catalog_cache._loaded_at = None  # type: ignore[attr-defined]

    # Git'i kapalı tut
    monkeypatch.setenv("DSL_GIT_ENABLED", "false")
    yield


def test_validate_action_happy_path():
    from app.domains.dsl import editor_service

    payload = {
        "id": "test_action",
        "category": "ui.click",
        "description": "Bir eylemi test eder",
        "aliases": {"tr": ["test tıklaması"]},
        "implementations": {
            "python": {"source_file": "engine/steps/test.py", "function": "test_click"}
        },
    }
    # No raise
    editor_service.validate_action_payload(payload)


def test_validate_action_rejects_bad_id():
    from app.domains.dsl import editor_service

    payload = {
        "id": "BAD-ID",  # uppercase + tire
        "category": "ui.click",
        "description": "Bir eylemi test eder",
        "aliases": {"tr": ["tık"]},
        "implementations": {"python": {"source_file": "x.py"}},
    }
    with pytest.raises(editor_service.EditorError):
        editor_service.validate_action_payload(payload)


def test_validate_action_rejects_empty_aliases():
    from app.domains.dsl import editor_service

    payload = {
        "id": "no_alias",
        "category": "ui.click",
        "description": "Açıklama burada",
        "aliases": {},
        "implementations": {"python": {"source_file": "x.py"}},
    }
    with pytest.raises(editor_service.EditorError):
        editor_service.validate_action_payload(payload)


def test_compute_diff_create():
    from app.domains.dsl import editor_service

    after = {"id": "x", "category": "ui.click"}
    diff = editor_service.compute_diff(None, after)
    assert diff["op"] == "create"
    assert diff["before"] is None
    assert diff["after"] == after
    assert "id" in diff["changed_fields"]


def test_compute_diff_update_detects_fields():
    from app.domains.dsl import editor_service

    before = {"id": "x", "description": "eski", "tags": ["a"]}
    after = {"id": "x", "description": "yeni", "tags": ["a"]}
    diff = editor_service.compute_diff(before, after)
    assert diff["op"] == "update"
    assert diff["changed_fields"] == ["description"]


def test_compute_diff_delete():
    from app.domains.dsl import editor_service

    diff = editor_service.compute_diff({"id": "x"}, None)
    assert diff["op"] == "delete"
    assert diff["after"] is None


# ── apply_edit (git disabled) ──────────────────────────────────────────────


def _dummy_user(user_id: str = "u1", email: str = "[email protected]"):
    class _U:  # noqa: N801
        def __init__(self):
            self.id = user_id
            self.email = email

    return _U()


def _feedback_tables_ready() -> bool:
    """Migration çalışmadıysa testler skip edilsin."""
    try:
        from sqlalchemy import inspect

        from app.infra.database import engine

        tables = set(inspect(engine).get_table_names())
        return {"sd_dsl_edit_proposals", "sd_dsl_catalog_audit"}.issubset(tables)
    except Exception:
        return False


def _db_session():
    from app.infra.database import SessionLocal

    return SessionLocal()


def test_apply_edit_create_writes_yaml(monkeypatch: pytest.MonkeyPatch):
    if not _feedback_tables_ready():
        pytest.skip("DSL edit tabloları yok — 'alembic upgrade head' çalıştırın")

    from app.domains.dsl import editor_service

    payload = {
        "id": "new_action_1",
        "category": "ui.click",
        "description": "Yeni test eylemi",
        "aliases": {"tr": ["tık bir"], "en": ["click one"]},
        "implementations": {
            "python": {"source_file": "engine/steps/x.py", "function": "x"}
        },
    }
    with _db_session() as db:
        result = editor_service.apply_edit(
            db,
            operation="create",
            payload=payload,
            action_id=payload["id"],
            actor=_dummy_user(),
        )

    assert result.status == "merged"
    assert result.mode == "disabled"  # DSL_GIT_ENABLED=false
    assert result.action_id == "new_action_1"
    assert result.proposal_id


def test_apply_edit_create_conflicts_on_existing(monkeypatch: pytest.MonkeyPatch):
    if not _feedback_tables_ready():
        pytest.skip("DSL edit tabloları yok")

    from app.domains.dsl import editor_service
    from app.domains.dsl import yaml_writer

    # Diskte var et
    yaml_writer.upsert_action(
        {
            "id": "dupe_action",
            "category": "ui.click",
            "description": "var olan",
            "aliases": {"tr": ["a"]},
            "implementations": {"python": {"source_file": "x.py"}},
        }
    )
    from app.domains.dsl.loader import catalog_cache

    catalog_cache.load()

    with _db_session() as db:
        with pytest.raises(editor_service.ConflictError):
            editor_service.apply_edit(
                db,
                operation="create",
                payload={
                    "id": "dupe_action",
                    "category": "ui.click",
                    "description": "yeni tanım",
                    "aliases": {"tr": ["b"]},
                    "implementations": {"python": {"source_file": "y.py"}},
                },
                action_id="dupe_action",
                actor=_dummy_user(),
            )


def test_apply_edit_require_review_creates_pending(monkeypatch: pytest.MonkeyPatch):
    if not _feedback_tables_ready():
        pytest.skip("DSL edit tabloları yok")

    from app.domains.dsl import editor_service

    payload = {
        "id": "pending_action_1",
        "category": "ui.click",
        "description": "Pending test",
        "aliases": {"en": ["pending click"]},
        "implementations": {"python": {"source_file": "x.py"}},
    }
    with _db_session() as db:
        result = editor_service.apply_edit(
            db,
            operation="create",
            payload=payload,
            action_id=payload["id"],
            actor=_dummy_user(),
            require_review=True,
        )
        assert result.status == "pending"
        assert result.mode == "review"

        # YAML'e yazılmamalı
        from app.domains.dsl import yaml_writer

        assert yaml_writer.find_action_file("pending_action_1") is None

        # Proposal DB'ye düştü
        proposals = editor_service.list_proposals(db, status="pending", action_id="pending_action_1")
        assert len(proposals) == 1
