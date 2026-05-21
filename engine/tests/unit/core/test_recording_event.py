"""Unit tests for core/recording_event.py"""
import pytest

from core.recording_event import (
    RecordingEvent,
    EventTarget,
    EventAction,
    EventContext,
    EventAssertion,
    SelectorChainBuilder,
    EventBuilder,
    BoundingBox,
)


class TestSelectorChainBuilder:
    def test_builds_chain_with_testid(self):
        chain = SelectorChainBuilder.build({
            "data-testid": "login-btn",
            "id": "submit",
            "tag": "button",
        })
        assert len(chain.candidates) >= 2
        assert chain.primary.type == "testid"
        assert chain.primary.confidence == 1.0

    def test_builds_chain_id_only(self):
        chain = SelectorChainBuilder.build({"id": "email", "tag": "input"})
        assert chain.primary.value == "#email"

    def test_builds_chain_aria_label(self):
        chain = SelectorChainBuilder.build({"aria-label": "Close"})
        assert any(c.value == '[aria-label="Close"]' for c in chain.candidates)

    def test_builds_chain_name(self):
        chain = SelectorChainBuilder.build({"name": "username", "tag": "input"})
        assert any('name="username"' in c.value for c in chain.candidates)

    def test_builds_chain_text_fallback(self):
        chain = SelectorChainBuilder.build({"text": "Submit"})
        assert any(c.type == "text" for c in chain.candidates)

    def test_builds_chain_xpath_fallback(self):
        chain = SelectorChainBuilder.build({"xpath": "//button[@id='x']"})
        xpath_candidates = [c for c in chain.candidates if c.type == "xpath"]
        assert len(xpath_candidates) == 1
        assert xpath_candidates[0].confidence == 0.3

    def test_empty_info_returns_empty_chain(self):
        chain = SelectorChainBuilder.build({})
        assert len(chain.candidates) == 0

    def test_to_element_name(self):
        assert SelectorChainBuilder.to_element_name({"data-testid": "login-btn"}) == "loginbtn"
        assert SelectorChainBuilder.to_element_name({"id": "email_input"}) == "email_input"
        assert SelectorChainBuilder.to_element_name({}) == "element"
        assert SelectorChainBuilder.to_element_name({"text": "123start"}).startswith("el_")


class TestRecordingEvent:
    def test_round_trip(self):
        event = RecordingEvent(
            id="abc",
            session_id="sess1",
            event_type="user_action",
            target=EventTarget(selector="#btn", selector_type="css", tag_name="button"),
            action=EventAction(type="click"),
            context=EventContext(url="http://localhost/login", title="Login"),
        )
        d = event.to_dict()
        rebuilt = RecordingEvent.from_dict(d)
        assert rebuilt.id == "abc"
        assert rebuilt.target.selector == "#btn"
        assert rebuilt.action.type == "click"
        assert rebuilt.context.url == "http://localhost/login"

    def test_with_assertion(self):
        event = RecordingEvent(
            assertion=EventAssertion(type="text", expected="Hello", passed=True),
        )
        d = event.to_dict()
        assert d["assertion"]["type"] == "text"
        rebuilt = RecordingEvent.from_dict(d)
        assert rebuilt.assertion.expected == "Hello"

    def test_without_assertion(self):
        event = RecordingEvent()
        d = event.to_dict()
        assert "assertion" not in d
        rebuilt = RecordingEvent.from_dict(d)
        assert rebuilt.assertion is None

    def test_bounding_box(self):
        bb = BoundingBox(x=10, y=20, width=100, height=50)
        d = bb.to_dict()
        assert d["x"] == 10
        assert d["height"] == 50


class TestEventBuilder:
    def test_click(self):
        builder = EventBuilder(session_id="s1")
        event = builder.click(
            element_info={"data-testid": "btn", "tag": "button"},
            url="http://localhost/page",
        )
        assert event.session_id == "s1"
        assert event.action.type == "click"
        assert event.target.selector_type == "testid"
        assert len(event.target.selector_chain) >= 1

    def test_type_text(self):
        builder = EventBuilder()
        event = builder.type_text("hello", element_info={"id": "input1"})
        assert event.action.type == "fill"
        assert event.action.value == "hello"

    def test_navigate(self):
        builder = EventBuilder()
        event = builder.navigate("http://example.com", "Home")
        assert event.event_type == "navigation"
        assert event.action.value == "http://example.com"

    def test_assert_text(self):
        builder = EventBuilder()
        event = builder.assert_text("Hello World", selector="#title")
        assert event.event_type == "assertion"
        assert event.assertion.type == "text"
        assert event.assertion.expected == "Hello World"

    def test_assert_url(self):
        builder = EventBuilder()
        event = builder.assert_url("http://example.com/dashboard")
        assert event.assertion.type == "url"

    def test_scroll(self):
        builder = EventBuilder()
        event = builder.scroll(y=800)
        assert event.action.type == "scroll"
        assert event.action.metadata["y"] == 800

    def test_press_key(self):
        builder = EventBuilder()
        event = builder.press_key("Enter", selector="#input")
        assert event.action.type == "press_key"
        assert event.action.key == "Enter"

    def test_timestamp_increments(self):
        builder = EventBuilder()
        e1 = builder.click(selector="#a")
        e2 = builder.click(selector="#b")
        assert e2.timestamp >= e1.timestamp
