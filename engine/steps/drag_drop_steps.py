"""
steps/drag_drop_steps.py — Drag & Drop BDD Adimlari (NexusQA DragDropMethods port'u)

Desteklenen adimlar:
  When kullanici "{source}" elementini "{target}" elementine surukler
"""
from pytest_bdd import when, parsers

from core.context import GlobalContext
from core.actions import Actions


@when(parsers.parse('kullanici "{source}" elementini "{target}" elementine surukler'))
def step_drag_drop(page, source, target):
    source = GlobalContext.render(source)
    target = GlobalContext.render(target)
    Actions(page).drag_and_drop(source, target)
