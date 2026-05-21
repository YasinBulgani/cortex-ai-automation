"""DSL grounding helper unit tests — katalogu mock'lu, hızlı ve izole.

Test stratejisi:
- ``catalog_cache`` singleton'unu her testte temiz tutuyoruz; elle birkaç
  action inject ediyoruz. ``embedding_index`` ise bilerek kapalı — fonksiyonlar
  lexical fallback'e düşsün.
- ``grounding_cache`` (modül içi LRU) testler arasında sızmasın diye her
  test başında temizleniyor.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Katalog cache'ini temiz ve test içinde kontrol edilebilir hale getir."""
    from app.domains.dsl import loader
    from app.domains.tspm import dsl_grounding_for_bdd

    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(loader, "_CATALOG_DIR", catalog_dir)
    loader.catalog_cache._catalog_dir = catalog_dir  # type: ignore[attr-defined]
    loader.catalog_cache._actions = []  # type: ignore[attr-defined]
    loader.catalog_cache._by_id = {}  # type: ignore[attr-defined]
    loader.catalog_cache._loaded_at = "2026-04-20T00:00:00+00:00"

    # Grounding cache — modül içi; testler arası sızma olmasın
    dsl_grounding_for_bdd.clear_grounding_cache()
    dsl_grounding_for_bdd.is_catalog_available.cache_clear()
    yield


def _inject_actions(actions: list[dict]) -> None:
    """Katalog cache'ine elle action listesi yerleştir."""
    from app.domains.dsl import loader
    from app.domains.dsl.schemas import DslAction

    parsed = [DslAction.model_validate(a) for a in actions]
    loader.catalog_cache._actions = parsed  # type: ignore[attr-defined]
    loader.catalog_cache._by_id = {a.id: a for a in parsed}  # type: ignore[attr-defined]


# ── grounded_aliases_for_text ────────────────────────────────────────────────


def test_grounded_aliases_empty_text_returns_empty():
    from app.domains.tspm.dsl_grounding_for_bdd import grounded_aliases_for_text

    result = grounded_aliases_for_text("")
    assert result.is_empty()

    result2 = grounded_aliases_for_text("   \n  ")
    assert result2.is_empty()


def test_grounded_aliases_buckets_by_category_and_tags():
    """ui.click → when, assert.* → then, bgts.state.* → given."""
    _inject_actions([
        {
            "id": "click_text",
            "category": "ui.click",
            "description": "Eylem: kullanıcı metne tıklar",
            "aliases": {"tr": ["kullanıcı \"{text}\" metnine tıklar"]},
            "tags": ["auto-extracted", "when"],
            "implementations": {},
        },
        {
            "id": "assert_visible",
            "category": "assert.visibility",
            "description": "Doğrulama: element görünür",
            "aliases": {"tr": ["\"{selector}\" elementi görünür olmalıdır"]},
            "tags": ["assertion"],
            "implementations": {},
        },
        {
            "id": "user_on_login",
            "category": "bgts.auth",
            "description": "Ön koşul: kullanıcı giriş sayfasında",
            "aliases": {"tr": ["kullanıcı giriş sayfasında bekliyor"]},
            "tags": ["precondition"],
            "implementations": {},
        },
    ])

    from app.domains.tspm.dsl_grounding_for_bdd import grounded_aliases_for_text

    # Query three key tokens — birden çok action eşleşsin
    result = grounded_aliases_for_text(
        "kullanıcı giriş sayfasında tıklar ve element görünür olmalıdır"
    )
    assert any("tıklar" in g.pattern for g in result.when), (
        "when bucket'ında click_text olmalı: {}".format([g.pattern for g in result.when])
    )
    assert any("görünür olmalıdır" in g.pattern for g in result.then), (
        "then bucket'ında assert_visible olmalı: {}".format([g.pattern for g in result.then])
    )
    assert any("giriş sayfasında" in g.pattern for g in result.given), (
        "given bucket'ında user_on_login olmalı: {}".format([g.pattern for g in result.given])
    )


def test_grounding_as_prompt_block_dumps_headers():
    _inject_actions([
        {
            "id": "click_text",
            "category": "ui.click",
            "description": "Eylem",
            "aliases": {"tr": ["kullanıcı \"{text}\" metnine tıklar"]},
            "tags": [],
            "implementations": {},
        },
    ])

    from app.domains.tspm.dsl_grounding_for_bdd import (
        grounded_aliases_for_text,
        grounding_as_prompt_block,
    )

    grounded = grounded_aliases_for_text("tıkla")
    block = grounding_as_prompt_block(grounded)
    assert "DSL Standart Kalıpları" in block
    assert "EGER (When)" in block
    assert "KURAL" in block


def test_grounding_cache_hits_same_key():
    """Aynı metin için ikinci çağrı cache'den gelmeli (hybrid_search bir kere çalışmalı)."""
    _inject_actions([
        {
            "id": "click_text",
            "category": "ui.click",
            "description": "Eylem",
            "aliases": {"tr": ["kullanıcı \"{text}\" metnine tıklar"]},
            "tags": [],
            "implementations": {},
        },
    ])

    from app.domains.tspm.dsl_grounding_for_bdd import grounded_aliases_for_text

    r1 = grounded_aliases_for_text("kullanıcı tıklar")
    r2 = grounded_aliases_for_text("kullanıcı tıklar")
    assert r1 is r2  # aynı nesne referansı — cache hit


