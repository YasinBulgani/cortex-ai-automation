"""DSL API smoke + integration testleri.

Katalog gerçek YAML dosyalarından yüklenir; bu yüzden sayılar tam kontrol
edilemez, ama yapısal garantileri test ederiz.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def _dsl_catalog_warm() -> None:
    """Modül başında katalog cache'inin yüklenmiş olduğundan emin ol."""
    from app.domains.dsl.loader import catalog_cache

    catalog_cache.load()


def _auth(client: TestClient, db_ready: bool) -> dict:
    if not db_ready:
        pytest.skip("Veritabanı hazır değil")
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    if resp.status_code != 200:
        pytest.skip(f"Login başarısız (seed yok?): {resp.status_code}")
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── Auth ────────────────────────────────────────────────────────────────────


def test_dsl_requires_auth(client: TestClient, _dsl_catalog_warm) -> None:
    assert client.get("/api/v1/dsl/actions").status_code == 401
    assert client.get("/api/v1/dsl/stats").status_code == 401
    assert client.get("/api/v1/dsl/categories").status_code == 401


# ── Stats ───────────────────────────────────────────────────────────────────


def test_dsl_stats_shape(client: TestClient, db_ready: bool, _dsl_catalog_warm) -> None:
    headers = _auth(client, db_ready)
    resp = client.get("/api/v1/dsl/stats", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "total",
        "unique_ids",
        "by_top_category",
        "by_full_category",
        "by_implementation",
        "by_source_file",
        "aliases",
    ):
        assert key in body, f"Stats '{key}' alanı eksik"
    assert isinstance(body["total"], int)
    assert body["total"] >= 0


# ── Categories ──────────────────────────────────────────────────────────────


