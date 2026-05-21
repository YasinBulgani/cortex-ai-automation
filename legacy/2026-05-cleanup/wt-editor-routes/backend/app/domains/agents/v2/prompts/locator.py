"""Locator Agent — AI XPath üretim prompt'u."""
from __future__ import annotations


LOCATOR_XPATH_SYSTEM_PROMPT = """Sen DOM uzmanı bir test mühendisisin. KIRILGAN OLMAYAN XPath üretirsin.

KURALLAR:
1. Index kullanma (div[3] YASAK)
2. contains(text(), '...'), @aria-label, @role, @data-testid tercih et
3. Parent context kullan
4. Kısa tut (<150 karakter)
5. [1] değil, distinguishing attribute ekle

YANIT: Sadece XPath string. Başına `xpath=` koyma.
"""


def build_locator_xpath_user_prompt(
    element_description: str,
    dom_snippet: str,
    broken_selector: str | None = None,
) -> str:
    broken_hint = ""
    if broken_selector:
        broken_hint = f"\n\nŞu anki locator ÇALIŞMIYOR: `{broken_selector}`."
    return f"""Element tanımı: {element_description}

=== DOM BAĞLAMI ===
{dom_snippet[:3000]}
=== DOM SONU ===
{broken_hint}

Kararlı bir XPath üret.
"""
