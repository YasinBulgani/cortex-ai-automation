# Step Phrase Reference

Bu dosya **Selenium** ve **Playwright** runner'ları için desteklenen tüm Gherkin step phrase'lerini listeler.
Aynı feature dosyası her iki engine ile çalışabilir; sadece glue paketi farklı.

| ✅ | Her iki engine'de var |
| 🅢 | Sadece Selenium |
| 🅟 | Sadece Playwright |

## Navigation

| Step | Engine |
|---|---|
| `Given I open "{string}" link` | ✅ |
| `Given I open the recorded url "{string}"` | ✅ |
| `When I go back and see previous page` | ✅ |
| `When I go forward and see next page` | ✅ |
| `When I reload current page` | ✅ |
| `When I switch to the newly opened tab` | ✅ |
| `When I switch back to the previous tab` | ✅ |
| `When Close the current tab` | ✅ |

## Click / Interaction

| Step | Engine |
|---|---|
| `When I click "{string}"` | ✅ |
| `When I click "{string}" if it exists` | ✅ |
| `When I click radio "{string}" element` | ✅ |
| `When I click "{string}" checkbox element` | ✅ |
| `When I click "{string}" uncheck checkbox element` | ✅ |
| `When I double click "{string}"` | ✅ |
| `When I right click on element with key "{string}"` | ✅ |
| `When I hover over "{string}"` | ✅ |
| `When I mouseover on "{string}" element` | ✅ |
| `When I scroll to "{string}"` | ✅ |
| `When I drag "{string}" element to "{string}" target element` | ✅ |
| `When I hold mouse button on "{string}" element for {int} seconds` | ✅ |
| `When I click outside the current active element` | ✅ |

## Input

| Step | Engine |
|---|---|
| `When I write "{string}" into "{string}"` | ✅ (env placeholder destekli) |
| `When I type "{string}" into "{string}"` | ✅ |
| `When I clear "{string}"` | ✅ |
| `When I enter encrypted password alias "{string}" into "{string}"` | ✅ |
| `When I select "{string}" from "{string}"` | ✅ |
| `When I check "{string}"` | ✅ |
| `When I uncheck "{string}"` | ✅ |
| `When I upload file "{string}" into "{string}"` | ✅ |
| `When I force clear "{string}"` | ✅ |
| `When I force type "{string}" into "{string}"` | ✅ |
| `When I force click "{string}"` | ✅ |

## Keys

| Step | Engine |
|---|---|
| `When I press "{string}"` / `When I press "{string}" key` | ✅ |
| `When I press "{string}" and "{string}" keys simultaneously` | ✅ |
| `When I force press ESC key` | ✅ |

## Shadow DOM

| Step | Engine |
|---|---|
| `When I click shadow element with key "{string}"` | ✅ (Playwright otomatik penetre) |
| `When I force click shadow element with key "{string}"` | ✅ |

## File operations

| Step | Engine |
|---|---|
| `When I click "{string}" to download file "{string}" with extension "{string}" and max size {int} MB` | ✅ |
| `When I delete downloaded file "{string}"` | ✅ |

## Waits

| Step | Engine |
|---|---|
| `When I wait for {int} seconds` | ✅ |
| `When I wait for page to load` | ✅ |

## Variables

| Step | Engine |
|---|---|
| `Given I save the text "{string}" as the variable "{string}"` | ✅ |
| `Given I save the element text "{string}" as the variable "{string}"` | ✅ |
| `Given I save the element value "{string}" as the variable "{string}"` | ✅ |
| `Given I save the current date "{string}" as the variable "{string}"` | ✅ |
| `Given I generate a random unique email with domain "{string}" as the variable "{string}"` | ✅ |
| `When I type variable "{string}" into element "{string}"` | ✅ |
| `Then I verify the variable "{string}" equals to other variable "{string}"` | ✅ |
| `Then I verify the variable "{string}" contains other variable "{string}"` | ✅ |
| `Then I verify the variable "{string}" is not equal to other variable "{string}"` | ✅ |
| `Then I verify element text "{string}" equals to variable "{string}"` | ✅ |
| `Then I verify element text "{string}" contains variable "{string}"` | ✅ |
| `Then I verify element value "{string}" contains variable "{string}"` | ✅ |

## Database

| Step | Engine |
|---|---|
| `When I connect to the database "{string}"` | ✅ |
| `When I close the database connection` | ✅ |
| `When I execute the SQL from json with key "{string}" and parameters "{string}"` | ✅ |

## Crypto

| Step | Engine |
|---|---|
| `When I encrypt password "{string}" and save as alias "{string}" with overwrite` | ✅ |

## Assertions

| Step | Engine |
|---|---|
| `Then I see "{string}"` | ✅ |
| `Then I do not see "{string}"` / `Then I do not see "{string}" element` | ✅ |
| `Then I verify "{string}" contains "{string}"` | ✅ |
| `Then I verify "{string}" value is "{string}"` | ✅ |
| `Then I verify title contains "{string}"` | 🅟 |
| `Then I verify url contains "{string}"` | 🅟 |
| `Then I verify "{string}" is enabled` | 🅟 |
| `Then I verify "{string}" is disabled` | 🅟 |

## Accessibility (axe-core)

| Step | Engine |
|---|---|
| `Then I run accessibility audit and expect WCAG 2.1 AA compliance` | 🅟 |
| `Then I run accessibility audit and expect no critical violations` | 🅟 |
| `Then I run accessibility audit with minimum impact "{string}"` | 🅟 |

Impact level seçenekleri: `minor`, `moderate`, `serious`, `critical`. Default: `serious+` (yani WCAG AA bloklayıcılar).

## Sadece Selenium'da olanlar (henüz Playwright'a gelmedi)

| Step |
|---|
| `When I process approval steps using ... actions menu, ... approval menu, until ... button is found ...` |
| `When I click all "{string}" links and return` |
| `When I click "{string}" combobox as "{string}"` |
| `When Karate ile "{string}" tagli senaryo çalıştırılır` |

> Bu eksiklikleri eklemek için: `PwExtraSteps.java`'ya yeni step + ilgili `PwXxxMethods.java`'ya method.

## Environment placeholder

Write/type step'leri `${ENV:VAR}` ve `${ENV:VAR:default}` placeholder'larını çözer:

```gherkin
When I write "${ENV:CORTEX_USERNAME:test_user}" into "userNameInput"
```

`CORTEX_USERNAME` env değişkeni varsa onun değeri, yoksa `test_user` kullanılır.
