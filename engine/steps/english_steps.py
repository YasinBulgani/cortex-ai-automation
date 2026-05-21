"""
steps/english_steps.py — Ingilizce BDD Step Alias'lari

Plan Risk 3 Azaltma: NexusQA Ingilizce step pattern'leri
(I click on 'key', I enter 'value' into 'key', vb.) ile
uyumluluk saglar. Feature dosyalari Turkce veya Ingilizce
yazilabilir; her iki dilde de adim tanimlari mevcuttur.

NexusQA step pattern'leri:
  Given I open the application url from config 'url'
  When  I click on 'key'
  When  I enter 'value' into the input 'key'
  When  I press the 'key' key
  When  I clear the input 'key'
  When  I wait for N seconds
  When  I upload the file 'type' to the input 'key'
  When  I refresh the page
  Then  I see the element 'key'
  Then  I verify element 'key' text is 'expected'
"""
import allure
from pytest_bdd import given, when, then, parsers

from config.settings import settings
from core.context import GlobalContext
from core.data_reader import DataReader
from core.locator_manager import LocatorManager
from core.actions import Actions


def _resolve(key: str) -> str:
    return LocatorManager.resolve(key)


def _render_value(value: str) -> str:
    # Çevredeki tırnak işaretlerini soy — regex parser quote'ları yutmaz
    if isinstance(value, str):
        value = value.strip().strip('"').strip("'").strip()
    rendered = GlobalContext.render(value)
    if rendered != value:
        return rendered
    if DataReader.has(value):
        return DataReader.get(value)
    return rendered


# ── GIVEN ─────────────────────────────────────────────────────────────────────

@given(parsers.parse("I open the application url from config '{key}'"))
def en_open_url(page, key):
    url = _render_value(key)
    # Çevredeki tırnak işaretlerini ve boşlukları temizle (regex parser için güvence)
    if isinstance(url, str):
        url = url.strip().strip('"').strip("'").strip()
    if not url:
        url = settings.BASE_URL
    elif not url.startswith(("http://", "https://")):
        # "www.google.com" gibi şema'sız URL'lere https:// ekle
        if "." in url and " " not in url:
            url = "https://" + url
        else:
            url = settings.BASE_URL
    with allure.step(f"Navigate: {url}"):
        page.goto(url, wait_until="domcontentloaded", timeout=settings.NAVIGATION_TIMEOUT)


@given(parsers.parse('I open the application url "{key}"'))
def en_open_url_double_quotes(page, key):
    en_open_url(page, key)


@given(parsers.re(r"I open the application url (?P<key>.+)"))
def en_open_url_bare(page, key):
    en_open_url(page, key.strip())


@given(parsers.parse('I am on the "{path}" page'))
def en_navigate(page, path):
    path = GlobalContext.render(path)
    base = settings.BASE_URL.rstrip("/")
    url = f"{base}/{path.lstrip('/')}" if not path.startswith("http") else path
    with allure.step(f"Navigate: {url}"):
        page.goto(url, wait_until="domcontentloaded", timeout=settings.NAVIGATION_TIMEOUT)


# ── WHEN ──────────────────────────────────────────────────────────────────────

@when(parsers.parse("I click on '{key}'"))
def en_click(page, key):
    key = _render_value(key)
    with allure.step(f"Click: '{key}'"):
        Actions(page).click(key)


@when(parsers.parse('I click on "{key}"'))
def en_click_double_quotes(page, key):
    en_click(page, key)


@when(parsers.re(r"I click on (?P<key>.+)"))
def en_click_bare(page, key):
    en_click(page, key.strip())


@when(parsers.parse("I enter '{value}' into the input '{key}'"))
def en_fill(page, value, key):
    key = _render_value(key)
    value = _render_value(value)
    with allure.step(f"Fill: '{key}' <- '{value}'"):
        Actions(page).fill(key, value)


@when(parsers.parse('I enter "{value}" into the input "{key}"'))
def en_fill_double_quotes(page, value, key):
    en_fill(page, value, key)


@when(parsers.parse("I clear the input '{key}'"))
def en_clear(page, key):
    key = _render_value(key)
    with allure.step(f"Clear: '{key}'"):
        Actions(page).clear(key)


@when(parsers.parse('I clear the input "{key}"'))
def en_clear_double_quotes(page, key):
    en_clear(page, key)


@when(parsers.re(r"I clear and enter (?P<value>\S+) into the input (?P<key>.+)"))
def en_clear_and_fill_bare(page, value, key):
    resolved_key = _render_value(key.strip())
    resolved_value = _render_value(value.strip())
    with allure.step(f"Clear+Fill: '{resolved_key}' <- '{resolved_value}'"):
        Actions(page).clear(resolved_key)
        Actions(page).fill(resolved_key, resolved_value)


@when(parsers.parse("I press the '{key}' key"))
def en_press_key(page, key):
    with allure.step(f"Press: {key}"):
        Actions(page).press_key(key.capitalize())


@when(parsers.parse("I wait for {seconds:d} seconds"))
def en_wait(page, seconds):
    with allure.step(f"Wait: {seconds}s"):
        page.wait_for_timeout(seconds * 1000)


