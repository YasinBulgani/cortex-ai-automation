"""
steps/hover_steps.py — Hover BDD Adimlari (NexusQA HoverMethods port'u)

Desteklenen adimlar:
  When kullanici "{key}" elementinin uzerine gelir
  When kullanici "{hover_key}" uzerine gelir ve "{click_key}" elementine tiklar
"""
from pytest_bdd import when, parsers

from core.context import GlobalContext
from core.actions import Actions


@when(parsers.parse('kullanici "{key}" elementinin uzerine gelir'))
def step_hover(page, key):
    key = GlobalContext.render(key)
    Actions(page).hover(key)


@when(parsers.parse('kullanici "{hover_key}" uzerine gelir ve "{click_key}" elementine tiklar'))
def step_hover_and_click(page, hover_key, click_key):
    hover_key = GlobalContext.render(hover_key)
    click_key = GlobalContext.render(click_key)
    Actions(page).hover_and_click(hover_key, click_key)
