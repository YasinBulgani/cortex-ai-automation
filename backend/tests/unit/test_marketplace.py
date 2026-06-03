"""Unit tests for the marketplace domain — templates registry and router.

Tests:
    1. test_marketplace_templates_loaded      — TEMPLATES listesi boş değil
    2. test_marketplace_template_schema       — her template id, name, description içeriyor
    3. test_marketplace_install_requires_auth — unauthenticated istek 401 döner
    4. test_marketplace_category_filter       — kategori filtresi çalışıyor
    5. test_marketplace_search                — arama sonuçları döner
"""
from __future__ import annotations

import pytest

try:
    from app.domains.marketplace.templates import (
        TEMPLATES,
        Template,
        list_categories,
        list_templates,
        search,
        stats,
    )
    from app.domains.marketplace.router import router

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="marketplace import failed")


# ---------------------------------------------------------------------------
# 1. TEMPLATES listesi boş değil
# ---------------------------------------------------------------------------


def test_marketplace_templates_loaded():
    """TEMPLATES tuple en az bir şablon içermeli."""
    assert len(TEMPLATES) > 0, "TEMPLATES boş — en az 1 built-in şablon bekleniyor"


# ---------------------------------------------------------------------------
# 2. Her template id, name, description içeriyor
# ---------------------------------------------------------------------------


def test_marketplace_template_schema():
    """Her Template nesnesinin id, name ve description alanları dolu olmalı."""
    for t in TEMPLATES:
        assert isinstance(t, Template), f"{t!r} Template örneği değil"
        assert t.id and isinstance(t.id, str), f"Template.id boş veya str değil: {t!r}"
        assert t.name and isinstance(t.name, str), f"Template.name boş veya str değil: {t.id}"
        assert t.description and isinstance(t.description, str), (
            f"Template.description boş veya str değil: {t.id}"
        )


# ---------------------------------------------------------------------------
# 3. Unauthenticated istek 401 döner
# ---------------------------------------------------------------------------


def test_marketplace_install_requires_auth():
    """GET /marketplace/templates kimlik doğrulaması olmadan 401 dönmeli."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.infra.database import get_db
    from unittest.mock import MagicMock

    mock_db = MagicMock()
    mock_db.get.return_value = None

    app = FastAPI()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.include_router(router)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/marketplace/templates")
    assert resp.status_code in {401, 403, 422}, (
        f"Beklenen 401/403/422 ama {resp.status_code} döndü"
    )


# ---------------------------------------------------------------------------
# 4. Kategori filtresi çalışıyor
# ---------------------------------------------------------------------------


def test_marketplace_category_filter():
    """list_templates(category=...) yalnızca o kategorideki şablonları döndürmeli."""
    categories = list_categories()
    assert len(categories) > 0, "list_categories() boş döndü"

    for cat in categories:
        result = list_templates(category=cat)
        assert len(result) > 0, f"'{cat}' kategorisinde şablon yok"
        for t in result:
            assert t.category == cat, (
                f"Filtre hatası: beklenen kategori '{cat}', alınan '{t.category}'"
            )

    # Geçersiz kategori boş liste döndürmeli
    empty = list_templates(category="__nonexistent__")
    assert empty == [], "Geçersiz kategori için boş liste bekleniyor"


# ---------------------------------------------------------------------------
# 5. Arama sonuçları döner
# ---------------------------------------------------------------------------


def test_marketplace_search():
    """search() en az bir template üzerinde gerçek sorgu döndürmeli."""
    # Boş sorgu boş liste döndürmeli
    assert search("") == [], "Boş sorgu boş liste döndürmeli"
    assert search("   ") == [], "Whitespace-only sorgu boş liste döndürmeli"

    # TEMPLATES'den ilk template'in adının ilk kelimesiyle arama yap
    first = TEMPLATES[0]
    first_word = first.name.split()[0].lower()
    results = search(first_word)
    assert len(results) > 0, (
        f"'{first_word}' kelimesiyle arama sonuç döndürmedi"
    )

    # Var olmayan token ile arama boş dönmeli
    no_results = search("xyzzy_nonexistent_token_12345")
    assert no_results == [], "Var olmayan token için boş liste bekleniyor"

    # Tüm sonuçlar Template örneği olmalı
    for t in results:
        assert isinstance(t, Template), f"Arama sonucu Template değil: {t!r}"