# ── snap_step_to_catalog ─────────────────────────────────────────────────────


def test_snap_step_clicks_to_click_action():
    _inject_actions([
        {
            "id": "click_text",
            "category": "ui.click",
            "description": "Eylem",
            "aliases": {"tr": ["kullanıcı \"{text}\" metnine tıklar"]},
            "tags": ["when"],
            "implementations": {},
        },
    ])

    from app.domains.tspm.dsl_grounding_for_bdd import snap_step_to_catalog

    snapped = snap_step_to_catalog("Eğer", 'kullanıcı "Giriş Yap" butonuna tıklar', min_score=0.3)
    assert snapped is not None
    assert snapped.action_id == "click_text"
    # {text} yer tutucusu tırnaklı değerle dolmuş olmalı
    assert "Giriş Yap" in snapped.filled_text


def test_snap_step_fills_capitalized_fallback():
    """Tırnak yoksa Büyük harfli kelime öbeği parametre olur."""
    _inject_actions([
        {
            "id": "click_text",
            "category": "ui.click",
            "description": "Eylem",
            "aliases": {"tr": ["kullanıcı \"{text}\" metnine tıklar"]},
            "tags": ["when"],
            "implementations": {},
        },
    ])

    from app.domains.tspm.dsl_grounding_for_bdd import snap_step_to_catalog

    # Tırnaksız ama büyük harfli "Giriş Yap" — capitalized phrase extraction
    snapped = snap_step_to_catalog("Eğer", "kullanıcı Giriş Yap metnine tıklar", min_score=0.3)
    assert snapped is not None
    assert "Giriş Yap" in snapped.filled_text


def test_snap_step_below_threshold_returns_none():
    _inject_actions([
        {
            "id": "click_text",
            "category": "ui.click",
            "description": "Eylem",
            "aliases": {"tr": ["kullanıcı \"{text}\" metnine tıklar"]},
            "tags": ["when"],
            "implementations": {},
        },
    ])

    from app.domains.tspm.dsl_grounding_for_bdd import snap_step_to_catalog

    # Çok uzak bir cümle (çakışma yok)
    snapped = snap_step_to_catalog(
        "Eğer",
        "zzz xyz non-matching quantum flux capacitor",
        min_score=0.9,
    )
    assert snapped is None


def test_snap_empty_text_returns_none():
    from app.domains.tspm.dsl_grounding_for_bdd import snap_step_to_catalog

    assert snap_step_to_catalog("Eğer", "") is None
    assert snap_step_to_catalog("Eğer", "   ") is None


def test_snap_respects_bucket_hint():
    """Keyword 'O zaman' verilirse assert.* kategorisi öncelikli."""
    _inject_actions([
        {
            "id": "assert_visible",
            "category": "assert.visibility",
            "description": "Doğrulama",
            "aliases": {"tr": ["\"{selector}\" elementi görünür olmalıdır"]},
            "tags": ["then"],
            "implementations": {},
        },
        {
            "id": "click_text",
            "category": "ui.click",
            "description": "Eylem",
            "aliases": {"tr": ["kullanıcı \"{text}\" metnine tıklar"]},
            "tags": ["when"],
            "implementations": {},
        },
    ])

    from app.domains.tspm.dsl_grounding_for_bdd import snap_step_to_catalog

    # "görünür" hem click_text hem assert_visible'a kelime overlap sağlayabilir
    snapped = snap_step_to_catalog(
        "O zaman",
        'hata mesajı "uyarı" görünür olmalıdır',
        min_score=0.3,
    )
    assert snapped is not None
    assert snapped.action_id == "assert_visible"


def test_snap_steps_batch_preserves_unmatched():
    _inject_actions([
        {
            "id": "click_text",
            "category": "ui.click",
            "description": "Eylem",
            "aliases": {"tr": ["kullanıcı \"{text}\" metnine tıklar"]},
            "tags": ["when"],
            "implementations": {},
        },
    ])

    from app.domains.tspm.dsl_grounding_for_bdd import snap_steps

    steps = [
        {"keyword": "Diyelim ki", "text": "sistem hazır"},
        {"keyword": "Eğer", "text": 'kullanıcı "OK" butonuna tıklar'},
        {"keyword": "O zaman", "text": "zzz random no match"},
    ]
    result = snap_steps(steps, min_score=0.3)
    assert len(result) == 3
    # Orta step snap olmalı
    assert result[1].get("dsl_action_id") == "click_text"
    # İlk ve son step snap olmayabilir (katalog az) — en azından text korunmalı
    assert result[0]["text"] == "sistem hazır"
    assert result[2]["text"] == "zzz random no match"


def test_catalog_unavailable_returns_empty_grounding():
    """Katalog boşsa grounded_aliases_for_text boş döner — exception atmaz."""
    # Hiçbir action inject etmiyoruz, catalog_cache boş
    from app.domains.tspm.dsl_grounding_for_bdd import grounded_aliases_for_text

    result = grounded_aliases_for_text("herhangi bir metin")
    assert result.is_empty()
