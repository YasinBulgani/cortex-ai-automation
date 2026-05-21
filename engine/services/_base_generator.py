"""
Engine — Self-Refine Loop Yardımcısı

Tüm LLM generator servisleri (BDDGenerator, AssertionEngine, CoverageAnalyzer vb.)
bu modülü kullanarak self-refine döngüsünü tekrar yazmadan alır.

Kullanım:
    from ._base_generator import refine_generate

    output, errors, n_refines = refine_generate(
        call_fn=lambda msgs: gateway.complete(msgs, model=model).content,
        messages=initial_messages,
        validate_fn=my_validate,
        refine_prompt="Şu hataları düzelt:\n{errors}",
    )
"""
from __future__ import annotations

import logging
from typing import Callable

_log = logging.getLogger(__name__)

# Varsayılan max refine turları (ilk deneme hariç)
DEFAULT_MAX_REFINE = 2


def refine_generate(
    call_fn: Callable[[list[dict]], str],
    messages: list[dict],
    validate_fn: Callable[[str], list[str]],
    refine_prompt: str,
    max_refine: int = DEFAULT_MAX_REFINE,
    tag: str = "generator",
) -> tuple[str, list[str], int]:
    """
    Self-refine döngüsü: LLM çağır → doğrula → hatalıysa düzelt → tekrar çağır.

    Args:
        call_fn:       ``messages`` listesi alıp LLM yanıtı (str) dönen callable.
        messages:      Başlangıç mesaj listesi [{"role": ..., "content": ...}].
        validate_fn:   Çıktı alan, hata listesi (list[str]) dönen callable.
                       Boş liste → geçerli çıktı.
        refine_prompt: ``{errors}`` placeholder'ı içeren refine talimatı.
        max_refine:    En fazla kaç refine turu yapılacağı (default: 2).
        tag:           Log satırlarında görünen servis adı.

    Returns:
        (output, validation_errors, refine_count)
        - output:            Son LLM çıktısı (geçerli ya da son deneme).
        - validation_errors: Son tur hata listesi (boş → başarılı).
        - refine_count:      Kaç refine turu yapıldı (0 = ilk denemede geçti).
    """
    current_messages = list(messages)
    last_output = ""
    last_errors: list[str] = []
    refines_done = 0

    for attempt in range(max_refine + 1):
        last_output = call_fn(current_messages)
        last_errors = validate_fn(last_output)

        if not last_errors:
            _log.debug("[%s] Başarılı (deneme %d)", tag, attempt + 1)
            break

        if attempt >= max_refine:
            _log.warning(
                "[%s] %d deneme sonrası %d hata kaldı — son çıktı kullanılıyor.",
                tag, attempt + 1, len(last_errors),
            )
            break

        # Refine turu
        refines_done += 1
        error_lines = "\n".join(f"  - {e}" for e in last_errors)
        _log.info("[%s] Refine #%d — %d hata", tag, refines_done, len(last_errors))
        current_messages = [
            *messages,
            {"role": "assistant", "content": last_output},
            {"role": "user", "content": refine_prompt.format(errors=error_lines)},
        ]

    return last_output, last_errors, refines_done


# ── Hazır validate fonksiyonları ─────────────────────────────────────────────

def validate_gherkin(output: str) -> list[str]:
    """
    Gherkin feature dosyasının minimal geçerlilik kontrolü.
    - Feature: satırı olmalı
    - En az bir Scenario veya Scenario Outline olmalı
    - Her senaryo en az bir Then içermeli
    """
    errors: list[str] = []
    if "Feature:" not in output:
        errors.append("'Feature:' satırı bulunamadı")
    if not any(kw in output for kw in ("Scenario:", "Scenario Outline:")):
        errors.append("En az bir 'Scenario:' veya 'Scenario Outline:' olmalı")

    # Her senaryo bloğu Then içermeli mi?
    import re
    scenarios = re.split(r"Scenario(?:\s+Outline)?:", output)
    for i, block in enumerate(scenarios[1:], start=1):  # ilk parça Feature açıklaması
        if "Then" not in block:
            errors.append(f"Senaryo #{i} 'Then' (assertion) içermiyor")
    return errors


def validate_python_code(output: str) -> list[str]:
    """Python syntax kontrolü."""
    import ast
    errors: list[str] = []
    try:
        ast.parse(output)
    except SyntaxError as exc:
        errors.append(f"Python syntax hatası: {exc}")
    if "assert" not in output and "expect" not in output:
        errors.append("Test hiç assertion içermiyor (assert veya expect bulunamadı)")
    return errors


def validate_json_output(output: str) -> list[str]:
    """JSON parse kontrolü (json_repair sonrası)."""
    import json
    from .json_repair import repair_json_safe
    errors: list[str] = []
    result = repair_json_safe(output)
    if result is None:
        errors.append("Geçerli JSON üretilemedi")
    return errors
