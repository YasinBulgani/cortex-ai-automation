"""Seed senaryo kütüphanesi testleri."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.domains.mobile.llm_stepper import generate_steps
from app.domains.mobile.seed_scenarios import (
    SEED_SCENARIOS,
    get_seed_scenario,
    list_seed_scenarios,
    seed_categories,
)


pytestmark = pytest.mark.P2


class TestSeedLibrary:
    def test_ten_scenarios(self):
        assert len(SEED_SCENARIOS) == 10

    def test_all_have_unique_ids(self):
        ids = [s.id for s in SEED_SCENARIOS]
        assert len(ids) == len(set(ids))

    def test_all_have_non_empty_prompt(self):
        for s in SEED_SCENARIOS:
            assert len(s.prompt) > 20, f"{s.id} prompt çok kısa"

    def test_all_have_at_least_one_platform(self):
        for s in SEED_SCENARIOS:
            assert s.platforms, f"{s.id} platform tanımsız"

    def test_all_have_tags(self):
        for s in SEED_SCENARIOS:
            assert s.tags, f"{s.id} tag tanımsız"

    def test_difficulty_values(self):
        for s in SEED_SCENARIOS:
            assert s.difficulty in ("kolay", "orta", "zor")

    def test_filter_by_category_auth(self):
        items = list_seed_scenarios(category="auth")
        assert len(items) >= 2
        assert all(s.category == "auth" for s in items)

    def test_filter_by_platform_android(self):
        items = list_seed_scenarios(platform="android")
        assert all("android" in s.platforms for s in items)

    def test_filter_by_platform_ios_excludes_android_only(self):
        ios_items = list_seed_scenarios(platform="ios")
        ids = {s.id for s in ios_items}
        # seed_media_player ve seed_a11y sadece android — iOS listesinde olmamalı
        assert "seed_media_player" not in ids
        assert "seed_a11y_screen_reader" not in ids

    def test_get_by_id(self):
        s = get_seed_scenario("seed_login_happy")
        assert s is not None
        assert s.category == "auth"

    def test_get_by_id_404(self):
        assert get_seed_scenario("nonexistent") is None

    def test_categories_are_unique(self):
        cats = seed_categories()
        assert len(cats) == len(set(cats))


class TestSeedPromptsAreStepable:
    """Her seed prompt'tan en az 2 adım heuristic üretilebilir olmalı."""

    @pytest.mark.parametrize("seed", SEED_SCENARIOS, ids=lambda s: s.id)
    def test_prompt_generates_steps(self, seed):
        resp = generate_steps(seed.prompt, seed.platforms[0])
        assert len(resp.steps) >= 2
        assert resp.steps[0].action == "launch"


class TestSeedRouterEndpoints:
    def test_list_seeds(self, mobile_client: TestClient):
        r = mobile_client.get("/api/v1/mobile/scenarios/seed")
        assert r.status_code == 200
        assert len(r.json()) == 10

    def test_filter_by_category(self, mobile_client: TestClient):
        r = mobile_client.get("/api/v1/mobile/scenarios/seed?category=auth")
        assert r.status_code == 200
        body = r.json()
        assert len(body) >= 2
        assert all(s["category"] == "auth" for s in body)

    def test_filter_by_difficulty(self, mobile_client: TestClient):
        r = mobile_client.get("/api/v1/mobile/scenarios/seed?difficulty=kolay")
        assert r.status_code == 200
        assert all(s["difficulty"] == "kolay" for s in r.json())

    def test_get_single_seed(self, mobile_client: TestClient):
        r = mobile_client.get("/api/v1/mobile/scenarios/seed/seed_login_happy")
        assert r.status_code == 200
        assert r.json()["id"] == "seed_login_happy"

    def test_get_single_seed_404(self, mobile_client: TestClient):
        r = mobile_client.get("/api/v1/mobile/scenarios/seed/ghost")
        assert r.status_code == 404

    def test_list_categories(self, mobile_client: TestClient):
        r = mobile_client.get("/api/v1/mobile/scenarios/seed/categories")
        assert r.status_code == 200
        cats = r.json()
        assert "auth" in cats
        assert "banking" in cats
