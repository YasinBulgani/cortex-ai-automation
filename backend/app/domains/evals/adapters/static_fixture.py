"""Static fixture adapter — test/demo için.

Inputs içindeki ``_fixture`` anahtarını aynen ``actual`` olarak geri döner.
Hiçbir dış bağımlılık yok → birim testleri bu adapter ile runner'ı baştan
sona koşabilir, gateway/model gerekmez.

Suite YAML örneği:
    adapter: static_fixture
    cases:
      - id: c1
        inputs:
          _fixture:
            ranked_ids: ["click_button", "click_element"]
            top_1: "click_button"
        expected:
          top_1: "click_button"
          relevant_ids: ["click_button"]
"""
from __future__ import annotations

from typing import Any, Dict


class StaticFixtureAdapter:
    name = "static_fixture"

    def available(self) -> bool:
        return True

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        fixture = inputs.get("_fixture")
        if fixture is None:
            raise ValueError(
                "StaticFixtureAdapter: inputs._fixture zorunlu (dict döner)"
            )
        if not isinstance(fixture, dict):
            raise ValueError("StaticFixtureAdapter: inputs._fixture dict olmalı")
        return dict(fixture)
