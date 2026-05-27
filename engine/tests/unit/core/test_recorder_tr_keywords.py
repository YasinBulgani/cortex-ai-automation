"""Regression tests for TR_KEYWORDS expansion in CucumberGenerator.

2026-05-24 düzeltmesi: 12 yeni action type eklendi,
bilinmeyen action'lar 'MANUEL GEREKLİ' uyarısı verir.
"""
from __future__ import annotations

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'core'))

from test_recorder import CucumberGenerator, RecordedAction


def _make_action(action_type: str, selector: str = "#el", value: str = "") -> RecordedAction:
    return RecordedAction(
        action_type=action_type,
        selector=selector,
        value=value,
        element_name=selector,
        metadata={},
    )


class TestTRKeywordsExpansion:
    def setup_method(self):
        self.gen = CucumberGenerator()

    def test_drag_drop_has_step(self):
        action = _make_action("drag_drop")
        step = self.gen._action_to_step(action)
        assert "drag_drop" not in step.lower() or "sürükleyip" in step

    def test_multi_select_has_step(self):
        action = _make_action("multi_select")
        step = self.gen._action_to_step(action)
        assert "multi_select" not in step or "birden fazla" in step

    def test_double_click_has_step(self):
        action = _make_action("double_click")
        step = self.gen._action_to_step(action)
        assert "çift tıklar" in step or "MANUEL" in step

    def test_check_has_step(self):
        action = _make_action("check")
        step = self.gen._action_to_step(action)
        assert "işaretler" in step or "MANUEL" in step

    def test_press_key_has_step(self):
        action = _make_action("press_key", value="Enter")
        step = self.gen._action_to_step(action)
        assert "Enter" in step or "tuşuna basar" in step

    def test_unknown_action_has_warning(self):
        action = _make_action("completely_unknown_action_xyz")
        step = self.gen._action_to_step(action)
        assert "MANUEL" in step.upper() or "REQUIRED" in step.upper()

    def test_known_actions_no_warning(self):
        known = ["navigate", "click", "type", "select", "wait", "scroll", "hover"]
        for action_type in known:
            action = _make_action(action_type, value="test")
            step = self.gen._action_to_step(action)
            assert "MANUEL GEREKLİ" not in step, f"{action_type} için MANUEL uyarısı olmamalı"
