"""Marketplace template registry — bütünlük + query API testleri."""
from __future__ import annotations

import pytest

from app.domains.marketplace.templates import (
    TEMPLATES,
    get_template,
    list_categories,
    list_templates,
    search,
    stats,
)


# ── Veri bütünlüğü ──────────────────────────────────────────────────────


def test_at_least_twenty_templates() -> None:
    # Plan §6 E4.2: "20 template ile başlangıç seti"
    assert len(TEMPLATES) >= 20


def test_all_ids_unique() -> None:
    ids = [t.id for t in TEMPLATES]
    assert len(ids) == len(set(ids))


def test_all_gherkin_non_empty_and_contains_keywords() -> None:
    for t in TEMPLATES:
        assert t.gherkin.strip(), f"{t.id}: gherkin boş"
        # Türkçe Gherkin anahtar kelimeleri
        g = t.gherkin
        assert "Senaryo" in g or "Scenario" in g, f"{t.id}: Senaryo anahtarı yok"
        assert any(kw in g for kw in ("Given", "When", "Then")), (
            f"{t.id}: Given/When/Then eksik"
        )


def test_all_categories_recognized() -> None:
    allowed = {"payments", "credit", "card", "kyc", "reporting", "security"}
    for t in TEMPLATES:
        assert t.category in allowed, f"{t.id}: bilinmeyen kategori {t.category}"


def test_ids_lowercase_dot_notation() -> None:
    import re

    pat = re.compile(r"^[a-z][a-z0-9_]*\.[a-z0-9_]+(\.[a-z0-9_]+)?$")
    for t in TEMPLATES:
        assert pat.match(t.id), f"{t.id}: id formatı uygun değil"


def test_tag_is_tuple_not_list() -> None:
    # Immutable — runtime mutasyon kazası olmasın
    for t in TEMPLATES:
        assert isinstance(t.tags, tuple)


# ── Query API ───────────────────────────────────────────────────────────


class TestQueries:
    def test_list_categories_sorted(self) -> None:
        cats = list_categories()
        assert cats == sorted(cats)
        assert "payments" in cats
        assert "credit" in cats

    def test_list_all(self) -> None:
        assert len(list_templates()) == len(TEMPLATES)

    def test_list_by_category(self) -> None:
        payments = list_templates(category="payments")
        assert all(t.category == "payments" for t in payments)
        assert len(payments) >= 3  # EFT happy + insufficient + FAST var

    def test_list_by_tag(self) -> None:
        happy = list_templates(tag="happy-path")
        assert all("happy-path" in t.tags for t in happy)
        assert len(happy) >= 2

    def test_list_category_and_tag_intersect(self) -> None:
        fast = list_templates(category="payments", tag="fast")
        assert all(t.category == "payments" and "fast" in t.tags for t in fast)

    def test_get_by_id_found(self) -> None:
        t = get_template("eft.happy_path")
        assert t is not None
        assert t.category == "payments"

    def test_get_by_id_missing(self) -> None:
        assert get_template("ghost") is None

    def test_search_single_token(self) -> None:
        res = search("SWIFT")
        assert any("swift" in t.id for t in res)

    def test_search_multi_token_and_semantics(self) -> None:
        # "kkb sorgu" → iki token ikisi de geçmeli
        res = search("kkb sorgu")
        assert any(t.id == "kkb.inquiry" for t in res)

    def test_search_empty_returns_empty(self) -> None:
        assert search("") == []
        assert search("   ") == []

    def test_stats_totals(self) -> None:
        s = stats()
        assert s["total"] == len(TEMPLATES)
        # Her kategori en az 1
        for cat in list_categories():
            assert s[cat] >= 1


# ── Serialization ───────────────────────────────────────────────────────


def test_to_dict_json_friendly() -> None:
    import json

    t = TEMPLATES[0]
    d = t.to_dict()
    # Tuple değil list olmalı (JSON serialize dostu)
    assert isinstance(d["tags"], list)
    assert isinstance(d["preconditions"], list)
    s = json.dumps(d, ensure_ascii=False)
    assert len(s) > 50
