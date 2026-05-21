"""Unit tests for core/pom_ts_generator.py"""
import pytest

from core.pom_ts_generator import POMTypeScriptGenerator


class TestPOMTypeScriptGenerator:
    def setup_method(self):
        self.gen = POMTypeScriptGenerator()

    def test_from_session_basic(self):
        session = {
            "name": "login_test",
            "base_url": "http://localhost:3000",
            "actions": [
                {"action_type": "navigate", "selector": "", "value": "http://localhost:3000/login", "element_name": "page"},
                {"action_type": "type", "selector": "#email", "selector_type": "css", "value": "admin@test.com", "element_name": "email_input"},
                {"action_type": "click", "selector": '[data-testid="login-btn"]', "selector_type": "css", "value": "", "element_name": "login_btn"},
            ],
        }
        code = self.gen.from_session(session)
        assert "class LoginTestPage" in code
        assert "BasePage" in code
        assert "emailInput" in code or "email_input" in code
        assert "loginBtn" in code or "login_btn" in code

    def test_from_session_with_class_name(self):
        session = {"name": "test", "actions": [], "base_url": ""}
        code = self.gen.from_session(session, class_name="MyCustomPage")
        assert "class MyCustomPage" in code

    def test_from_events_with_testid(self):
        events = [
            {
                "target": {
                    "selector": "#btn",
                    "selector_type": "css",
                    "element_name": "submit_btn",
                    "selector_chain": [
                        {"type": "testid", "value": '[data-testid="submit"]', "confidence": 1.0, "stable": True},
                        {"type": "css", "value": "#btn", "confidence": 0.9, "stable": True},
                    ],
                },
                "action": {"type": "click"},
                "context": {"url": "http://localhost/page"},
            },
        ]
        code = self.gen.from_events(events, class_name="EventPage")
        assert "class EventPage" in code
        assert "testId" in code

    def test_from_locator_json(self):
        locator_data = {
            "login_btn": {
                "chain": [{"type": "testid", "value": '[data-testid="login-btn"]', "confidence": 1.0, "stable": True}],
                "screen": "login",
                "element_type": "button",
            },
            "email_input": {
                "chain": [{"type": "css", "value": "#email", "confidence": 0.9, "stable": True}],
                "screen": "login",
                "element_type": "input",
            },
        }
        code = self.gen.from_locator_json(locator_data, class_name="LocatorPage")
        assert "class LocatorPage" in code
        assert "loginBtn" in code or "login_btn" in code

    def test_generates_click_methods(self):
        session = {
            "name": "test",
            "base_url": "",
            "actions": [
                {"action_type": "click", "selector": "#btn", "selector_type": "css", "element_name": "submit_btn", "value": ""},
            ],
        }
        code = self.gen.from_session(session)
        assert "click" in code.lower()

    def test_generates_fill_methods(self):
        session = {
            "name": "test",
            "base_url": "",
            "actions": [
                {"action_type": "type", "selector": "#input", "selector_type": "css", "element_name": "name_field", "value": "test"},
            ],
        }
        code = self.gen.from_session(session)
        assert "fill" in code.lower()

    def test_to_class_name(self):
        assert POMTypeScriptGenerator._to_class_name("login_test") == "LoginTestPage"
        assert POMTypeScriptGenerator._to_class_name("my-flow") == "MyFlowPage"

    def test_to_prop_name(self):
        assert POMTypeScriptGenerator._to_prop_name("login_btn") == "loginBtn"
        assert POMTypeScriptGenerator._to_prop_name("email_input") == "emailInput"