@when(parsers.re(r"I wait for element (?P<key>.+) to be clickable"))
def en_wait_clickable_bare(page, key):
    resolved_key = _render_value(key.strip())
    selector = _resolve(resolved_key)
    with allure.step(f"Wait clickable: '{resolved_key}'"):
        page.locator(selector).first.wait_for(state="visible", timeout=settings.DEFAULT_TIMEOUT)


@when("I refresh the page")
def en_refresh(page):
    with allure.step("Refresh page"):
        page.reload(wait_until="domcontentloaded")


@when(parsers.parse("I upload the file '{file_type}' to the input '{key}'"))
def en_upload(page, file_type, key):
    key = GlobalContext.render(key)
    file_path = settings.BASE_DIR / "data" / "testfiles" / file_type
    with allure.step(f"Upload: '{file_type}' -> '{key}'"):
        Actions(page).upload_file(key, file_path)


@when(parsers.parse("I double click on '{key}'"))
def en_dblclick(page, key):
    key = GlobalContext.render(key)
    with allure.step(f"Double-click: '{key}'"):
        Actions(page).double_click(key)


@when(parsers.parse("I hover over '{key}'"))
def en_hover(page, key):
    key = GlobalContext.render(key)
    with allure.step(f"Hover: '{key}'"):
        Actions(page).hover(key)


@when(parsers.parse("I select '{label}' from '{key}'"))
def en_select(page, label, key):
    key = GlobalContext.render(key)
    label = GlobalContext.render(label)
    with allure.step(f"Select: '{label}' from '{key}'"):
        Actions(page).select_by_label(key, label)


@when(parsers.parse("I check '{key}'"))
def en_check(page, key):
    key = GlobalContext.render(key)
    with allure.step(f"Check: '{key}'"):
        Actions(page).check(key)


@when(parsers.parse("I uncheck '{key}'"))
def en_uncheck(page, key):
    key = GlobalContext.render(key)
    with allure.step(f"Uncheck: '{key}'"):
        Actions(page).uncheck(key)


@when(parsers.parse("I scroll to '{key}'"))
def en_scroll_to(page, key):
    key = GlobalContext.render(key)
    with allure.step(f"Scroll to: '{key}'"):
        Actions(page).scroll_to(key)


@when(parsers.parse("I drag '{source}' to '{target}'"))
def en_drag_drop(page, source, target):
    source = GlobalContext.render(source)
    target = GlobalContext.render(target)
    with allure.step(f"Drag: '{source}' -> '{target}'"):
        Actions(page).drag_and_drop(source, target)


# ── THEN ──────────────────────────────────────────────────────────────────────

@then(parsers.parse("I see the element '{key}'"))
def en_assert_visible(page, key):
    key = _render_value(key)
    with allure.step(f"Visible: '{key}'"):
        Actions(page).assert_visible(key)


@then(parsers.parse('I see the element "{key}"'))
def en_assert_visible_double_quotes(page, key):
    en_assert_visible(page, key)


@then(parsers.re(r"I see the element (?P<key>.+)"))
def en_assert_visible_bare(page, key):
    en_assert_visible(page, key.strip())


@then(parsers.parse("I verify element '{key}' text is '{expected}'"))
def en_assert_text(page, key, expected):
    key = _render_value(key)
    expected = _render_value(expected)
    with allure.step(f"Text check: '{key}' == '{expected}'"):
        Actions(page).assert_text(key, expected)


@then(parsers.parse('I verify element "{key}" text is "{expected}"'))
def en_assert_text_double_quotes(page, key, expected):
    en_assert_text(page, key, expected)


@then(parsers.re(r"I don't see element (?P<key>.+)"))
def en_assert_hidden_bare(page, key):
    resolved_key = _render_value(key.strip())
    with allure.step(f"Hidden: '{resolved_key}'"):
        Actions(page).assert_hidden(resolved_key)


@then(parsers.parse("the element '{key}' should be hidden"))
def en_assert_hidden(page, key):
    key = GlobalContext.render(key)
    with allure.step(f"Hidden: '{key}'"):
        Actions(page).assert_hidden(key)


@then(parsers.parse("the URL should contain '{text}'"))
def en_assert_url(page, text):
    text = GlobalContext.render(text)
    with allure.step(f"URL contains: '{text}'"):
        assert text in page.url, f"URL '{text}' icermiyor: {page.url}"


@then(parsers.parse("the page title should contain '{text}'"))
def en_assert_title(page, text):
    text = GlobalContext.render(text)
    with allure.step(f"Title contains: '{text}'"):
        title = page.title()
        assert text in title, f"Title '{text}' icermiyor: {title}"


@then(parsers.parse("the element '{key}' should be checked"))
def en_assert_checked(page, key):
    key = GlobalContext.render(key)
    assert Actions(page).is_checked(key), f"Not checked: {key}"


@then(parsers.parse("the element '{key}' should be enabled"))
def en_assert_enabled(page, key):
    key = GlobalContext.render(key)
    Actions(page).assert_enabled(key)


@then(parsers.parse("the element '{key}' should be disabled"))
def en_assert_disabled(page, key):
    key = GlobalContext.render(key)
    Actions(page).assert_disabled(key)
