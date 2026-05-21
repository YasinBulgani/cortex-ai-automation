"""
Engine — JSON Repair Utility

Gateway'deki app/core/json_repair.py ile aynı strateji.
Engine bağımsız deploy edilebildiği için local kopya tutulur;
logic değişirse her iki dosya da güncellenmelidir.

Küçük açık kaynak modellerin (7b–14b) ürettiği bozuk JSON'u
parse edilebilir hale getirir.
"""
from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)


def repair_json(raw: str) -> dict | list:
    """
    Bozuk JSON string'ini onar ve Python nesnesine çevir.

    Raises:
        ValueError: Tüm onarım adımları başarısız olursa.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    text = raw.strip()

    text = _strip_markdown_fences(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    text = _remove_trailing_commas(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    text = _balance_brackets(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    extracted = _extract_json_block(raw)
    if extracted:
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            pass

    logger.warning("json_repair: başarısız. İlk 200 karakter: %s", raw[:200])
    raise ValueError(f"JSON onarılamadı: {raw[:200]!r}")


def repair_json_safe(raw: str, default: dict | list | None = None) -> dict | list | None:
    """Hata fırlatmayan versiyon. Başarısız olursa `default` döner."""
    try:
        return repair_json(raw)
    except ValueError:
        return default


def _strip_markdown_fences(text: str) -> str:
    text = re.sub(r"^```(?:json|JSON)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _remove_trailing_commas(text: str) -> str:
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*\]", "]", text)
    return text


def _balance_brackets(text: str) -> str:
    stack: list[str] = []
    in_string = False
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '\\' and in_string and i + 1 < len(text):
            i += 2
            continue
        if ch == '"':
            in_string = not in_string
        elif not in_string:
            if ch == '{':
                stack.append('}')
            elif ch == '[':
                stack.append(']')
            elif ch in ('}', ']') and stack and stack[-1] == ch:
                stack.pop()
        i += 1
    return text + "".join(reversed(stack))


def _extract_json_block(text: str) -> str | None:
    for start_ch, end_ch in [('{', '}'), ('[', ']')]:
        idx = text.find(start_ch)
        if idx == -1:
            continue
        for end_idx in range(len(text) - 1, idx, -1):
            if text[end_idx] == end_ch:
                candidate = text[idx:end_idx + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    continue
    return None
