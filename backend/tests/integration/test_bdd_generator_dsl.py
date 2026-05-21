"""Integration-style tests — BDDGenerator ve legacy generate_bdd_scenarios'un
DSL kataloğuyla birlikte nasıl davrandığını doğrular.

Test stratejisi:
- DB etkileşimini mock'lanmış ``Session`` ile atlatıyoruz; odak noktası
  post-process snap, fallback yolu ve prompt enjeksiyonu.
- LLM provider'larının tamamı devre dışı — legacy fonksiyonun DSL-aware
  fallback'e düşmesini ve kaliteli senaryo üretmesini test ediyoruz.
- Ayrı bir testte LLM başarılı gibi davranır (monkeypatch) ve snap'in
  çıktıyı kanonikleştirdiğini doğrularız.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_catalog_with_seed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Temiz katalog + birkaç TR action inject edilmiş ortam."""
    from app.domains.dsl import loader
    from app.domains.dsl.schemas import DslAction
    from app.domains.tspm import dsl_grounding_for_bdd

    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(loader, "_CATALOG_DIR", catalog_dir)
    loader.catalog_cache._catalog_dir = catalog_dir  # type: ignore[attr-defined]

    seed_actions = [
        {
            "id": "click_text",
            "category": "ui.click",
            "description": "Eylem: kullanıcı metne tıklar",
            "aliases": {"tr": ["kullanıcı \"{text}\" metnine tıklar"]},
            "tags": ["auto-extracted", "when"],
            "implementations": {},
        },
        {
            "id": "fill_input",
            "category": "ui.input",
            "description": "Eylem: kullanıcı alana değer yazar",
            "aliases": {"tr": ["kullanıcı \"{selector}\" kutusuna \"{value}\" yazar"]},
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
            "id": "assert_error_message_visible",
            "category": "assert.visibility",
            "description": "Doğrulama: hata mesajı görünür",
            "aliases": {"tr": ["hata mesajı görünür olmalıdır"]},
            "tags": ["assertion"],
            "implementations": {},
        },
        {
            "id": "user_on_login_page_waiting",
            "category": "bgts.auth",
            "description": "Ön koşul: kullanıcı giriş sayfasında",
            "aliases": {"tr": ["kullanıcı giriş sayfasında bekliyor"]},
            "tags": ["precondition"],
            "implementations": {},
        },
    ]

    parsed = [DslAction.model_validate(a) for a in seed_actions]
    loader.catalog_cache._actions = parsed  # type: ignore[attr-defined]
    loader.catalog_cache._by_id = {a.id: a for a in parsed}  # type: ignore[attr-defined]
    loader.catalog_cache._loaded_at = "2026-04-20T00:00:00+00:00"

    dsl_grounding_for_bdd.clear_grounding_cache()
    dsl_grounding_for_bdd.is_catalog_available.cache_clear()

    # Tüm LLM sağlayıcılarını devre dışı bırak — testler deterministik olsun
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

    def _gateway_unavailable():
        return False

    monkeypatch.setattr(
        "app.domains.ai.gateway_client.gateway_is_available",
        _gateway_unavailable,
    )

    yield


# ── Legacy generate_bdd_scenarios — DSL fallback testi ──────────────────────


def test_legacy_fallback_uses_dsl_catalog_and_snaps():
    """LLM yokken fallback'in ürettiği senaryolar DSL alias'larına snap olmalı."""
    from app.domains.tspm.bdd_generator import generate_bdd_scenarios

    text = (
        'Kullanıcı giriş sayfasında "Giriş Yap" butonuna tıklar. '
        'Kullanıcı "email" alanına "test@example.com" yazar. '
        'Hata mesajı görünür olmalıdır.'
    )

    scenarios = generate_bdd_scenarios(text)

    assert len(scenarios) >= 2, "En az 2 senaryo üretilmeli"

    # En az bir senaryonun en az bir adımı DSL'e snap olmuş olmalı
    any_snapped = False
    for sc in scenarios:
        for step in sc.get("steps", []):
            if step.get("dsl_action_id"):
                any_snapped = True
                break

    assert any_snapped, (
        "Fallback en az bir DSL-snapped step üretmeliydi. Senaryolar: {}".format(
            [[s.get("text") for s in sc.get("steps", [])] for sc in scenarios]
        )
    )


def test_legacy_fallback_no_static_placeholder_text():
    """Eski fallback'in sabit 'sistem hazır durumda / beklenen sonuç doğrulanır'
    şablonu artık çıkmamalı — DSL-aware sürümü kullanılmalı."""
    from app.domains.tspm.bdd_generator import generate_bdd_scenarios

    text = (
        'Kullanıcı "Giriş Yap" butonuna tıklar ve ana sayfa görünür olmalıdır.'
    )
    scenarios = generate_bdd_scenarios(text)
    assert scenarios, "Fallback senaryo üretmedi"

    # "dsl-fallback" tag'i olmalı (yeni fallback'in imzası)
    tags_flat = [t for sc in scenarios for t in (sc.get("tags") or [])]
    assert "dsl-fallback" in tags_flat


def test_legacy_fallback_scenarios_have_coverage_field():
    """Her fallback senaryosu dsl_coverage aggregate field'ına sahip olmalı."""
    from app.domains.tspm.bdd_generator import generate_bdd_scenarios

    text = "Kullanıcı giriş yapar. Hata mesajı görünür olmalıdır."
    scenarios = generate_bdd_scenarios(text)
    for sc in scenarios:
        assert "dsl_coverage" in sc
        assert 0.0 <= sc["dsl_coverage"] <= 1.0


