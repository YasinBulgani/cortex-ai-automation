"""
steps/scroll_steps.py — Scroll BDD Adimlari (NexusQA ScrollMethods port'u)

Desteklenen adimlar:
  When kullanici "{key}" elementine scroll yapar
  When kullanici sayfayi asagi scroll yapar
  When kullanici sayfayi yukari scroll yapar
  When kullanici sayfa basina scroll yapar
  When kullanici sayfa sonuna scroll yapar
"""
from pytest_bdd import when, parsers

from core.context import GlobalContext
from core.actions import Actions


@when(parsers.parse('kullanici "{key}" elementine scroll yapar'))
def step_scroll_to(page, key):
    key = GlobalContext.render(key)
    actions = Actions(page)
    actions.scroll_to(key)


@when("kullanici sayfayi asagi scroll yapar")
def step_scroll_down(page):
    Actions(page).scroll_page("down", 500)


@when("kullanici sayfayi yukari scroll yapar")
def step_scroll_up(page):
    Actions(page).scroll_page("up", 500)


@when("kullanici sayfa basina scroll yapar")
def step_scroll_top(page):
    Actions(page).scroll_to_top()


@when("kullanici sayfa sonuna scroll yapar")
def step_scroll_bottom(page):
    Actions(page).scroll_to_bottom()
