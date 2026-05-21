"""
steps/keyboard_steps.py — Klavye BDD Adimlari (NexusQA KeyboardSteps port'u)

Desteklenen adimlar:
  When kullanici "{key}" tusuna basar
  When kullanici "{element}" elementinde "{key}" tusuna basar
"""
from pytest_bdd import when, parsers

from core.context import GlobalContext
from core.actions import Actions


_KEY_MAP = {
    "enter": "Enter",
    "tab": "Tab",
    "escape": "Escape",
    "esc": "Escape",
    "backspace": "Backspace",
    "delete": "Delete",
    "space": " ",
    "arrowup": "ArrowUp",
    "arrowdown": "ArrowDown",
    "arrowleft": "ArrowLeft",
    "arrowright": "ArrowRight",
    "home": "Home",
    "end": "End",
    "pageup": "PageUp",
    "pagedown": "PageDown",
}


def _normalize_key(key: str) -> str:
    return _KEY_MAP.get(key.lower().strip(), key)


@when(parsers.parse('kullanici "{key}" tusuna basar'))
def step_press_key(page, key):
    Actions(page).press_key(_normalize_key(key))


@when(parsers.parse('kullanici "{element}" elementinde "{key}" tusuna basar'))
def step_press_on_element(page, element, key):
    element = GlobalContext.render(element)
    Actions(page).press_on_element(element, _normalize_key(key))