# ── LLM mock'lu: snap post-process doğrulaması ──────────────────────────────


def test_llm_output_gets_snapped_to_canonical(monkeypatch: pytest.MonkeyPatch):
    """AI Gateway senaryo dönerse, non-kanonik step'ler DSL'e snap edilmeli."""
    import json

    # Gateway'i "aktif" gibi göster ve fix bir JSON döndür
    def _gateway_available():
        return True

    def _gateway_complete(**kwargs):
        return json.dumps({
            "scenarios": [
                {
                    "title": "Giriş senaryosu",
                    "description": "Kullanıcı sisteme giriş yapar",
                    "feature": "Giriş",
                    "gherkin": "",
                    "tags": ["smoke"],
                    "steps": [
                        {"keyword": "Diyelim ki", "text": "kullanıcı giriş sayfasında bekliyor"},
                        # LLM 'tıklanır' yerine 'tıklar' kullanmış — snap kanonikleştirsin
                        {"keyword": "Eğer", "text": 'kullanıcı "Giriş Yap" butonuna tıklar'},
                        {"keyword": "O zaman", "text": "hata mesajı görünür olmalıdır"},
                    ],
                },
            ],
        })

    monkeypatch.setattr(
        "app.domains.ai.gateway_client.gateway_is_available",
        _gateway_available,
    )
    monkeypatch.setattr(
        "app.domains.ai.gateway_client.gateway_complete",
        _gateway_complete,
    )

    from app.domains.tspm.bdd_generator import generate_bdd_scenarios

    scenarios = generate_bdd_scenarios("Giriş akışı testi")
    assert len(scenarios) == 1

    steps = scenarios[0]["steps"]
    # Click step — "click_text" action'ına snap olmalı
    click_steps = [s for s in steps if s.get("dsl_action_id") == "click_text"]
    assert click_steps, (
        "Click step snap edilmedi. Steps: {}".format(steps)
    )
    # Yer tutucu "Giriş Yap" ile doldurulmuş olmalı
    assert any("Giriş Yap" in s["text"] for s in click_steps)

    # Visibility assert — assert_error_message_visible'a snap olmalı
    assert_steps = [
        s for s in steps
        if s.get("dsl_action_id") in ("assert_error_message_visible", "assert_visible")
    ]
    assert assert_steps, (
        "Görünürlük doğrulaması snap edilmedi. Steps: {}".format(steps)
    )

    # dsl_coverage yüzde 100'e yakın olmalı
    assert scenarios[0]["dsl_coverage"] >= 0.66


# ── Enhanced BDDGenerator — step library testi ──────────────────────────────


def test_enhanced_get_step_library_includes_dsl_when_grounded():
    """get_step_library(grounding_text=...) DSL alias'larını dict'e enjekte etsin."""
    from unittest.mock import MagicMock
    from app.domains.tspm.bdd_generator import BDDGenerator

    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = []

    gen = BDDGenerator(db=mock_db, project_id="test-project")
    lib = gen.get_step_library(grounding_text="kullanıcı tıklar ve giriş yapar")

    assert "dsl_given" in lib
    assert "dsl_when" in lib
    assert "dsl_then" in lib
    assert "dsl_catalog_size" in lib
    assert lib["dsl_catalog_size"] > 0
    # "tıklar" sorgusu ile DSL when'de click_text çıkmalı
    assert any("tıklar" in p for p in lib["dsl_when"]), (
        "DSL when bucket boş: {}".format(lib["dsl_when"])
    )


def test_enhanced_get_step_library_no_grounding_text():
    """grounding_text olmadığında dsl_* listeleri boş kalmalı."""
    from unittest.mock import MagicMock
    from app.domains.tspm.bdd_generator import BDDGenerator

    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = []

    gen = BDDGenerator(db=mock_db, project_id="test-project")
    lib = gen.get_step_library()
    assert lib["dsl_given"] == []
    assert lib["dsl_when"] == []
    assert lib["dsl_then"] == []
    assert lib["dsl_catalog_size"] == 0


# ── Empty catalog fallback — katalog boşsa mevcut davranış korunsun ──────────


def test_fallback_works_when_catalog_empty(monkeypatch: pytest.MonkeyPatch):
    """Katalog boşsa generate_bdd_scenarios yine senaryo üretmeli (crash etmez)."""
    from app.domains.dsl import loader
    from app.domains.tspm import dsl_grounding_for_bdd

    # Kataloğu boşalt
    loader.catalog_cache._actions = []  # type: ignore[attr-defined]
    loader.catalog_cache._by_id = {}  # type: ignore[attr-defined]
    dsl_grounding_for_bdd.clear_grounding_cache()
    dsl_grounding_for_bdd.is_catalog_available.cache_clear()

    from app.domains.tspm.bdd_generator import generate_bdd_scenarios

    scenarios = generate_bdd_scenarios(
        "Kullanıcı giriş yapar. Ana sayfa gösterilir."
    )
    assert scenarios, "Boş katalogda bile senaryo üretilmeli"
    # Katalog yok → hiçbir step'in dsl_action_id'si olmamalı ama yapı tamam olmalı
    for sc in scenarios:
        assert "title" in sc
        assert "steps" in sc
        assert len(sc["steps"]) >= 1
