"""
Nexus QA — JSON Repair Utility

Küçük açık kaynak modellerin (7b–14b) ürettiği bozuk JSON'u
parse edilebilir hale getirir. Aşamalı strateji:

  1. Doğrudan parse — çoğu zaman yeterli
  2. Markdown fence temizleme
  3. Tek tırnak → çift tırnak
  4. Trailing comma silme
  5. Parantez dengeleme (eksik } veya ] ekleme)
  6. Hâlâ bozuksa ValueError fırlat
"""
from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)


def repair_json(raw: str) -> dict | list:
    """
    Bozuk JSON string'ini onar ve Python nesnesine çevir.

    Args:
        raw: LLM'den gelen ham metin.

    Returns:
        Parse edilmiş dict veya list.

    Raises:
        ValueError: Tüm onarım adımları başarısız olursa.
    """
    # ── Adım 1: Doğrudan parse ───────────────────────────────────────────────
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    text = raw.strip()

    # ── Adım 2: Markdown fence temizle  (```json ... ``` veya ``` ... ```) ──
    text = _strip_markdown_fences(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # ── Adım 3: Tek tırnak → çift tırnak ────────────────────────────────────
    text = _fix_single_quotes(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # ── Adım 4: Trailing comma sil ───────────────────────────────────────────
    text = _remove_trailing_commas(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # ── Adım 5: Eksik kapanış parantezi ekle ────────────────────────────────
    text = _balance_brackets(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # ── Adım 6: JSON bloğunu metinden çıkar (kısmen gömülü JSON) ────────────
    extracted = _extract_json_block(raw)
    if extracted:
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            pass

    logger.warning("json_repair: tüm adımlar başarısız. İlk 200 karakter: %s", raw[:200])
    raise ValueError(f"JSON onarılamadı. Ham metin (ilk 200 karakter): {raw[:200]!r}")


def repair_json_safe(raw: str, default: dict | list | None = None) -> dict | list | None:
    """
    repair_json'un hata fırlatmayan versiyonu.
    Onarım başarısız olursa `default` döner (varsayılan: None).
    """
    try:
        return repair_json(raw)
    except ValueError:
        return default


# ── Yardımcı fonksiyonlar ────────────────────────────────────────────────────

def _strip_markdown_fences(text: str) -> str:
    """```json ... ``` veya ``` ... ``` bloklarını sıyır."""
    # Açılış fence'i (```json, ```JSON, ```)
    text = re.sub(r"^```(?:json|JSON)?\s*\n?", "", text)
    # Kapanış fence'i
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _fix_single_quotes(text: str) -> str:
    """
    Basit tek tırnak → çift tırnak dönüşümü.
    Kaçış karakterlerini korur, iç içe tırnakları handle eder.
    """
    # JSON key veya value'larda tek tırnak kullanan modeller için
    # Dikkatli regex: sadece string sınırlarındaki tırnakları değiştir
    result = []
    in_string = False
    quote_char = None
    i = 0
    while i < len(text):
        ch = text[i]
        if not in_string:
            if ch in ('"', "'"):
                in_string = True
                quote_char = ch
                result.append('"')  # Her zaman çift tırnak açılışı
            else:
                result.append(ch)
        else:
            if ch == '\\' and i + 1 < len(text):
                # Escape sequence — olduğu gibi al
                result.append(ch)
                result.append(text[i + 1])
                i += 2
                continue
            elif ch == quote_char:
                in_string = False
                result.append('"')  # Her zaman çift tırnak kapanışı
            else:
                # Çift tırnak içinde tek tırnak varsa kaçır
                if ch == '"' and quote_char == "'":
                    result.append('\\"')
                else:
                    result.append(ch)
        i += 1
    return "".join(result)


def _remove_trailing_commas(text: str) -> str:
    """
    JSON'da geçersiz olan trailing comma'ları sil.
    Örnek: {"key": "val",} → {"key": "val"}
    """
    # Object kapanışından önce
    text = re.sub(r",\s*}", "}", text)
    # Array kapanışından önce
    text = re.sub(r",\s*\]", "]", text)
    return text


def _balance_brackets(text: str) -> str:
    """
    Eksik kapanış parantezi veya köşeli parantez ekle.
    Stack tabanlı: açık ama kapanmamış her parantez için kapanış ekler.
    """
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

    # Kalan açık parantezler için kapanış ekle (ters sırada)
    return text + "".join(reversed(stack))


def _extract_json_block(text: str) -> str | None:
    """
    Metin içine gömülü JSON bloğunu çıkar.
    İlk { veya [ ile başlayan, geçerli bir JSON bloğu arar.
    """
    for start_ch, end_ch in [('{', '}'), ('[', ']')]:
        idx = text.find(start_ch)
        if idx == -1:
            continue
        # Sondan başlayarak kapanış parantezini bul
        for end_idx in range(len(text) - 1, idx, -1):
            if text[end_idx] == end_ch:
                candidate = text[idx:end_idx + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    continue
    return None
