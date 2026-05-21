"""
steps/input_steps.py — Form Input BDD Adimlari (NexusQA InputMethods port'u)

Desteklenen adimlar:
  When kullanici "{key}" alanina "{value}" yazar
  When kullanici "{key}" alanini temizler
  When kullanici "{key}" alanina "{value}" yazip Enter'a basar
  When kullanici "{key}" alanina karakter karakter "{value}" yazar
"""
import allure
from pytest_bdd import when, parsers

from core.context import GlobalContext
from core.actions import Actions


@when(parsers.parse('kullanici "{key}" alanina "{value}" yazar'))
def step_fill_input(page, key, value):
    key = GlobalContext.render(key)
    value = GlobalContext.render(value)
    actions = Actions(page)
    actions.fill(key, value)


@when(parsers.parse('kullanici "{key}" alanini temizler'))
def step_clear_input(page, key):
    key = GlobalContext.render(key)
    actions = Actions(page)
    actions.clear(key)


@when(parsers.parse('kullanici "{key}" alanina "{value}" yazip Enter\'a basar'))
def step_fill_and_enter(page, key, value):
    key = GlobalContext.render(key)
    value = GlobalContext.render(value)
    actions = Actions(page)
    actions.fill_and_enter(key, value)


@when(parsers.parse('kullanici "{key}" alanina karakter karakter "{value}" yazar'))
def step_type_slowly(page, key, value):
    key = GlobalContext.render(key)
    value = GlobalContext.render(value)
    actions = Actions(page)
    actions.type_text(key, value)
