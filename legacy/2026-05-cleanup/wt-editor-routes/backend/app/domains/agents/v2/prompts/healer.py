"""Healer Agent prompt'ları."""
from __future__ import annotations

import json


HEALER_CLASSIFY_SYSTEM_PROMPT = """Kırık bir testin bağlamına bakıp tek kelimeyle kategori söylersin.

KATEGORİLER:
- locator_changed
- timing_issue
- data_dependency
- env_issue
- real_bug
- flaky
- test_bug

SADECE kategori adı.
"""


def build_healer_classify_user_prompt(
    error_type: str,
    error_message: str,
    stack_trace: str,
    last_actions: list[dict],
    console_errors: list[str],
    dom_changed: bool,
) -> str:
    return f"""Hata tipi: {error_type}
Hata mesajı: {error_message[:500]}

Stack (ilk 1000 kar):
{stack_trace[:1000]}

Son aksiyonlar:
{json.dumps(last_actions[-3:], ensure_ascii=False, indent=2)}

Console error sayısı: {len(console_errors)}
{chr(10).join(console_errors[:3])}

DOM değişti mi: {dom_changed}

Kategori?
"""


HEALER_FIX_SYSTEM_PROMPT = """Kırılmış bir locator için 3 ALTERNATİF üretirsin.

YANIT (JSON):
[
  {"strategy": "role_based", "new_selector": "...", "confidence": 0.85, "reasoning": "..."},
  {"strategy": "text_based", "new_selector": "...", "confidence": 0.70, "reasoning": "..."},
  {"strategy": "vision_xpath", "new_selector": "...", "confidence": 0.60, "reasoning": "..."}
]
"""


def build_healer_fix_user_prompt(
    element_description: str,
    broken_selector: str,
    dom_snippet: str,
    previous_dom_snippet: str | None = None,
) -> str:
    diff = ""
    if previous_dom_snippet:
        diff = f"\n\nÖnceki DOM (test geçerken):\n{previous_dom_snippet[:1500]}"
    return f"""Element tanımı: {element_description}

KIRILAN locator: `{broken_selector}`

Şu anki DOM:
{dom_snippet[:2500]}
{diff}

3 alternatif üret.
"""
