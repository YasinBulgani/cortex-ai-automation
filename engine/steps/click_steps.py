"""
steps/click_steps.py — Tikla BDD Adimlari (NexusQA ClickMethods port'u)

Desteklenen adimlar:
  When kullanici "{key}" elementine tiklar
  When kullanici "{key}" elementine cift tiklar
  When kullanici "{key}" elementine sag tiklar
  When kullanici "{text}" metnine tiklar
  When kullanici "{key}" elementine force tiklar
"""
import allure
from pytest_bdd import when, parsers

from core.context import GlobalContext
from core.actions import Actions


@when(parsers.parse('kullanici "{key}" elementine tiklar'))
def step_click_element(page, key):
    key = GlobalContext.render(key)
    actions = Actions(page)
    actions.click(key)


@when(parsers.parse('kullanici "{key}" elementine cift tiklar'))
def step_double_click(page, key):
    key = GlobalContext.render(key)
    actions = Actions(page)
    actions.double_click(key)


@when(parsers.parse('kullanici "{key}" elementine sag tiklar'))
def step_right_click(page, key):
    key = GlobalContext.render(key)
    actions = Actions(page)
    actions.right_click(key)


@when(parsers.parse('kullanici "{text}" metnine tiklar'))
def step_click_text(page, text):
    text = GlobalContext.render(text)
    actions = Actions(page)
    actions.click_text(text)


@when(parsers.parse('kullanici "{key}" elementine force tiklar'))
def step_force_click(page, key):
    key = GlobalContext.render(key)
    actions = Actions(page)
    actions.force_click(key)
