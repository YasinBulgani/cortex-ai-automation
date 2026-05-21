"""Gherkin parser — roundtrip ve edge case testleri."""

from __future__ import annotations

import pytest

from app.domains.agents.v2.schemas.scenario import (
    GherkinFeature,
    GherkinScenario,
    GherkinStep,
)
from app.domains.agents.v2.tools.gherkin_parser import parse_gherkin_text


TR_BASIC = """\
# language: tr
@smoke @banking
Özellik: Giriş

  Senaryo: Geçerli kredensiyel
    Verilen kullanıcı login sayfasındadır
    Eğer e-posta "user@bank.com" girilirse
    Ve şifre "secret123" girilirse
    O zaman ana sayfa görünür
"""


EN_WITH_BACKGROUND = """\
@api
Feature: User API

  Background:
    Given the API base URL is set

  Scenario: Create user
    When POST /users with body "{...}"
    Then response is 201
"""


OUTLINE = """\
# language: tr
Özellik: Para transferi

  Senaryo Taslağı: Çeşitli tutarlar
    Verilen bakiye <bakiye> TL
    Eğer <tutar> TL gönderilir
    O zaman kalan <kalan> TL olur

    Örnekler:
      | bakiye | tutar | kalan |
      | 100    | 30    | 70    |
      | 200    | 80    | 120   |
"""


class TestGherkinParser:
    def test_basic_tr(self):
        f = parse_gherkin_text(TR_BASIC)
        assert f is not None
        assert f.language == "tr"
        assert f.name == "Giriş"
        assert "smoke" in f.tags and "banking" in f.tags
        assert len(f.scenarios) == 1
        sc = f.scenarios[0]
        assert sc.name == "Geçerli kredensiyel"
        assert len(sc.steps) == 4
        # Keyword normalization
        assert sc.steps[0].keyword == "Given"
        assert sc.steps[1].keyword == "When"
        assert sc.steps[2].keyword == "And"
        assert sc.steps[3].keyword == "Then"

    def test_en_with_background(self):
        f = parse_gherkin_text(EN_WITH_BACKGROUND)
        assert f is not None
        assert "api" in f.tags
        assert f.background is not None
        assert len(f.background) == 1
        assert f.background[0].text.startswith("the API base URL")

    def test_outline_with_examples(self):
        f = parse_gherkin_text(OUTLINE)
        assert f is not None
        sc = f.scenarios[0]
        assert sc.is_outline
        assert sc.examples is not None
        assert len(sc.examples) == 2
        assert sc.examples[0]["bakiye"] == "100"

    def test_fence_stripping(self):
        raw = "```gherkin\n" + TR_BASIC + "```"
        f = parse_gherkin_text(raw)
        assert f is not None
        assert f.name == "Giriş"

    def test_malformed_returns_none(self):
        assert parse_gherkin_text("Tamamen bozuk içerik") is None

    def test_roundtrip(self):
        f = parse_gherkin_text(TR_BASIC)
        assert f is not None
        out = f.to_gherkin_text()
        # Yeniden parse edebiliyor muyuz?
        f2 = parse_gherkin_text(out)
        assert f2 is not None
        assert f2.name == f.name
        assert len(f2.scenarios) == len(f.scenarios)
