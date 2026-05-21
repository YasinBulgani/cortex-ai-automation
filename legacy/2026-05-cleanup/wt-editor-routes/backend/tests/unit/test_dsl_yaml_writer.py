"""ruamel.yaml tabanlı DSL yazıcısının round-trip davranışı.

Gerçek katalog dosyalarını bozmamak için testler geçici dizinde çalışır;
`app.domains.dsl.yaml_writer.CATALOG_DIR` monkeypatch edilir.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def tmp_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Geçici katalog dizini."""
    from app.domains.dsl import yaml_writer

    target = tmp_path / "catalog"
    target.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(yaml_writer, "CATALOG_DIR", target)
    return target


def test_target_file_for_known_category(tmp_catalog):
    from app.domains.dsl import yaml_writer

    assert (
        yaml_writer.target_file_for_category("ui.click").name
        == "ui-actions.yaml"
    )
    assert (
        yaml_writer.target_file_for_category("bgts.project.create").name
        == "bgts-domain.yaml"
    )
    assert (
        yaml_writer.target_file_for_category("mobile.gesture").name
        == "mobile-actions.yaml"
    )


def test_target_file_for_unknown_category(tmp_catalog):
    from app.domains.dsl import yaml_writer

    assert (
        yaml_writer.target_file_for_category("exotic.new").name
        == "uncategorized.yaml"
    )


def test_upsert_create_and_update(tmp_catalog):
    from app.domains.dsl import yaml_writer

    action = {
        "id": "click_test",
        "category": "ui.click",
        "description": "Test aksiyonu",
        "aliases": {"tr": ["tıkla"], "en": ["click"]},
        "implementations": {
            "python": {"source_file": "engine/steps/click.py", "function": "click"}
        },
        "tags": ["ui"],
        "since": "2026-04-17",
    }

    path = yaml_writer.upsert_action(action)
    assert path.name == "ui-actions.yaml"
    assert path.exists()

    # Roundtrip: oku ve kontrol et
    all_items = [it for p, it in yaml_writer.load_all_actions() if it["id"] == "click_test"]
    assert len(all_items) == 1
    assert all_items[0]["description"] == "Test aksiyonu"

    # Update — description değişsin
    action2 = dict(action, description="Güncel açıklama")
    yaml_writer.upsert_action(action2)
    all_items = [it for p, it in yaml_writer.load_all_actions() if it["id"] == "click_test"]
    assert len(all_items) == 1
    assert all_items[0]["description"] == "Güncel açıklama"


def test_upsert_moves_file_when_category_changes(tmp_catalog):
    from app.domains.dsl import yaml_writer

    action = {
        "id": "foo_bar",
        "category": "ui.click",
        "description": "ilk",
        "aliases": {"tr": ["tik"]},
        "implementations": {"python": {"source_file": "x.py"}},
    }
    first = yaml_writer.upsert_action(action)
    assert first.name == "ui-actions.yaml"

    # Kategori değişti → başka dosyaya taşınmalı
    moved = yaml_writer.upsert_action(dict(action, category="api.http"))
    assert moved.name == "api-actions.yaml"

    # Eski dosyada artık yok
    ids_in_ui = [
        it["id"]
        for p, it in yaml_writer.load_all_actions()
        if p.name == "ui-actions.yaml"
    ]
    assert "foo_bar" not in ids_in_ui

    # Yeni dosyada var
    ids_in_api = [
        it["id"]
        for p, it in yaml_writer.load_all_actions()
        if p.name == "api-actions.yaml"
    ]
    assert "foo_bar" in ids_in_api


def test_delete_removes_action(tmp_catalog):
    from app.domains.dsl import yaml_writer

    action = {
        "id": "temp_action",
        "category": "ui.input",
        "description": "geçici",
        "aliases": {"en": ["temp"]},
        "implementations": {"python": {"source_file": "x.py"}},
    }
    yaml_writer.upsert_action(action)
    assert yaml_writer.find_action_file("temp_action") is not None

    deleted = yaml_writer.delete_action("temp_action")
    assert deleted is not None
    assert yaml_writer.find_action_file("temp_action") is None


def test_delete_missing_returns_none(tmp_catalog):
    from app.domains.dsl import yaml_writer

    assert yaml_writer.delete_action("definitely_not_exists_xyz") is None


def test_field_order_is_stable(tmp_catalog):
    from app.domains.dsl import yaml_writer

    action = {
        "notes": "son",
        "description": "Test",
        "tags": ["ui"],
        "category": "ui.click",
        "id": "ordered_action",
        "aliases": {"tr": ["tık"]},
        "implementations": {"python": {"source_file": "x.py"}},
    }
    path = yaml_writer.upsert_action(action)
    content = path.read_text(encoding="utf-8")
    # id category description sırası
    assert content.index("- id: ordered_action") < content.index("category:")
    assert content.index("category:") < content.index("description:")
    assert content.index("description:") < content.index("aliases:")
