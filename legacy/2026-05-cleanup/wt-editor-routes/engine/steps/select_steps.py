"""
steps/select_steps.py — Dropdown Secim BDD Adimlari (NexusQA SelectMethods port'u)

Desteklenen adimlar:
  When kullanici "{key}" dropdown'undan "{value}" degerini secer
  When kullanici "{key}" dropdown'undan "{label}" metnini secer
  When kullanici "{key}" dropdown'undan {index}. siradakini secer
"""
from pytest_bdd import when, parsers

from core.context import GlobalContext
from core.actions import Actions


@when(parsers.parse('kullanici "{key}" dropdown\'undan "{value}" degerini secer'))
def step_select_by_value(page, key, value):
    key = GlobalContext.render(key)
    value = GlobalContext.render(value)
    actions = Actions(page)
    actions.select_by_value(key, value)


@when(parsers.parse('kullanici "{key}" dropdown\'undan "{label}" metnini secer'))
def step_select_by_label(page, key, label):
    key = GlobalContext.render(key)
    label = GlobalContext.render(label)
    actions = Actions(page)
    actions.select_by_label(key, label)


@when(parsers.parse('kullanici "{key}" dropdown\'undan {index:d}. siradakini secer'))
def step_select_by_index(page, key, index):
    key = GlobalContext.render(key)
    actions = Actions(page)
    actions.select_by_index(key, index)
