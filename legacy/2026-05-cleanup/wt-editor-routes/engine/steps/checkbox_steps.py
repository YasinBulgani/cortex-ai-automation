"""
steps/checkbox_steps.py — Checkbox & Radio BDD Adimlari
(NexusQA CheckboxMethods + RadioButtonMethods port'u)

Desteklenen adimlar:
  When kullanici "{key}" checkbox'ini isaretler
  When kullanici "{key}" checkbox'inin isaretini kaldirir
  Then "{key}" checkbox'i isaretli olmalidir
  Then "{key}" checkbox'i isaretli olmamalidir
"""
from pytest_bdd import when, then, parsers

from core.context import GlobalContext
from core.actions import Actions


@when(parsers.parse('kullanici "{key}" checkbox\'ini isaretler'))
def step_check(page, key):
    key = GlobalContext.render(key)
    actions = Actions(page)
    actions.check(key)


@when(parsers.parse('kullanici "{key}" checkbox\'inin isaretini kaldirir'))
def step_uncheck(page, key):
    key = GlobalContext.render(key)
    actions = Actions(page)
    actions.uncheck(key)


@then(parsers.parse('"{key}" checkbox\'i isaretli olmalidir'))
def step_assert_checked(page, key):
    key = GlobalContext.render(key)
    actions = Actions(page)
    assert actions.is_checked(key), f"Checkbox isaretli degil: {key}"


@then(parsers.parse('"{key}" checkbox\'i isaretli olmamalidir'))
def step_assert_unchecked(page, key):
    key = GlobalContext.render(key)
    actions = Actions(page)
    assert not actions.is_checked(key), f"Checkbox isaretli: {key}"
