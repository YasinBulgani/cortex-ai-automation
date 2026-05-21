"""
Recording Event Model
=====================
Kaydet-oynat (record-playback) mantığına uygun genişletilmiş event modeli.

SmartSelectorEngine ile entegre çalışarak her event için selector chain oluşturur.
Playback sırasında self-healing cascade ile çalışır.

Kullanım:
    builder = EventBuilder(session_id="abc123")
    event = builder.click(
        element_info={"data-testid": "login-btn", "id": "submit", "tag": "button"},
        url="http://localhost:3000/login",
        title="Login"
    )
"""
from __future__ import annotations

import uuid
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any

from core.locator_registry import SelectorCandidate, SelectorChain

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Event Veri Sınıfları
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class BoundingBox:
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EventTarget:
    """Olayın hedef elementi."""
    selector: str = ""
    selector_type: str = "css"
    selector_chain: list[SelectorCandidate] = field(default_factory=list)
    tag_name: str = ""
    element_name: str = ""
    bounding_box: BoundingBox | None = None
    screenshot_b64: str = ""

    def to_dict(self) -> dict:
        return {
            "selector": self.selector,
            "selector_type": self.selector_type,
            "selector_chain": [c.to_dict() for c in self.selector_chain],
            "tag_name": self.tag_name,
            "element_name": self.element_name,
            "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> EventTarget:
        chain = [SelectorCandidate.from_dict(c) for c in d.get("selector_chain", [])]
        bb = BoundingBox(**d["bounding_box"]) if d.get("bounding_box") else None
        return cls(
            selector=d.get("selector", ""),
            selector_type=d.get("selector_type", "css"),
            selector_chain=chain,
            tag_name=d.get("tag_name", ""),
            element_name=d.get("element_name", ""),
            bounding_box=bb,
        )


@dataclass
class EventAction:
    """Olay aksiyon detayları."""
    type: str = ""
    value: str = ""
    key: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> EventAction:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class EventContext:
    """Olayın sayfa bağlamı."""
    url: str = ""
    title: str = ""
    viewport_width: int = 1280
    viewport_height: int = 720
    page_load_state: str = "domcontentloaded"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> EventContext:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class EventAssertion:
    """Opsiyonel doğrulama."""
    type: str = ""
    expected: str = ""
    actual: str = ""
    passed: bool | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> EventAssertion:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class RecordingEvent:
    """Kayıt oturumundaki tek bir event."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    session_id: str = ""

    timestamp: float = 0.0
    wall_clock: str = field(default_factory=lambda: datetime.now().isoformat())

    event_type: str = "user_action"  # user_action | navigation | assertion | wait | system

    target: EventTarget = field(default_factory=EventTarget)
    action: EventAction = field(default_factory=EventAction)
    context: EventContext = field(default_factory=EventContext)
    assertion: EventAssertion | None = None

    def to_dict(self) -> dict:
        result = {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "wall_clock": self.wall_clock,
            "event_type": self.event_type,
            "target": self.target.to_dict(),
            "action": self.action.to_dict(),
            "context": self.context.to_dict(),
        }
        if self.assertion:
            result["assertion"] = self.assertion.to_dict()
        return result

    @classmethod
    def from_dict(cls, d: dict) -> RecordingEvent:
        return cls(
            id=d.get("id", str(uuid.uuid4())[:12]),
            session_id=d.get("session_id", ""),
            timestamp=d.get("timestamp", 0.0),
            wall_clock=d.get("wall_clock", ""),
            event_type=d.get("event_type", "user_action"),
            target=EventTarget.from_dict(d.get("target", {})),
            action=EventAction.from_dict(d.get("action", {})),
            context=EventContext.from_dict(d.get("context", {})),
            assertion=EventAssertion.from_dict(d["assertion"]) if d.get("assertion") else None,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Selector Chain Builder
# ──────────────────────────────────────────────────────────────────────────────

class SelectorChainBuilder:
    """
    Element bilgisinden güvenlik skorlu selector chain oluşturur.
    SmartSelectorEngine'in gelişmiş hali — tek seçici yerine zincir döner.
    """

    CONFIDENCE_MAP: dict[str, float] = {
        "data-testid": 1.0,
        "id": 0.9,
        "aria-label": 0.85,
        "role": 0.85,
        "label": 0.85,
        "name": 0.8,
        "placeholder": 0.7,
        "type+name": 0.65,
        "class": 0.4,
        "text": 0.5,
        "xpath": 0.3,
    }

    STABLE_TYPES = {"data-testid", "id", "aria-label", "role", "label", "name"}

    @classmethod
    def build(cls, element_info: dict) -> SelectorChain:
        """
        Element bilgisinden tüm olası seçicileri çıkarır ve sıralı chain döner.

        Args:
            element_info: {
                tag, id, class, data-testid, aria-label, name,
                placeholder, text, xpath, type, role
            }
        """
        candidates: list[SelectorCandidate] = []

        testid = element_info.get("data-testid", "")
        if testid:
            candidates.append(SelectorCandidate(
                type="testid",
                value=f'[data-testid="{testid}"]',
                confidence=cls.CONFIDENCE_MAP["data-testid"],
                stable=True,
            ))

        el_id = element_info.get("id", "")
        if el_id:
            candidates.append(SelectorCandidate(
                type="css",
                value=f"#{el_id}",
                confidence=cls.CONFIDENCE_MAP["id"],
                stable=True,
            ))

        aria = element_info.get("aria-label", "")
        if aria:
            candidates.append(SelectorCandidate(
                type="css",
                value=f'[aria-label="{aria}"]',
                confidence=cls.CONFIDENCE_MAP["aria-label"],
                stable=True,
            ))

        role = element_info.get("role", "")
        text_content = element_info.get("text", "")
        if role and text_content:
            candidates.append(SelectorCandidate(
                type="role",
                value=f'role={role}[name="{text_content[:50]}"]',
                confidence=cls.CONFIDENCE_MAP["role"],
                stable=True,
            ))

        name = element_info.get("name", "")
        tag = element_info.get("tag", "")
        if name:
            val = f'{tag}[name="{name}"]' if tag else f'[name="{name}"]'
            candidates.append(SelectorCandidate(
                type="css",
                value=val,
                confidence=cls.CONFIDENCE_MAP["name"],
                stable=True,
            ))

        placeholder = element_info.get("placeholder", "")
        if placeholder:
            candidates.append(SelectorCandidate(
                type="css",
                value=f'[placeholder="{placeholder}"]',
                confidence=cls.CONFIDENCE_MAP["placeholder"],
                stable=False,
            ))

        if text_content and not role:
            candidates.append(SelectorCandidate(
                type="text",
                value=f'text="{text_content[:50]}"',
                confidence=cls.CONFIDENCE_MAP["text"],
                stable=False,
            ))

        xpath = element_info.get("xpath", "")
        if xpath:
            candidates.append(SelectorCandidate(
                type="xpath",
                value=xpath,
                confidence=cls.CONFIDENCE_MAP["xpath"],
                stable=False,
            ))

        return SelectorChain(candidates)

    @classmethod
    def to_element_name(cls, element_info: dict) -> str:
        """Element için snake_case ad üretir."""
        import re
        candidates_for_name = [
            element_info.get("data-testid", ""),
            element_info.get("id", ""),
            element_info.get("aria-label", ""),
            element_info.get("name", ""),
            element_info.get("placeholder", ""),
            element_info.get("text", ""),
        ]
        name = next((c for c in candidates_for_name if c), "element")
        name = re.sub(r"[^a-zA-Z0-9_\s]", "", name)
        name = re.sub(r"\s+", "_", name.strip().lower())
        name = re.sub(r"_+", "_", name)
        if not name or name[0].isdigit():
            name = "el_" + name
        return name[:40] or "element"


# ──────────────────────────────────────────────────────────────────────────────
# Event Builder
# ──────────────────────────────────────────────────────────────────────────────

class EventBuilder:
    """
    Recording event'leri kolayca oluşturmak için builder.
    Her aksiyon tipi için kısayol metot sunar.
    """

    def __init__(self, session_id: str = ""):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self._start_time = datetime.now().timestamp()

    def _elapsed(self) -> float:
        return datetime.now().timestamp() - self._start_time

    def _build_target(self, element_info: dict | None = None, selector: str = "",
                      selector_type: str = "css") -> EventTarget:
        if element_info:
            chain = SelectorChainBuilder.build(element_info)
            primary = chain.primary
            return EventTarget(
                selector=primary.value if primary else selector,
                selector_type=primary.type if primary else selector_type,
                selector_chain=chain.candidates,
                tag_name=element_info.get("tag", ""),
                element_name=SelectorChainBuilder.to_element_name(element_info),
            )
        return EventTarget(selector=selector, selector_type=selector_type)

    def _build_context(self, url: str = "", title: str = "") -> EventContext:
        return EventContext(url=url, title=title)

    # ── Aksiyon Kısayolları ────────────────────────────────────────────────
    def click(self, element_info: dict | None = None, selector: str = "",
              url: str = "", title: str = "", **metadata) -> RecordingEvent:
        return RecordingEvent(
            session_id=self.session_id,
            timestamp=self._elapsed(),
            event_type="user_action",
            target=self._build_target(element_info, selector),
            action=EventAction(type="click", metadata=metadata),
            context=self._build_context(url, title),
        )

    def type_text(self, text: str, element_info: dict | None = None,
                  selector: str = "", url: str = "", title: str = "") -> RecordingEvent:
        return RecordingEvent(
            session_id=self.session_id,
            timestamp=self._elapsed(),
            event_type="user_action",
            target=self._build_target(element_info, selector),
            action=EventAction(type="fill", value=text),
            context=self._build_context(url, title),
        )

    def navigate(self, target_url: str, page_title: str = "") -> RecordingEvent:
        return RecordingEvent(
            session_id=self.session_id,
            timestamp=self._elapsed(),
            event_type="navigation",
            action=EventAction(type="navigate", value=target_url),
            context=self._build_context(target_url, page_title),
        )

    def select(self, value: str, element_info: dict | None = None,
               selector: str = "", url: str = "", title: str = "") -> RecordingEvent:
        return RecordingEvent(
            session_id=self.session_id,
            timestamp=self._elapsed(),
            event_type="user_action",
            target=self._build_target(element_info, selector),
            action=EventAction(type="select", value=value),
            context=self._build_context(url, title),
        )

    def check(self, element_info: dict | None = None, selector: str = "",
              url: str = "", title: str = "") -> RecordingEvent:
        return RecordingEvent(
            session_id=self.session_id,
            timestamp=self._elapsed(),
            event_type="user_action",
            target=self._build_target(element_info, selector),
            action=EventAction(type="check"),
            context=self._build_context(url, title),
        )

    def scroll(self, x: int = 0, y: int = 500, selector: str = "",
               url: str = "", title: str = "") -> RecordingEvent:
        return RecordingEvent(
            session_id=self.session_id,
            timestamp=self._elapsed(),
            event_type="user_action",
            target=EventTarget(selector=selector),
            action=EventAction(type="scroll", metadata={"x": x, "y": y}),
            context=self._build_context(url, title),
        )

    def wait_for(self, selector: str = "", duration_ms: int = 0,
                 url: str = "", title: str = "") -> RecordingEvent:
        return RecordingEvent(
            session_id=self.session_id,
            timestamp=self._elapsed(),
            event_type="wait",
            target=EventTarget(selector=selector),
            action=EventAction(type="wait_for", metadata={"duration_ms": duration_ms}),
            context=self._build_context(url, title),
        )

    def press_key(self, key: str, selector: str = "",
                  url: str = "", title: str = "") -> RecordingEvent:
        return RecordingEvent(
            session_id=self.session_id,
            timestamp=self._elapsed(),
            event_type="user_action",
            target=EventTarget(selector=selector),
            action=EventAction(type="press_key", key=key),
            context=self._build_context(url, title),
        )

    def upload(self, file_path: str, element_info: dict | None = None,
               selector: str = "", url: str = "", title: str = "") -> RecordingEvent:
        return RecordingEvent(
            session_id=self.session_id,
            timestamp=self._elapsed(),
            event_type="user_action",
            target=self._build_target(element_info, selector),
            action=EventAction(type="upload", value=file_path),
            context=self._build_context(url, title),
        )

    # ── Assertion Kısayolları ──────────────────────────────────────────────
    def assert_text(self, expected: str, selector: str = "",
                    url: str = "", title: str = "") -> RecordingEvent:
        return RecordingEvent(
            session_id=self.session_id,
            timestamp=self._elapsed(),
            event_type="assertion",
            target=EventTarget(selector=selector),
            action=EventAction(type="assert_text"),
            context=self._build_context(url, title),
            assertion=EventAssertion(type="text", expected=expected),
        )

    def assert_visible(self, selector: str = "",
                       url: str = "", title: str = "") -> RecordingEvent:
        return RecordingEvent(
            session_id=self.session_id,
            timestamp=self._elapsed(),
            event_type="assertion",
            target=EventTarget(selector=selector),
            action=EventAction(type="assert_visible"),
            context=self._build_context(url, title),
            assertion=EventAssertion(type="visible", expected="true"),
        )

    def assert_url(self, expected_url: str) -> RecordingEvent:
        return RecordingEvent(
            session_id=self.session_id,
            timestamp=self._elapsed(),
            event_type="assertion",
            action=EventAction(type="assert_url"),
            context=self._build_context(expected_url),
            assertion=EventAssertion(type="url", expected=expected_url),
        )
