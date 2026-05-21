"""
steps/assertion_steps.py — Dogrulama BDD Adimlari (NexusQA AssertionMethods port'u)

Desteklenen adimlar:
  Then "{key}" elementi gorunur olmalidir
  Then "{key}" elementi gizli olmalidir
  Then "{key}" elementinin metni "{expected}" olmalidir
  Then "{key}" elementinin degeri "{expected}" olmalidir
  Then "{key}" elementi aktif olmalidir
  Then "{key}" elementi deaktif olmalidir
  Then sayfada "{count}" adet "{key}" elementi bulunmalidir
  Then sayfa URL'si "{text}" icermelidir
  Then sayfa basligi "{text}" icermelidir
"""
import allure
from pytest_bdd import then, parsers

from core.context import GlobalContext
from core.actions import Actions


@then(parsers.parse('"{key}" elementi gorunur olmalidir'))
def step_assert_visible(page, key):
    key = GlobalContext.render(key)
    Actions(page).assert_visible(key)


@then(parsers.parse('"{key}" elementi gizli olmalidir'))
def step_assert_hidden(page, key):
    key = GlobalContext.render(key)
    Actions(page).assert_hidden(key)


@then(parsers.parse('"{key}" elementinin metni "{expected}" olmalidir'))
def step_assert_text(page, key, expected):
    key = GlobalContext.render(key)
    expected = GlobalContext.render(expected)
    Actions(page).assert_text(key, expected)


@then(parsers.parse('"{key}" elementinin degeri "{expected}" olmalidir'))
def step_assert_value(page, key, expected):
    key = GlobalContext.render(key)
    expected = GlobalContext.render(expected)
    Actions(page).assert_value(key, expected)


@then(parsers.parse('"{key}" elementi aktif olmalidir'))
def step_assert_enabled(page, key):
    key = GlobalContext.render(key)
    Actions(page).assert_enabled(key)


@then(parsers.parse('"{key}" elementi deaktif olmalidir'))
def step_assert_disabled(page, key):
    key = GlobalContext.render(key)
    Actions(page).assert_disabled(key)


@then(parsers.parse('sayfada "{count:d}" adet "{key}" elementi bulunmalidir'))
def step_assert_count(page, count, key):
    key = GlobalContext.render(key)
    Actions(page).assert_element_count(key, count)


@then(parsers.parse('sayfa URL\'si "{text}" icermelidir'))
def step_assert_url(page, text):
    text = GlobalContext.render(text)
    with allure.step(f"URL kontrol: '{text}'"):
        assert text in page.url, f"URL '{text}' icermiyor: {page.url}"


@then(parsers.parse('sayfa basligi "{text}" icermelidir'))
def step_assert_title(page, text):
    text = GlobalContext.render(text)
    with allure.step(f"Baslik kontrol: '{text}'"):
        title = page.title()
        assert text in title, f"Baslik '{text}' icermiyor: {title}"