def test_dsl_categories_tree(client: TestClient, db_ready: bool, _dsl_catalog_warm) -> None:
    headers = _auth(client, db_ready)
    resp = client.get("/api/v1/dsl/categories", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    # Katalog boş değilse, her düğüm id/label/count taşır
    for node in body:
        assert "id" in node and "label" in node and "count" in node
        assert isinstance(node.get("children", []), list)


# ── List ────────────────────────────────────────────────────────────────────


def test_dsl_actions_list_pagination(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    resp = client.get(
        "/api/v1/dsl/actions?page=1&page_size=5",
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 5
    assert len(body["items"]) <= 5
    assert body["total"] >= len(body["items"])


def test_dsl_actions_filter_lang(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    resp = client.get("/api/v1/dsl/actions?lang=tr&page_size=10", headers=headers)
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert "tr" in (item.get("aliases") or {}), (
            f"{item['id']} TR alias içermiyor"
        )


def test_dsl_actions_invalid_lang_rejected(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    resp = client.get("/api/v1/dsl/actions?lang=de", headers=headers)
    assert resp.status_code == 422


# ── Detail & 404 ────────────────────────────────────────────────────────────


def test_dsl_action_not_found(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    resp = client.get(
        "/api/v1/dsl/actions/this_definitely_does_not_exist_xyz",
        headers=headers,
    )
    assert resp.status_code == 404


def test_dsl_action_detail_roundtrip(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    lst = client.get(
        "/api/v1/dsl/actions?page_size=1",
        headers=headers,
    ).json()
    items = lst.get("items") or []
    if not items:
        pytest.skip("Katalog boş; action yok")

    aid = items[0]["id"]
    detail = client.get(f"/api/v1/dsl/actions/{aid}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["id"] == aid
    assert "description" in body
    assert "aliases" in body


# ── Search & Suggest ────────────────────────────────────────────────────────


def test_dsl_search_requires_query(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    resp = client.get("/api/v1/dsl/search", headers=headers)
    assert resp.status_code == 422


def test_dsl_search_returns_shape(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    resp = client.get("/api/v1/dsl/search?q=click", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "click"
    assert "total" in body and "items" in body
    for hit in body["items"]:
        assert "action" in hit and "matched_language" in hit


def test_dsl_suggest_shape(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    resp = client.post(
        "/api/v1/dsl/suggest",
        json={
            "description": "Kullanıcı Login butonuna tıklar ve anasayfa açılır",
            "limit": 5,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert isinstance(body["items"], list)
    assert len(body["items"]) <= 5


def test_dsl_suggest_rejects_empty(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    resp = client.post(
        "/api/v1/dsl/suggest",
        json={"description": ""},
        headers=headers,
    )
    assert resp.status_code == 422


# ── Semantic Search + Hybrid Mode ──────────────────────────────────────────


def test_dsl_suggest_lexical_mode(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    """`mode=lexical` her koşulda çalışır, AI gateway gereksiz."""
    headers = _auth(client, db_ready)
    resp = client.post(
        "/api/v1/dsl/suggest",
        json={
            "description": "kullanıcı butona tıklar",
            "limit": 5,
            "mode": "lexical",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "lexical"
    for hit in body["items"]:
        assert hit.get("source") == "lexical"


def test_dsl_suggest_accepts_auto_mode(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    """`mode=auto` → indeks yoksa lexical'e düşer, her zaman 200 döner."""
    headers = _auth(client, db_ready)
    resp = client.post(
        "/api/v1/dsl/suggest",
        json={"description": "tıkla", "limit": 3, "mode": "auto"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] in {"lexical", "hybrid", "semantic"}


def test_dsl_suggest_rejects_invalid_mode(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    resp = client.post(
        "/api/v1/dsl/suggest",
        json={"description": "tıkla", "mode": "cosmic"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_dsl_semantic_falls_back_without_index(
    client: TestClient, db_ready: bool, _dsl_catalog_warm, monkeypatch
) -> None:
    """Index hazır değilse semantic arama lexical_fallback ile yanıt verir."""
    from app.domains.dsl import embedding_index

    monkeypatch.setattr(embedding_index.alias_index, "is_ready", lambda: False)
    monkeypatch.setattr(embedding_index.alias_index, "ensure_loaded", lambda: None)

    headers = _auth(client, db_ready)
    resp = client.post(
        "/api/v1/dsl/search/semantic",
        json={"q": "click", "limit": 3},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["mode"] == "lexical_fallback"


def test_dsl_index_info_returns_current_state(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    resp = client.get("/api/v1/dsl/index/info", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "ready" in body
    assert "rows" in body
    assert isinstance(body["rows"], int)


# ── Feedback ───────────────────────────────────────────────────────────────


def _feedback_table_exists() -> bool:
    """`alembic upgrade head` çalışmamışsa tabloyu atlayalım."""
    try:
        from sqlalchemy import inspect

        from app.infra.database import engine

        return "sd_dsl_feedback" in inspect(engine).get_table_names()
    except Exception:
        return False


def test_dsl_feedback_records_vote(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    """Feedback endpoint'i vote kaydeder ve sonraki aramalarda bonus uygular."""
    if not _feedback_table_exists():
        pytest.skip("sd_dsl_feedback tablosu yok — 'alembic upgrade head' çalıştırın")

    headers = _auth(client, db_ready)
    lst = client.get(
        "/api/v1/dsl/actions?page_size=1",
        headers=headers,
    ).json()
    if not lst.get("items"):
        pytest.skip("Katalog boş")
    aid = lst["items"][0]["id"]

    resp = client.post(
        "/api/v1/dsl/feedback",
        json={
            "query": "__test_feedback_query__",
            "action_id": aid,
            "vote": "up",
            "search_mode": "lexical",
            "rank": 0,
            "raw_score": 0.8,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"]
    assert "recorded_at" in body


def test_dsl_feedback_rejects_bad_vote(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    resp = client.post(
        "/api/v1/dsl/feedback",
        json={"query": "x", "action_id": "any", "vote": "love"},
        headers=headers,
    )
    assert resp.status_code == 422


# ── Editor API (CRUD + proposals) ──────────────────────────────────────────


def _edit_tables_exist() -> bool:
    try:
        from sqlalchemy import inspect

        from app.infra.database import engine

        tables = set(inspect(engine).get_table_names())
        return {"sd_dsl_edit_proposals", "sd_dsl_catalog_audit"}.issubset(tables)
    except Exception:
        return False


def test_dsl_editor_config_is_public_to_auth(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    resp = client.get("/api/v1/dsl/editor/config", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    for key in ("git_enabled", "git_mode", "base_branch", "provider", "remote", "strict_clean"):
        assert key in body


def test_dsl_list_proposals_ok(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    if not _edit_tables_exist():
        pytest.skip("DSL edit tabloları yok — 'alembic upgrade head' çalıştırın")
    headers = _auth(client, db_ready)
    resp = client.get("/api/v1/dsl/proposals?status=pending", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body and isinstance(body["items"], list)


def test_dsl_list_proposals_rejects_invalid_status(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    resp = client.get("/api/v1/dsl/proposals?status=spaceship", headers=headers)
    assert resp.status_code == 422


def test_dsl_create_action_require_review_roundtrip(
    client: TestClient, db_ready: bool, _dsl_catalog_warm, monkeypatch: pytest.MonkeyPatch
) -> None:
    """require_review=true → pending proposal üretir, YAML yazılmaz."""
    if not _edit_tables_exist():
        pytest.skip("DSL edit tabloları yok")

    headers = _auth(client, db_ready)
    action_id = "__api_smoke_create__"

    # Temizlik — bu id daha önce oluşmuş olabilir (disk'te)
    import pathlib

    from app.domains.dsl import yaml_writer

    existing = yaml_writer.find_action_file(action_id)
    if isinstance(existing, pathlib.Path):
        yaml_writer.delete_action(action_id)

    resp = client.post(
        "/api/v1/dsl/actions",
        headers=headers,
        json={
            "action": {
                "id": action_id,
                "category": "ui.click",
                "description": "API smoke create",
                "aliases": {"tr": ["smoke test"]},
                "implementations": {
                    "python": {"source_file": "engine/steps/smoke.py"}
                },
            },
            "options": {"require_review": True},
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["mode"] == "review"
    assert body["action_id"] == action_id
    assert body["proposal_id"]

    # Proposal listesinde görünüyor
    lst = client.get(
        f"/api/v1/dsl/proposals?status=pending&action_id={action_id}",
        headers=headers,
    ).json()
    assert any(p["id"] == body["proposal_id"] for p in lst["items"])


def test_dsl_create_action_validates_schema(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    resp = client.post(
        "/api/v1/dsl/actions",
        headers=headers,
        json={
            "action": {
                "id": "InVaLid-ID",
                "category": "ui.click",
                "description": "bozuk id",
                "aliases": {"tr": ["x"]},
                "implementations": {"python": {"source_file": "x.py"}},
            },
            "options": {"require_review": True},
        },
    )
    assert resp.status_code == 400


# ── AI Alias üretimi ────────────────────────────────────────────────────────


def test_dsl_ai_aliases_rejects_bad_lang(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    resp = client.post(
        "/api/v1/dsl/actions/click_on_element/ai-aliases",
        headers=headers,
        json={"lang": "de", "count": 3},
    )
    assert resp.status_code == 422


def test_dsl_ai_aliases_rejects_big_count(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    resp = client.post(
        "/api/v1/dsl/actions/click_on_element/ai-aliases",
        headers=headers,
        json={"lang": "tr", "count": 99},
    )
    assert resp.status_code == 422


# ── Mobile katalog ──────────────────────────────────────────────────────────


def test_mobile_catalog_loaded(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    """mobile-actions.yaml yüklendi ve kategorileri doğru."""
    headers = _auth(client, db_ready)
    resp = client.get(
        "/api/v1/dsl/actions?category=mobile&page_size=50",
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 10, "mobile katalog az görünüyor, YAML yüklendi mi?"
    for item in body["items"]:
        assert item["category"].startswith("mobile."), item["category"]


# ── Mobile AI scenario (AI gateway olmadan 502 dönmesini test et) ──────────


def test_mobile_scenario_rejects_short_description(
    client: TestClient, db_ready: bool, _dsl_catalog_warm
) -> None:
    headers = _auth(client, db_ready)
    resp = client.post(
        "/api/v1/automation-suite/mobile/generate",
        headers=headers,
        json={"description": "a"},
    )
    assert resp.status_code == 422
